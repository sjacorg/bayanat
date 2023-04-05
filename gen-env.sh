#!/bin/bash
echo "Bayanat .env Generation Script"

if [ -f .env ]
then
    echo "WARNING: .env file already exists."
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

echo "Do you want to install Bayanat natively or using Docker?"

while true
do
    read -e -p "Enter n for native installation, or d for Docker: " nd
    
    if [ "$nd" = "n" ]
    then
        echo "Installaing Bayanat natively."
        break
    elif [ "$nd" = "d" ]
    then
        echo "Installing Bayanat using Docker Compose."
        break
    else
        echo "Incorrect input!"
    fi
done

echo "Generating Secrets and .env file"
echo "Do you want to use localfile system or S3 Storage to store media files?"
while true
do
    read -e -p "Enter l for local filesystem, or s for S3: " local
    
    if [ "$local" = "l" ]
    then
        FILESYSTEM_LOCAL="True"
        echo "Using local filesystem."
        break
    elif [ "$local" = "s" ]
    then
        FILESYSTEM_LOCAL="False"
        echo "Using S3 storage."
        break
    else
        echo "Incorrect input!"
    fi
done  

if [ "$FILESYSTEM_LOCAL" != "True" ]
then
    echo "Please enter S3 authentication credentials."
    read -e -p "Access Key ID: " AWS_ACCESS_KEY_ID
    read -e -p "Secret Access Key: " AWS_SECRET_ACCESS_KEY
    read -e -p "S3 Bucket name: " S3_BUCKET
    read -e -p "S3 Region: " AWS_REGION
elif [ "$nd" = "d" ]
then
    while true
    do
        read -e -p "Enter media path: (autocomplete is on) " MEDIA_PATH
        if [ ! -d $MEDIA_PATH ]
        then
            until [ "$conf" = "y" -o "$conf" = "n" ]
            do
                read -e -p "Media directory doesn't exist. Do you want to create it? y/n " conf
                if [ "$conf" = "y" ]
                then
                    echo "Creating Media directory."
                    if mkdir -p $MEDIA_PATH
                    then
                        echo "Media directory created seccessfully."
                        echo "Using $MEDIA_PATH as media directory."
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
            echo "Using $MEDIA_PATH as media directory."
            break
        fi
    done    
fi

echo "Generating .env file..."
echo "FLASK_APP=run.py" > ./.env
echo "FLASK_DEBUG=0" >> ./.env
echo "FILESYSTEM_LOCAL=$FILESYSTEM_LOCAL" >> ./.env
echo "" >> ./.env

echo "SECRET_KEY='$(openssl rand -base64 32)'" >> ./.env
echo "SECURITY_PASSWORD_SALT='$(openssl rand -base64 32)'" >> ./.env
echo "" >> ./.env

echo "SECURITY_TOTP_SECRETS='$(openssl rand -base64 32)'" >> ./.env
echo "SECURITY_TWO_FACTOR=True" >> ./.env
echo "SECURITY_TWO_FACTOR_RESCUE_MAIL=''" >> ./.env
echo "SECURITY_TWO_FACTOR_AUTHENTICATOR_VALIDITY=90" >> ./.env
echo "" >> ./.env

if [ "$FILESYSTEM_LOCAL" != "True" ]
then
    echo "AWS_ACCESS_KEY_ID='$AWS_ACCESS_KEY_ID'" >> ./.env
    echo "AWS_SECRET_ACCESS_KEY='$AWS_SECRET_ACCESS_KEY'" >> ./.env
    echo "S3_BUCKET='$S3_BUCKET'" >> ./.env
    echo "AWS_REGION='$AWS_REGION'" >> ./.env
    echo "" >> ./.env
fi

if [ "$nd" = "d" ]
then
    echo "MEDIA_PATH='$MEDIA_PATH'" >> ./.env
    echo "POSTGRES_USER=bayanat" >> ./.env
    echo "POSTGRES_PASSWORD='$(openssl rand -hex 32)'" >> ./.env
    echo "POSTGRES_DB=bayanat" >> ./.env
    echo "POSTGRES_HOST=postgres" >> ./.env
    echo "REDIS_HOST='redis'" >> ./.env
    echo "REDIS_PASSWORD='$(openssl rand -hex 32)'" >> ./.env
    echo "PYTHONUNBUFFERED=True" >> ./.env
    echo "REDIS_AOF_ENABLED=no" >> ./.env
    echo "" >> ./.env
fi

echo "ETL_TOOL=True" >> ./.env
echo "ETL_PATH_IMPORT=True" >> ./.env
echo "ETL_ALLOWED_PATH='/home/ubuntu/test'" >> ./.env
echo "OCR_ENABLED=True" >> ./.env
echo "SHEET_IMPORT=True" >> ./.env
echo "" >> ./.env

echo "MISSING_PERSONS=True" >> ./.env
echo "" >> ./.env

echo "RECAPTCHA_ENABLED=False" >> ./.env
echo "RECAPTCHA_PUBLIC_KEY=''" >> ./.env
echo "RECAPTCHA_PRIVATE_KEY=''" >> ./.env
echo "" >> ./.env

echo "MAPS_API_ENDPOINT='https://{s}.tile.osm.org/{z}/{x}/{y}.png'" >> ./.env

echo "GOOGLE_MAPS_API_KEY=''" >> ./.env
echo "" >> ./.env

echo "GOOGLE_CLIENT_ID=''" >> ./.env
echo "GOOGLE_CLIENT_SECRET=''" >> ./.env

echo "" >> ./.env
echo "DEDUP_TOOL=False" >> ./.env
echo "DEDUP_LOW_DISTANCE=0.3" >> ./.env
echo "DEDUP_MAX_DISTANCE=0.5" >> ./.env
echo "DEDUP_BATCH_SIZE=30" >> ./.env

echo "Completed .enf file generation"
exit 0