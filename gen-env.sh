#!/bin/bash
echo "Bayanat Environment Generation Script"

deployment=""
env_file=.env
domain=""
conf=""
media_path=""

while getopts "dne:oD:" option; do
    case $option in
        D | domain)
            domain="$OPTARG"
        ;;
        d | docker)
            deployment="d"
            media_path=./enferno/media/
        ;;
        n | native)
            deployment="n"
        ;;
        e | env)
            env_file="$OPTARG"
        ;;
        o | overwrite)
            conf="y"
        ;;
        *)
            echo "Unknown flag $OPTARG"
            exit 1
        ;;
    esac
done

# Fail loudly rather than writing a partial secrets file. Every line below is a
# redirect, and without this the script reports success after writing nothing.
# No -u: the prompt loops read $conf before it is ever assigned.
set -eo pipefail

# Compose mounts ./.env into the container, so `docker compose up` before this
# script runs makes Docker create it as a directory. The -f test below is false
# for a directory, so without this guard the run "succeeds" having written none
# of the secrets.
if [ -e "$env_file" ] && [ ! -f "$env_file" ]
then
    echo "ERROR: $env_file exists and is not a regular file." >&2
    echo "Docker creates it as a directory when 'docker compose up' runs before" >&2
    echo "this script. Remove it and re-run:  rmdir $env_file" >&2
    exit 1
fi

if [ -f $env_file ]
then
    echo "WARNING: $env_file file already exists."
    echo "This script will overwrite the content of this file."
    until [ "$conf" = "y" -o "$conf" = "n" ]
    do
        read -e -p "Do you want to overwrite it? y/n " conf
        if [ "$conf" = "y" ]
        then
            conf=""
            break
        elif [ "$conf" = "n" ]
        then
            echo "Aborting."
            exit 0
        else 
            echo "Incorrect input!"
        fi
    done
fi

if [ "$deployment" = "" ]
then 
    echo "Do you want to install Bayanat natively or using Docker?"

    while true
    do
        read -e -p "Enter n for native installation, or d for Docker: " deployment
        
        if [ "$deployment" = "n" ]
        then
            echo "Installaing Bayanat natively."
            break
        elif [ "$deployment" = "d" ]
        then
            echo "Installing Bayanat using Docker Compose."
            break
        else
            echo "Incorrect input!"
        fi
    done
    
    if [ "$deployment" = "d" ]
    then
        while true
        do
            read -e -p "Enter media path: (autocomplete is on) " media_path
            if [ ! -d $media_path ]
            then
                until [ "$conf" = "y" -o "$conf" = "n" ]
                do
                    read -e -p "Media directory doesn't exist. Do you want to create it? y/n " conf
                    if [ "$conf" = "y" ]
                    then
                        echo "Creating Media directory."
                        if mkdir -p $media_path
                        then
                            echo "Media directory created seccessfully."
                            echo "Using $media_path as media directory."
                            break 2
                        else
                            echo "Error creating media directory"
                            conf=""
                            break
                        fi
                    elif [ "$conf" = "n" ]
                    then
                        echo "Please enter another directory"
                        conf=""
                        break
                    else 
                        echo "Incorrect input!"
                    fi
                done
            else
                echo "Using $media_path as media directory."
                break
            fi
        done    
    fi
fi


# Only prompt on a terminal. This script runs unattended in CI
# (.github/workflows/run-tests.yml), where a blocking read would hang the job.
if [ "$deployment" = "d" -a -z "$domain" -a -t 0 ]
then
    echo ""
    echo "Enter the domain Bayanat will be served on, e.g. bayanat.example.org."
    echo "Caddy will request a Let's Encrypt certificate for it automatically."
    echo "Leave blank to serve plain HTTP on port 80 (local use, or when you"
    echo "already run a TLS-terminating proxy in front of this stack)."
    read -e -p "Domain: " domain
fi

# A real domain means Caddy terminates TLS, so the app must mark its session
# cookie secure and redirect to HTTPS. Without one it would lock itself out.
if [ -z "$domain" ]
then
    domain=":80"
    force_https="False"
else
    force_https="True"
fi

echo "Generating secrets and environment file"
echo "FLASK_APP=run.py" > ./$env_file
echo "FLASK_DEBUG=0" >> ./$env_file
echo "" >> ./$env_file

echo "SECRET_KEY='$(openssl rand -base64 32)'" >> ./$env_file
echo "SECURITY_PASSWORD_SALT='$(openssl rand -base64 32)'" >> ./$env_file
echo "" >> ./$env_file

echo "SECURITY_TOTP_SECRETS='$(openssl rand -base64 32)'" >> ./$env_file
echo "SECURITY_TWO_FACTOR=True" >> ./$env_file
echo "SECURITY_TWO_FACTOR_RESCUE_MAIL=''" >> ./$env_file
echo "SECURITY_TWO_FACTOR_AUTHENTICATOR_VALIDITY=90" >> ./$env_file
echo "" >> ./$env_file

if [ "$deployment" = "d" ]
then
    echo "DOMAIN='$domain'" >> ./$env_file
    echo "SECURE_COOKIES=$force_https" >> ./$env_file
    echo "FORCE_HTTPS=$force_https" >> ./$env_file
    echo "" >> ./$env_file

    echo "MEDIA_PATH='$media_path'" >> ./$env_file
    echo "POSTGRES_USER=bayanat" >> ./$env_file
    echo "POSTGRES_PASSWORD='$(openssl rand -hex 32)'" >> ./$env_file
    echo "POSTGRES_DB=bayanat" >> ./$env_file
    echo "POSTGRES_HOST=postgres" >> ./$env_file
    echo "REDIS_HOST='redis'" >> ./$env_file
    echo "REDIS_PASSWORD='$(openssl rand -hex 32)'" >> ./$env_file
    echo "PYTHONUNBUFFERED=True" >> ./$env_file
    echo "REDIS_AOF_ENABLED=no" >> ./$env_file
    echo "" >> ./$env_file
fi

if [ "$deployment" = "d" ]
then
    if [ ! -f config.json ]
    then
        # config.json is bind-mounted into the containers. Docker would create
        # it as a directory if it did not exist, and the app would fail to
        # read it.
        echo "Creating config.json from config.sample.json"
        cp config.sample.json config.json
    fi

    # The containers run as uid 1000 (see the useradd in flask/Dockerfile).
    # On Linux, bind mounts keep the host's ownership, so every path the app
    # writes to must belong to that uid or it cannot even open its log file.
    # Docker creates missing bind-mount sources as root, so create them first.
    echo "Preparing writable directories for the container user"
    mkdir -p logs backups enferno/imports "$media_path"
    if ! chown -R 1000 logs backups enferno/imports "$media_path" config.json 2>/dev/null
    then
        echo ""
        echo "WARNING: could not change ownership of the data directories."
        echo "The application runs as uid 1000 and will fail to start without"
        echo "write access. Run this before 'docker compose up -d':"
        echo ""
        echo "  sudo chown -R 1000 logs backups enferno/imports $media_path config.json"
        echo ""
    fi
fi

echo "Completed environment file generation"
echo "Please inspect the environment file below"
echo ""
cat $env_file

exit 0