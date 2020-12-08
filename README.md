Bayanat v1.0
=====================

Manual Installation
-------------------
Install the latest version of [Nginx](https://www.nginx.com/resources/wiki/start/topics/tutorials/install/).

Install the following packages: 

```
# apt install build-essential python3-dev libjpeg8-dev libzip-dev libxml2-dev libssl-dev libffi-dev libxslt1-dev libmysqlclient-dev libncurses5-dev python-setuptools postgresql postgresql-contrib python3-pip libpq-dev git redis-server
```

Install virtualenv:

```
$ pip3 install virtualenv
```

Clone the repository:

```
$ git clone git@github.com:sjacorg/bayanat.git
```

Install the rest of the dependencies:

```    
$ cd bayanat 

$ virtualenv env  -p python3

$ source env/bin/activate 

$ pip3 install -r requirements.txt
```

Edit the settings.py and change the values to suit your needs, specifically you can change Flask security settings, security keys, Redis DB, Postgres settings, password salts, and Flask mail.

Next, Postgres user and database can be created:

```
$ sudo -u postgres createuser --interactive
$ createdb user
```

After that, you should create your admin user, run the following command:

```
$ export FLASK_APP=run.py
$ flask create-db
$ flask install 
```

and follow the instructions, this will create your first user and first admin role.

To run the system locally, you can use a management command:

```
$ flask run
```

Example Nginx config file:

```
/etc/nginx/conf.d/test.conf

server {
listen 80 ssl;
server_name example.com;
# set based on your required media upload size
client_max_body_size 100M;
root /path/to/bayanat;
add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
location /static {
    alias /path/to/bayahat/enferno/static;
    expires max;
    }
#deny access to git and dot files
location ~ /\. {
deny all;
return 404;
}
#deny direct access to script and sensitive files
location ~* \.(pl|cgi|py|sh|lua|log|md5)$ {
    return 444;
    }
location / {

    add_header Strict-Transport-Security "max-age=31536000; includeSubDomains" always;
    proxy_set_header X-Forward-For $proxy_add_x_forwarded_for;
    proxy_set_header Host $http_host;
    proxy_redirect off;
    proxy_pass http://127.0.0.1:5000;
}
```

The following service can be created to run the app as a daemon:

```
/etc/systemd/system/bayanat.service

[Unit]
Description=UWSGI instance to serve Bayanat
After=syslog.target
[Service]
User=<user>
Group=<user>
WorkingDirectory=/path/to/bayanat
Environment="FLASK_DEBUG=0"
ExecStart=/path/to/bayanat/env/bin/uwsgi --master --enable-threads --threads 2  --processes 4 --http 127.0.0.1:5000  -w run:app --home env
Restart=always
KillSignal=SIGQUIT
Type=notify
StandardError=syslog
NotifyAccess=all
[Install]
WantedBy=multi-user.target
```

[Certbot](https://certbot.eff.org/) can be used to easily setup HTTPS with Nginx.

Once Nginx and the service is correctly configured, the app can be started:

Running Celery
-------------

`celery -A enfenro.tasks worker`

you can add `-b` to activate Celery heartbeat (periodic tasks) 

A sample task that runs within the app context has been prepared for you within the `enfenro/tasks/__init__.py` file, this is helpful if you have background tasks that interact with your SQLAlchemy models. 

Celery can also be run as a service:

```
[Unit]
Description=Celery Service
After=network.target
[Service]
User={{user_name}}
Group={{user_name}}
WorkingDirectory=/path/to/bayanat/
Environment="PATH=/path/to/bayanat/env/bin"
Environment="FLASK_DEBUG=0"
ExecStart=/home/path/to/bayanat/env/bin/celery -A enferno.tasks -c 4  worker -B
[Install]
WantedBy=multi-user.target
```

Using S3 for media uploads
-------------
By default media uploads will go into a private "media" directory, to use S3 instead, change the 
`FILESYSTEM_LOCAL` setting to false within the settings.py file, don't forget to update your s3 key/secret and bucket name. 

Running the system using Docker
-------------
Adjust the configuration inside the ".env" and "Dockerfile" files, then simply run the following command: 

```
docker-compose up --build
```

When all system components are built and show a running status, you will need to create the database structure and the admin user
using the following commands: 
```
$ docker exec -it <container> flask create-db
```

```
$ docker exec -it <container> flask install
```

License
-------------
This system is distributed WITHOUT ANY WARRANTY under the GNU Affero General Public License v3.0. 

