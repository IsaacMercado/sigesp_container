#!/bin/bash
set -e

if [ -z "$1" ] || [ -z "$2" ]; then
    echo "Uso: $0 <base_de_datos_origen> <nueva_base_de_datos>"
    echo "Ejemplo: $0 db_cida_2025 db_cida_2026"
    exit 1
fi

SOURCE_DB=$1
NEW_DB=$2

# Configuración del contenedor (el nuevo que ya usa LATIN9)
CONTAINER="sigesp-postgres-v2-temp"
DB_USER="postgres"

echo "=========================================================="
echo "Iniciando clonación de esquema (sin datos):"
echo "Origen  : $SOURCE_DB"
echo "Destino : $NEW_DB"
echo "=========================================================="

# Comprobar si el contenedor está corriendo
if ! docker ps --format '{{.Names}}' | grep -q "^${CONTAINER}$"; then
    echo "Error: El contenedor $CONTAINER no está en ejecución."
    exit 1
fi

# 1. Crear la nueva base de datos (hereda LATIN9 por defecto del contenedor nuevo o se fuerza)
echo "[1/2] Creando nueva base de datos '$NEW_DB'..."
docker exec -u $DB_USER $CONTAINER psql -c "CREATE DATABASE \"$NEW_DB\" ENCODING 'LATIN9';"

# 2. Volcar solo el esquema (-s) y restaurarlo en la nueva base de datos
echo "[2/2] Volcando y restaurando la estructura..."
docker exec -u $DB_USER $CONTAINER pg_dump -s -U $DB_USER "$SOURCE_DB" | \
  docker exec -i -u $DB_USER $CONTAINER psql -q -U $DB_USER -d "$NEW_DB" > /dev/null

echo "=========================================================="
echo "¡Clonación de esquema completada exitosamente!"
echo "La base de datos '$NEW_DB' está lista y vacía."
