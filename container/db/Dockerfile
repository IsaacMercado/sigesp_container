FROM postgres:9.6

ADD https://github.com/wolfcw/libfaketime.git /usr/local/src/libfaketime

# Fix sources for Debian Stretch (EOL)
# Remove dead postgres repos
RUN rm -rf /etc/apt/sources.list.d/*

RUN echo "deb [check-valid-until=no] http://archive.debian.org/debian stretch main" > /etc/apt/sources.list && \
    echo "deb [check-valid-until=no] http://archive.debian.org/debian-security stretch/updates main" >> /etc/apt/sources.list

RUN echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until && \
    echo 'Acquire::AllowInsecureRepositories "true";' >> /etc/apt/apt.conf.d/99allow-insecure

RUN apt-get update \
    && apt-get install -y --force-yes --no-install-recommends \
        build-essential \
    && cd /usr/local/src/libfaketime \
    && make \
    && make install \
    && cd / \
    && rm -rf /usr/local/src/libfaketime \
    && apt-get purge -y --auto-remove build-essential \
    && rm -rf /var/lib/apt/lists/*

# Install libfaketime and locales
RUN apt-get update \
    # && apt-get upgrade -y \
    && apt-get install -y --force-yes --no-install-recommends \
        locales \
        vim \
    && rm -rf /var/lib/apt/lists/*

# Generate Locale
RUN echo "es_VE.ISO-8859-15 ISO-8859-15" >> /etc/locale.gen && \
    locale-gen
