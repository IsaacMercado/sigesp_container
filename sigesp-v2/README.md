# SIGESP

## Crear super usuario en la base de datos

```bash
docker exec -it sigesp-v2 su -c "createuser -s -P sigesp" postgres

docker exec sigesp-postgres-v2-temp psql -U postgres -c "CREATE DATABASE db_cida_2025 ENCODING 'LATIN9' LC_COLLATE='es_VE.iso885915' LC_CTYPE='es_VE.iso885915' TEMPLATE template0;"
```
# sigesp_container
