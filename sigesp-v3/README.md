# SIGESP

## Crear super usuario en la base de datos

```bash
docker exec -it sigesp-v3 su -c "createuser -s -P sigesp" postgres
```

## Crear base de datos de plantilla

```bash
docker exec -it sigesp-v3 su -c "createdb -O sigesp -T sigesp_template data_sigesp" postgres
```

## Ejemplo de configuracion de base de datos XML

En el archivo `sigesp_enterprise\base\xml\sigesp_xml_configuracion.xml`

```xml
<?xml version="1.0" encoding="UTF-8"?>
<conexiones>
    <conexion>
        <servidor>localhost</servidor>
        <puerto>5432</puerto>
        <basedatos>data_sigesp</basedatos>
        <nombre>ESTABLE 2016</nombre>
        <login>sigesp</login>
        <password>sigesp</password>
        <gestor>POSTGRES</gestor>
        <logo>imagen.gif</logo>
        <ancho>70</ancho>
        <alto>70</alto>
        <directorio></directorio>
        <tomcatservidor>192.168.1.96</tomcatservidor>
        <tomcatpuerto>8080</tomcatpuerto>
    </conexion>
</conexiones>
```