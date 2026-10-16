# Preparación de despliegue en mewtwo

**Estado:** imágenes y stack preparados en lugia; no hay despliegue de producción, dominio HTTPS definitivo ni remoto Git configurado. La puesta en marcha requiere autorización cuando la app y las pruebas en iPhone estén listas.

## Imágenes y Portainer

`backend/Dockerfile` empaqueta Django/Gunicorn y `frontend/Dockerfile` construye React y lo sirve con Nginx. El workflow `.github/workflows/images.yml` publicará ambas imágenes en GHCR cuando exista un repositorio GitHub y se envíe la rama `main`. `compose.prod.yml` usa `HT_BACKEND_IMAGE` y `HT_FRONTEND_IMAGE` para esas imágenes. Si el paquete queda privado, Portainer necesitará credenciales de lectura de GHCR configuradas fuera de Git.

El stack conserva PostgreSQL, documentos privados y estáticos de Django en volúmenes separados. Nginx escucha dentro del contenedor en 8080 y el puerto del host se limita a `127.0.0.1:${HT_HTTP_PORT:-8088}`. El proxy HTTPS de mewtwo deberá alcanzar ese puerto, establecer `X-Forwarded-Proto: https`, conservar el encabezado `Host` y controlar quién puede enviar encabezados de proxy. No se debe publicar la aplicación por HTTP abierto. Nginx no registra líneas de petición para evitar que el código temporal de OAuth aparezca en logs.

Portainer recibirá las variables en la configuración privada del stack, nunca en el repositorio. Las obligatorias son:

| Grupo | Variables |
| --- | --- |
| Imágenes y red | `HT_BACKEND_IMAGE`, `HT_FRONTEND_IMAGE`, `HT_HTTP_PORT` (opcional) |
| Django y base | `HT_DJANGO_SECRET_KEY`, `HT_DB_NAME`, `HT_DB_USER`, `HT_DB_PASSWORD`, `HT_ALLOWED_HOSTS`, `HT_CSRF_TRUSTED_ORIGINS` |
| Home Assistant | `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN`, las tres `HT_LIST_*_ENTITY_ID`; si corresponde, `CLOUDFLARE_ACCESS_CLIENT_ID` y `CLOUDFLARE_ACCESS_CLIENT_SECRET` |
| Google Calendar | `HT_GOOGLE_CLIENT_ID`, `HT_GOOGLE_CLIENT_SECRET`, `HT_GOOGLE_REFRESH_TOKEN`, `HT_GOOGLE_CALENDAR_ID`, `HT_GOOGLE_REDIRECT_URI` |
| Jaime (opcional hasta conectar OpenClaw) | `HT_OPENCLAW_URL`, `HT_OPENCLAW_TOKEN`, `HT_OPENCLAW_AGENT_ID` (por defecto `main`) |

La URI OAuth de producción será `https://<dominio-final>/api/v1/calendar/oauth/callback/`; se registrará en Google Cloud cuando se conozca el dominio final. El backend lee solo esas variables en producción; el `.env` de lugia no se copia a la imagen. El arranque de Django aplica migraciones y recoge archivos estáticos antes de abrir Gunicorn. PostgreSQL debe pasar su comprobación de salud antes de que Django arranque.

Jaime queda `Sin configurar` si faltan URL o token de OpenClaw. En desarrollo, lugia llega al agente `main` por un túnel SSH local; ese túnel no forma parte del stack de producción. El backend de Portainer tiene el alias `host.docker.internal`, pero el Gateway actual escucha solo en loopback. Antes de desplegar hará falta un enlace privado desde Docker hacia ese loopback, con autenticación y sin exposición pública. [Las verificaciones y el diseño de red pendientes](integracion-openclaw.md) detallan la conexión. Ningún secreto de OpenClaw se entrega al frontend.

## Copias y restauración

Antes de publicar, se debe definir en Portainer una tarea periódica que exporte PostgreSQL en formato personalizado (`pg_dump -Fc`) y copie ese archivo **fuera de mewtwo**. Debe incluir también el volumen `private_uploads`, la configuración privada del stack y los datos necesarios para renovar OAuth. El volumen `django_static` se puede reconstruir de la imagen y no requiere copia. Se cifrarán las copias y se limitará su acceso a los administradores.

La restauración se probará en un stack aislado: restaurar el dump con `pg_restore`, restaurar `private_uploads`, aplicar migraciones, entrar con una cuenta administrativa y verificar calendario, listas y descarga de un documento autorizado. No se ejecutará una restauración sobre producción sin detener escrituras y acordar la ventana. La tarea automática, el destino externo de copias, la retención y la prueba de restauración **siguen pendientes**; por ello el stack no se considera listo para producción.

## Comprobaciones previas a publicar

1. Fijar dominio, proxy HTTPS y URI OAuth de producción; comprobar cookies seguras, CSRF y `python manage.py check --deploy` con las variables finales.
2. Ejecutar la aplicación en iPhone, probar instalación y actualización PWA, desconexión, autenticación y errores de servicios externos.
3. Confirmar permisos de GHCR y lectura por Portainer; fijar versiones de imágenes para despliegues y reversión.
4. Configurar copias externas y completar una restauración aislada.
5. Revisar que la base real no contenga registros de prueba ni credenciales en Git o imágenes.

En lugia ya se comprobó que `compose.prod.yml` es válido, que ambas imágenes se construyen, que Django pasa `check` dentro de su imagen y que la configuración de Nginx tiene sintaxis válida con el nombre de backend resuelto. No se ha iniciado este stack con datos de producción.

Una ejecución de `check --deploy` con valores de comprobación mostró solo los avisos de HSTS para subdominios y preload. Ambos se decidirán al conocer el dominio real; no se activan por defecto porque podrían afectar otros subdominios.
