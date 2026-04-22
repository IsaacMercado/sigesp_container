#!/bin/bash
set -e

# ====================================================================
# SCRIPT DE MIGRACIÓN: Postgres SQL_ASCII a LATIN9
# ====================================================================
# IMPORTANTE: Este script usa `docker exec` para comunicarse con 
# los contenedores directamente. Esto asegura que funcionará 
# exactamente igual tanto en tu entorno WSL local, como en el 
# servidor en la nube asumiendo que también utiliza Docker y los
# mismos nombres de contenedores, sin requerir instalar `psql` 
# en la máquina host.
# ====================================================================

# 1. Configurar nombres de los contenedores
SOURCE_CONTAINER="sigesp-v2"
TARGET_CONTAINER="sigesp-postgres-v2-temp"
DB_USER="postgres"

echo "Obteniendo bases de datos desde $SOURCE_CONTAINER..."

# Sacar solo los nombres de las bases de datos de usuario (se excluye la de sistema "postgres")
DATABASES=$(docker exec -u $DB_USER $SOURCE_CONTAINER psql -t -A -c "SELECT datname FROM pg_database WHERE datistemplate = false AND datname != 'postgres';")

for DB in $DATABASES; do
    # Limpiar espacios en blanco
    DB=$(echo $DB | xargs)
    if [ -z "$DB" ]; then continue; fi

    echo "=================================="
    echo "Procesando la base de datos: $DB"
    echo "=================================="

    # 1. Crear base de datos en el contenedor destino forzando LATIN9
    echo "Creando base de datos en contenedor destino..."
    docker exec -u $DB_USER $TARGET_CONTAINER psql -c "DROP DATABASE IF EXISTS \"$DB\";" > /dev/null 2>&1
    docker exec -u $DB_USER $TARGET_CONTAINER psql -c "CREATE DATABASE \"$DB\" ENCODING 'LATIN9';" > /dev/null 2>&1
    
    # 2. Respaldar y migrar volcado entre contenedores. 
    # Forzar client_encoding a LATIN9 (-E LATIN9)
    echo "Migrando datos..."
    docker exec -u $DB_USER $SOURCE_CONTAINER pg_dump -U $DB_USER -E LATIN9 "$DB" | \
      docker exec -i -u $DB_USER $TARGET_CONTAINER psql -q -U $DB_USER -d "$DB" > /dev/null
    
    echo "Completado: $DB"
done

echo "=================================="
echo "Migración terminada exitosamente."