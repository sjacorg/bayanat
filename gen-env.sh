#!/bin/bash
echo "Bayanat Environment Generation Script"

deployment=""
env_file=.env

while getopts "dne:o" option; do
    case $option in
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

echo "" >> ./$env_file

echo "Completed environment file generation"
echo "Please inspect the environment file below"
echo ""
cat $env_file

exit 0