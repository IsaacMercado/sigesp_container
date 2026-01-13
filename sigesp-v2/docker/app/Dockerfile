# syntax=docker/dockerfile:labs
FROM debian:bookworm-slim

# prevent Debian's PHP packages from being installed
RUN set -eux; \
    { \
        echo 'Package: php*'; \
        echo 'Pin: release *'; \
        echo 'Pin-Priority: -1'; \
    } > /etc/apt/preferences.d/no-debian-php

# persistent / runtime deps
RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        libfaketime \
        locales \
        ca-certificates \
        wget \
        xz-utils \
        make \
        gcc \
        libc-dev \
    ; \
    rm -rf /var/lib/apt/lists/*

RUN echo "es_VE.ISO-8859-15 ISO-8859-15" >> /etc/locale.gen && \
    locale-gen

ENV PHP_INI_DIR=/usr/local/etc/php
RUN set -eux; \
    mkdir -p "$PHP_INI_DIR/conf.d"; \
    [ ! -d /var/www/html ]; \
    mkdir -p /var/www/html; \
    chown www-data:www-data /var/www/html; \
    chmod 1777 /var/www/html

ENV APACHE_CONFDIR=/etc/apache2
ENV APACHE_ENVVARS=$APACHE_CONFDIR/envvars

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends apache2; \
    rm -rf /var/lib/apt/lists/*; \
    sed -ri 's/^export ([^=]+)=(.*)$/: ${\1:=\2}\nexport \1/' "$APACHE_ENVVARS"; \
    . "$APACHE_ENVVARS"; \
    for dir in \
        "$APACHE_LOCK_DIR" \
        "$APACHE_RUN_DIR" \
        "$APACHE_LOG_DIR" \
        "$APACHE_RUN_DIR/socks" \
    ; do \
        rm -rvf "$dir"; \
        mkdir -p "$dir"; \
        chown "$APACHE_RUN_USER:$APACHE_RUN_GROUP" "$dir"; \
        chmod 1777 "$dir"; \
    done; \
    rm -rvf /var/www/html/*; \
    ln -sfT /dev/stderr "$APACHE_LOG_DIR/error.log"; \
    ln -sfT /dev/stdout "$APACHE_LOG_DIR/access.log"; \
    ln -sfT /dev/stdout "$APACHE_LOG_DIR/other_vhosts_access.log"; \
    chown -R --no-dereference "$APACHE_RUN_USER:$APACHE_RUN_GROUP" "$APACHE_LOG_DIR"

RUN a2dismod mpm_event && a2enmod mpm_prefork

RUN { \
        echo '<FilesMatch \.php$>'; \
        echo '\tSetHandler application/x-httpd-php'; \
        echo '</FilesMatch>'; \
        echo; \
        echo 'DirectoryIndex disabled'; \
        echo 'DirectoryIndex index.php index.html'; \
        echo; \
        echo '<Directory /var/www/>'; \
        echo '\tOptions -Indexes'; \
        echo '\tAllowOverride All'; \
        echo '</Directory>'; \
    } | tee "$APACHE_CONFDIR/conf-available/docker-php.conf" \
    && a2enconf docker-php

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends \
        python3-apt \
        build-essential \
        libjpeg-dev \
        libpng-dev \
        libfreetype6-dev \
        libmcrypt-dev \
        libkrb5-dev \
        libltdl-dev \
        libpq-dev \
        apache2-dev \
        libargon2-dev \
        libonig-dev \
        libreadline-dev \
        libsodium-dev \
        libsqlite3-dev \
        default-libmysqlclient-dev \
        zlib1g-dev \
        libpcre3-dev \
        libbz2-dev \
        libmhash-dev \
        freetds-dev \
        unixodbc-dev \
        libldb-dev \
        libldap2-dev \
        libsasl2-dev; \
    rm -rf /var/lib/apt/lists/*

RUN set -eux; \
    wget https://www.openssl.org/source/old/1.0.2/openssl-1.0.2u.tar.gz; \
    tar -xzf openssl-1.0.2u.tar.gz -C /usr/src/ ;\
    rm openssl-1.0.2u.tar.gz ;\
    cd /usr/src/openssl-1.0.2u ;\
    ./config shared --openssldir=/opt/openssl-1.0.2/ enable-ec_nistp_64_gcc_128 ;\
    make depend ;\
    make -j$(nproc) ;\
    make install ;\
    ln -s /opt/openssl-1.0.2/lib /opt/openssl-1.0.2/lib/x86_64-linux-gnu; \
    echo "/opt/openssl-1.0.2/lib" > /etc/ld.so.conf.d/openssl.conf; \
    ldconfig

RUN set -eux; \
    cd /opt; \
    wget --no-check-certificate https://wiki.olvy.net/download/c-client.tar.gz; \
    tar xzf c-client.tar.gz; \
    cd /opt/imap-2007f; \
    sed -i 's|^SSLDIR=.*|SSLDIR=/opt/openssl-1.0.2|' src/osdep/unix/Makefile; \
    sed -i 's|^EXTRACFLAGS=.*|EXTRACFLAGS=-fPIC|' Makefile; \
    make slx IP6=4

RUN set -eux; \
    wget -O curl-7.88.1.tar.gz https://github.com/curl/curl/releases/download/curl-7_88_1/curl-7.88.1.tar.gz; \
    tar xzf curl-7.88.1.tar.gz; \
    cd curl-7.88.1; \
    ./configure --prefix=/opt/curl --with-ssl=/opt/openssl-1.0.2 --with-ca-path=/etc/ssl/certs; \
    make -j$(nproc); \
    make install; \
    cd ..; \
    rm -rf curl-7.88.1 curl-7.88.1.tar.gz

# Attempt to get freetype-config from old debian package
RUN wget --no-check-certificate http://archive.debian.org/debian-security/pool/updates/main/f/freetype/libfreetype6-dev_2.6.3-3.2+deb9u2_amd64.deb -O libfreetype.deb \
    || wget --no-check-certificate https://web.archive.org/web/20210101000000/http://archive.debian.org/debian-security/pool/updates/main/f/freetype/libfreetype6-dev_2.6.3-3.2+deb9u2_amd64.deb -O libfreetype.deb; \
    dpkg --fsys-tarfile libfreetype.deb \
    | tar xOf - ./usr/bin/freetype-config > /usr/bin/freetype-config \
    && chmod +x /usr/bin/freetype-config \
    && rm libfreetype.deb

# Compile Postgres Client libraries (or full server just for libs) 
# Note: Separated services, but we need libs for PHP build.
RUN set -eux; \
    wget -O postgresql.tar.bz2 https://ftp.postgresql.org/pub/source/v9.2.24/postgresql-9.2.24.tar.bz2; \
    tar -xjf postgresql.tar.bz2 -C /usr/src; \
    rm postgresql.tar.bz2; \
    cd /usr/src/postgresql-9.2.24; \
    ./configure --prefix=/usr/local/pgsql-9.2 --without-readline; \
    make -j$(nproc); \
    make install; \
    rm -rf /usr/src/postgresql-9.2.24

RUN set -eux; \
    wget https://launchpad.net/ubuntu/+archive/primary/+sourcefiles/libxml2/2.8.0+dfsg1-5ubuntu2.5/libxml2_2.8.0+dfsg1.orig.tar.gz -O libxml2.tar.gz; \
    tar -xzf libxml2.tar.gz; \
    cd libxml2-2.8.0+dfsg1; \
    ./configure --prefix=/opt/libxml2-2.8.0 --without-python; \
    make -j$(nproc); \
    make install; \
    cd ..; \
    rm -rf libxml2-2.8.0+dfsg1 libxml2.tar.gz

RUN set -eux; \
    wget https://download.gnome.org/sources/libxslt/1.1/libxslt-1.1.28.tar.xz -O libxslt.tar.xz; \
    tar -xJf libxslt.tar.xz; \
    cd libxslt-1.1.28; \
    ./configure --prefix=/opt/libxslt-1.1.28 --with-libxml-prefix=/opt/libxml2-2.8.0 --without-python --without-crypto; \
    make -j$(nproc); \
    make install; \
    cd ..; \
    rm -rf libxslt-1.1.28 libxslt.tar.xz

ENV PHP_VERSION=5.2.17
ENV PHP_CFLAGS="-fstack-protector-strong -fpic -fpie -O2 -D_LARGEFILE_SOURCE -D_FILE_OFFSET_BITS=64"
ENV PHP_CPPFLAGS="$PHP_CFLAGS"
ENV PHP_LDFLAGS="-Wl,-O1 -pie"

RUN set -eux; \
    wget http://museum.php.net/php5/php-${PHP_VERSION}.tar.gz; \
    tar xzf php-${PHP_VERSION}.tar.gz

RUN set -eux; \
    gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)"; \
    cd php-${PHP_VERSION}; \
    sed -i 's/unixd_config/ap_unixd_config/g' sapi/apache2handler/php_functions.c; \
    sed -i 's/unixd_config/ap_unixd_config/g' sapi/apache2handler/sapi_apache2.c; \
    sed -i 's/ap_unixd_config_rec/unixd_config_rec/g' sapi/apache2handler/php_functions.c; \
    sed -i 's/ap_unixd_config_rec/unixd_config_rec/g' sapi/apache2handler/sapi_apache2.c; \
    export \
        CFLAGS="$PHP_CFLAGS -fcommon" \
        CPPFLAGS="$PHP_CPPFLAGS" \
        LDFLAGS="$PHP_LDFLAGS" \
        PHP_BUILD_PROVIDER='https://github.com/IsaacMercado/sigesp_container' \
        PHP_UNAME='Linux - Docker' \
    ; \
    ln -s /usr/lib/x86_64-linux-gnu/libjpeg.so /usr/lib/libjpeg.so ; \
    ln -s /usr/lib/x86_64-linux-gnu/libpng.so /usr/lib/libpng.so ; \
    ./configure \
        --build="$gnuArch" \
        --with-config-file-path="$PHP_INI_DIR" \
        --with-config-file-scan-dir="$PHP_INI_DIR/conf.d" \
        --enable-bcmath \
        --enable-opcache \
        --enable-ftp \
        --enable-libxml \
        --with-libxml-dir=/opt/libxml2-2.8.0 \
        --enable-mbregex \
        --enable-mbstring \
        --enable-soap \
        --enable-sockets \
        --enable-zip \
        --with-curl=/opt/curl \
        --with-freetype-dir=/usr \
        --with-gd \
        --with-gettext \
        --with-mcrypt \
        --with-openssl=/opt/openssl-1.0.2 \
        --with-openssl-dir=/opt/openssl-1.0.2 \
        --with-zlib \
        --with-zlib-dir=/usr \
        --with-xsl=/opt/libxslt-1.1.28 \
        --enable-calendar \
        --enable-gd-native-ttf \
        --with-jpeg-dir=/usr/lib/x86_64-linux-gnu \
        --with-png-dir=/usr/lib/x86_64-linux-gnu \
        --with-imap=/opt/imap-2007f \
        --with-imap-ssl \
        --with-pdo-sqlite=/usr \
        --with-sqlite3=/usr \
        --with-pgsql=/usr/local/pgsql-9.2 \
        --with-pdo-pgsql=/usr/local/pgsql-9.2 \
        --enable-option-checking=fatal \
        --with-mhash \
        --with-pic \
        --with-password-argon2 \
        --with-sodium=shared \
        --enable-sodium \
        --with-iconv \
        --with-readline \
        --disable-phpdbg \
        --with-pear \
        --enable-cli \
        --disable-cgi \
        --with-apxs2 \
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
    cp -v php.ini-* "$PHP_INI_DIR/"; \
    cd /; \
    rm -rf php-${PHP_VERSION}*; \
    pecl update-channels; \
    rm -rf /tmp/pear ~/.pearrc; \
    php --version

COPY docker/app/docker-php-entrypoint /usr/local/bin/
RUN chmod +x /usr/local/bin/docker-php-entrypoint && sed -i 's/\r$//' /usr/local/bin/docker-php-entrypoint

ENTRYPOINT ["docker-php-entrypoint"]
STOPSIGNAL SIGWINCH

COPY docker/app/apache2-foreground /usr/local/bin/
RUN chmod +x /usr/local/bin/apache2-foreground && sed -i 's/\r$//' /usr/local/bin/apache2-foreground

WORKDIR /var/www/html

EXPOSE 80
CMD ["apache2-foreground"]
