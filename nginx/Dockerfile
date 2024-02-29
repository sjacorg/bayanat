FROM bitnami/nginx:1.24 as base
VOLUME /opt/bitnami/nginx/conf
COPY --chown=1001 nginx.conf /opt/bitnami/nginx/conf/

FROM base as dev
COPY --chown=1001 bayanat_dev.conf /opt/bitnami/nginx/conf/server_blocks/

FROM base as prod
COPY --chown=1001 bayanat.conf /opt/bitnami/nginx/conf/server_blocks/
