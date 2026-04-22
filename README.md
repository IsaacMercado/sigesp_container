# SIGESP

## Faketime API

Servicio HTTP simple en Starlette para:

- iniciar y cerrar sesion
- consultar la sesion actual
- leer y cambiar `container/faketime/current.rc`
- crear usuarios solo desde terminal

Arranque:

```sh
uv run faketime-api
```

Arranque con Docker Compose:

```sh
docker compose -f container/compose.yaml up -d faketime-api
docker compose -f container/compose.yaml logs -f faketime-api
```

Ejemplo de unidad `systemd` para todo el proyecto con Docker Compose:

Archivo de ejemplo: `deploy/sigesp-compose.service.example`

```ini
[Unit]
Description=SIGESP Docker Compose Stack
Requires=docker.service
After=docker.service network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/sigesp_container
EnvironmentFile=/opt/sigesp_container/.env
ExecStart=/usr/bin/docker compose -f /opt/sigesp_container/container/compose.yaml up -d --build
ExecStop=/usr/bin/docker compose -f /opt/sigesp_container/container/compose.yaml down
ExecReload=/usr/bin/docker compose -f /opt/sigesp_container/container/compose.yaml up -d --build

[Install]
WantedBy=multi-user.target
```

Instalacion tipica:

```sh
sudo cp deploy/sigesp-compose.service.example /etc/systemd/system/sigesp-compose.service
sudo systemctl daemon-reload
sudo systemctl enable --now sigesp-compose.service
sudo systemctl status sigesp-compose.service
```

Ajusta `WorkingDirectory`, `EnvironmentFile` y la ruta absoluta del `compose.yaml` segun la ubicacion real del repo en el servidor.

El servicio ahora vive en `container/api/Dockerfile` y se inicializa dentro del mismo `compose` que ya levanta PHP y PostgreSQL. Comparte `container/faketime/current.rc` con ambos contenedores y guarda su SQLite en un volumen Docker dedicado.
En el host publica por defecto `8789:8080` para evitar conflictos comunes con otros procesos locales en `8080`. Si necesitas otro puerto externo, define `FAKETIME_API_BIND_PORT`.
El codigo Python del servicio ahora vive aislado en el paquete `faketime_api/`. El `main.py` del root queda solo como wrapper de compatibilidad.

Variables opcionales:

```sh
FAKETIME_API_HOST=127.0.0.1
FAKETIME_API_PORT=8080
FAKETIME_API_BIND_PORT=8789
```

Puedes copiar `.env.example` a `.env` si quieres fijar el puerto expuesto del contenedor sin tocar el compose.

Endpoints:

```text
GET  /app
GET  /health
POST /auth/login
POST /auth/logout
GET  /auth/me
GET  /faketime
PUT  /faketime
```

Interfaz web:

```text
http://127.0.0.1:8080/app
```

Si lo levantas con Docker Compose y no cambias nada, usa:

```text
http://127.0.0.1:8789/app
```

La pagina web ya no permite registrar usuarios. Solo permite login, logout y cambio de faketime.

Alta de usuarios solo por terminal:

```sh
uv run faketime-api create-user --username admin
uv run faketime-api create-user --username admin --password "clave-segura-123"
```

Login:

```json
POST /auth/login
{
  "username": "admin",
  "password": "clave-segura-123"
}
```

Cambio de faketime:

```json
PUT /faketime
{
  "mode": "start_at",
  "value": "2028-03-15 12:34:56"
}
```

Modos soportados por la API:

- `absolute`: `YYYY-MM-DD HH:MM:SS`
- `start_at`: `@YYYY-MM-DD HH:MM:SS` o `YYYY-MM-DD HH:MM:SS`
- `relative`: `+14d`, `-10m`, `+0 x2`
- `raw`: expresion libfaketime de una sola linea

## Base de datos

### Crear super usuario en la base de datos

```bash
docker compose -f container/compose.yaml exec -u postgres postgres createuser -s sigesp
```

### Crear base de datos en LATIN9

Ya por defecto las bases de datos se crean con el encoding LATIN9

```bash
docker compose -f container/compose.yaml exec -u postgres postgres createdb -U sigesp test_db
```

Explicitamente seria:

```bash
docker compose -f container/compose.yaml exec -u postgres postgres psql      
psql -c "CREATE DATABASE test_db ENCODING 'LATIN9' LC_COLLATE='es_VE.iso885915' LC_CTYPE='es_VE.iso885915' TEMPLATE template0;"
```

### Crear un respaldo

Puedes usar el script

```bash
chmod +x backup.sh
./backup.sh db_cida_2025
```

Si lo quieres poner en un crontab

```bash
0 9 * * * .../sigesp_container/backup.sh db_cida_2025 >> .../sigesp_container/backups/backup.log 2>&1
0 14 * * * .../sigesp_container/backup.sh db_cida_2025 >> .../sigesp_container/backups/backup.log 2>&1
```

### Clonar esquema

Puedes usar el script 

```bash
chmod +x clone_schema.sh
./clone_schema.sh db_cida_2025 db_nueva_2025
```
