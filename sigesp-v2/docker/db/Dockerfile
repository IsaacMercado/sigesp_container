FROM postgres:9.2

# Fix sources for Debian Jessie (EOL)
# Remove dead postgres repos
RUN rm -rf /etc/apt/sources.list.d/*

RUN echo "deb [check-valid-until=no] http://archive.debian.org/debian jessie main" > /etc/apt/sources.list && \
    echo "deb [check-valid-until=no] http://archive.debian.org/debian-security jessie/updates main" >> /etc/apt/sources.list

RUN echo 'Acquire::Check-Valid-Until "false";' > /etc/apt/apt.conf.d/99no-check-valid-until && \
    echo 'Acquire::AllowInsecureRepositories "true";' >> /etc/apt/apt.conf.d/99allow-insecure

# Install libfaketime and locales
RUN apt-get update && apt-get install -y --force-yes --no-install-recommends \
    libfaketime \
    locales \
    && rm -rf /var/lib/apt/lists/*

# Generate Locale
RUN echo "es_VE.ISO-8859-15 ISO-8859-15" >> /etc/locale.gen && \
    locale-gen
