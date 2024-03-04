# syntax=docker/dockerfile:labs

FROM debian/eol:squeeze-slim

ADD https://github.com/wolfcw/libfaketime.git /usr/local/src/libfaketime

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        build-essential \
        python-apt \
    ; \
    cd /usr/local/src/libfaketime; \
    make; \
    make install; \
    cd /; \
    rm -rf /usr/local/src/libfaketime; \
    apt-mark markauto build-essential python-apt; \
    apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
    rm -rf /var/lib/apt/lists/*

# explicitly set user/group IDs
RUN set -eux; \
    groupadd -r postgres --gid=999; \
# https://salsa.debian.org/postgresql/postgresql-common/blob/997d842ee744687d99a2b2d95c1083a2615c79e8/debian/postgresql-common.postinst#L32-35
    useradd -r -g postgres --uid=999 --home-dir=/var/lib/postgresql --shell=/bin/bash postgres; \
# also create the postgres user's home directory with appropriate permissions
# see https://github.com/docker-library/postgres/issues/274
    mkdir -p /var/lib/postgresql; \
    chown -R postgres:postgres /var/lib/postgresql

# persistent / runtime deps
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        curl \
        ca-certificates \
        supervisor \
        postgresql \
        postgresql-contrib \
        xz-utils \
    ; \
    rm -rf /var/lib/apt/lists/*

ENV APACHE_CONFDIR /etc/apache2
ENV APACHE_ENVVARS $APACHE_CONFDIR/envvars

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        apache2 \
        apache2-utils \
        libapache2-mod-php5 \
        php5 \
        php5-pgsql \
    ; \
    rm -rf /var/lib/apt/lists/*; \
    \
# generically convert lines like
#   export APACHE_RUN_USER=www-data
# into
#   : ${APACHE_RUN_USER:=www-data}
#   export APACHE_RUN_USER
# so that they can be overridden at runtime ("-e APACHE_RUN_USER=...")
    sed -ri 's/^export ([^=]+)=(.*)$/: ${\1:=\2}\nexport \1/' "$APACHE_ENVVARS"; \
    \
# setup directories and permissions
    . "$APACHE_ENVVARS"; \
    for dir in \
        "$APACHE_LOCK_DIR" \
        "$APACHE_RUN_DIR" \
        "$APACHE_LOG_DIR" \
    ; do \
        rm -rvf "$dir"; \
        mkdir -p "$dir"; \
        chown "$APACHE_RUN_USER:$APACHE_RUN_GROUP" "$dir"; \
# allow running as an arbitrary user (https://github.com/docker-library/php/issues/743)
        chmod 1777 "$dir"; \
    done; \
    \
# delete the "index.html" that installing Apache drops in here
    rm -rvf /var/www/html/*; \
    \
# logs should go to stdout / stderr
    ln -sfT /dev/stderr "$APACHE_LOG_DIR/error.log"; \
    ln -sfT /dev/stdout "$APACHE_LOG_DIR/access.log"; \
    ln -sfT /dev/stdout "$APACHE_LOG_DIR/other_vhosts_access.log"; \
    chown -R --no-dereference "$APACHE_RUN_USER:$APACHE_RUN_GROUP" "$APACHE_LOG_DIR"

RUN set -eux; \
    { \
        echo "<VirtualHost *:80>"; \
        echo "\tServerName localhost"; \
        echo "\tDocumentRoot /var/www/html"; \
        echo '\tDirectoryIndex disabled'; \
        echo '\tDirectoryIndex inicio.html index.php index.html'; \
        echo "\tSetEnv LD_PRELOAD /usr/local/lib/faketime/libfaketime.so.1"; \
        echo "\t<Directory /var/www/html>"; \
        echo "\t\tOptions Indexes FollowSymLinks MultiViews"; \
        echo "\t\tAllowOverride All"; \
        echo "\t\tOrder allow,deny"; \
        echo "\t\tallow from all"; \
        echo "\t</Directory>"; \
        echo "</VirtualHost>"; \
    } | tee "$APACHE_CONFDIR/sites-available/docker-php.conf" \
    && a2dissite 000-default \
    && a2ensite docker-php.conf; \
    mkdir -p /var/www/html; \
    echo "<?php phpinfo();" > /var/www/index.php

RUN echo "listen_addresses = '*'" >> /etc/postgresql/8.4/main/postgresql.conf

# change pg_hba.conf
RUN sed -i 's/127.0.0.1\/32/0.0.0.0\/0/g' /etc/postgresql/8.4/main/pg_hba.conf

COPY template.sql /tmp/template.sql

RUN set -eux; \
    service postgresql start; \
    su - postgres -c "psql -f /tmp/template.sql"; \
    service postgresql stop; \
    rm -rf /tmp/template.sql

WORKDIR /var/www/html

STOPSIGNAL SIGINT

EXPOSE 80 5432

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf

CMD ["/usr/bin/supervisord"]
