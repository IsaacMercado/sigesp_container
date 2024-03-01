# syntax=docker/dockerfile:labs

FROM debian/eol:squeeze-slim

RUN set -eux; \
    { \
    echo 'Package: php*'; \
    echo 'Pin: release *'; \
    echo 'Pin-Priority: -1'; \
    } > /etc/apt/preferences.d/no-debian-php

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

RUN echo "listen_addresses = '*'" >> /etc/postgresql/8.4/main/postgresql.conf
RUN sed -i 's/127.0.0.1\/32/0.0.0.0\/0/g' /etc/postgresql/8.4/main/pg_hba.conf

ENV APACHE_CONFDIR /etc/apache2
ENV APACHE_ENVVARS $APACHE_CONFDIR/envvars

ENV PHP_INI_DIR /usr/local/etc/php
RUN set -eux; \
    mkdir -p "$PHP_INI_DIR/conf.d"; \
    # allow running as an arbitrary user (https://github.com/docker-library/php/issues/743)
    [ ! -d /var/www/html ]; \
    mkdir -p /var/www/html; \
    chown www-data:www-data /var/www/html; \
    chmod 1777 /var/www/html

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        apache2 \
        apache2-utils \
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
        echo '\t<FilesMatch \.php$>'; \
        echo '\t\tSetHandler application/x-httpd-php'; \
        echo '\t</FilesMatch>'; \
        echo "\tServerName localhost"; \
        echo "\tDocumentRoot /var/www/html"; \
        echo '\tDirectoryIndex disabled'; \
        echo '\tDirectoryIndex index.php index.html'; \
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

ADD http://museum.php.net/php5/php-5.2.17.tar.gz /tmp/php-5.2.17.tar.gz

RUN set -eux; \
    tar xvfz /tmp/php-5.2.17.tar.gz --directory /tmp; \
    mv /tmp/php-5.2.17 /usr/local/src/php; \
    rm /tmp/php-5.2.17.tar.gz

RUN set -eux; \
    \
    savedAptMark="$(dpkg --get-selections | awk '{print $1}')"; \
    devDeps="\
        python-apt \
        build-essential \
        apache2-dev \
        libxml2-dev \
        libcurl4-openssl-dev \
        libpcre3-dev \
        libbz2-dev \
        libjpeg-dev \
        libpng12-dev \
        libfreetype6-dev \
        libt1-dev \
        libmcrypt-dev \
        libmhash-dev \
        freetds-dev \
        unixodbc-dev \
        postgresql-server-dev-8.4 \
        libmysqlclient-dev \
        libxslt1-dev \
        libldb-dev \
        libldap2-dev \
        libsasl2-dev \
    "; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        $devDeps \
        libsybdb5 \
        libmhash2 \
        libmcrypt4 \
        libltdl7 \
        libt1-5 \
        libfreetype6 \
        libpng12-0 \
    ; \
    cd /usr/local/src/php; \
    ./configure \
        --mandir=/usr/share/man \
        --with-config-file-path="$PHP_INI_DIR" \
        --with-config-file-scan-dir="$PHP_INI_DIR/conf.d" \
        --includedir=/usr/include \
        --disable-debug \
        --with-regex=php \
        --disable-rpath \
        --disable-static \
        --disable-posix \
        --with-pic \
        --with-layout=GNU \
        --with-pear=/usr/share/php \
        --enable-calendar \
        --enable-sysvsem \
        --enable-sysvshm \
        --enable-sysvmsg \
        --enable-bcmath \
        --with-bz2 \
        --enable-ctype \
        --without-gdbm \
        --with-iconv \
        --enable-exif \
        --enable-ftp \
        --enable-cli \
        --with-gettext \
        --enable-mbstring \
        --with-pcre-regex \
        --enable-shmop \
        --enable-sockets \
        --enable-wddx \
        --with-mcrypt \
        --with-zlib \
        --enable-pdo \
        --with-curl \
        --enable-inline-optimization \
        --enable-xml \
        --enable-pcntl \
        --enable-mbregex \
        --with-mhash \
        --with-xsl \
        --enable-zip \
        --with-gd \
        --with-jpeg-dir=/usr/lib \
        --with-png-dir=/usr/lib \
        --with-openssl \
        --with-kerberos \
        --enable-gd-native-ttf \
        --with-t1lib=/usr \
        --with-freetype-dir=/usr \
        --with-ldap \
        --with-kerberos=/usr \
        --with-unixODBC=shared,/usr \
        --with-imap-ssl \
        --with-mssql \
        --with-sqlite \
        --with-pgsql \
        --with-pdo-pgsql \
        --enable-soap \
        --with-pdo-sqlite \
        # mysql
        --with-mysqli=/usr/bin/mysql_config \
        --with-pdo-mysql \
        --with-mysql \
        --with-mysqli \
        --disable-cgi \
        --with-apxs2=/usr/bin/apxs2 \
        ; \
    make -j "$(nproc)"; \
    find -type f -name '*.a' -delete; \
    make install; \
    find \
        /usr/local \
        -type f \
        -perm '/0111' \
        -exec sh -euxc ' \
            strip --strip-all "$@" || : \
        ' -- '{}' + \
    ; \
    make clean; \
    \
# https://github.com/docker-library/php/issues/692 (copy default example "php.ini" files somewhere easily discoverable)
    cp -v php.ini-* "$PHP_INI_DIR/"; \
	cd /; \
	\
# reset apt-mark's "manual" list so that "purge --auto-remove" will remove all build dependencies
	apt-mark markauto '.*' > /dev/null; \
    apt-mark markauto $devDeps; \
	[ -z "$savedAptMark" ] || apt-mark unmarkauto $savedAptMark; \
	find /usr/local -type f -executable -exec ldd '{}' ';' \
		| awk '/=>/ { so = $(NF-1); if (index(so, "/usr/local/") == 1) { next }; gsub("^/(usr/)?", "", so); print so }' \
		| sort -u \
		| xargs -r dpkg-query --search \
		| cut -d: -f1 \
		| sort -u \
		| xargs -r apt-mark manual \
	; \
	apt-get purge -y --auto-remove -o APT::AutoRemove::RecommendsImportant=false; \
	rm -rf /var/lib/apt/lists/*; \
	\
# update pecl channel definitions https://github.com/docker-library/php/issues/443
	pecl update-channels; \
	rm -rf /tmp/pear ~/.pearrc; \
	\
# smoke test
    a2enmod php5; \
    php --version

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends proftpd; \
    rm -rf /var/lib/apt/lists/*

WORKDIR /var/www/html
STOPSIGNAL SIGINT

EXPOSE 80 5432

COPY supervisord.conf /etc/supervisor/conf.d/supervisord.conf
CMD ["/usr/bin/supervisord"]
