# Google Calendar OAuth en lugia

## Registro en Google Cloud

1. Habilitar **Google Calendar API** en el proyecto.
2. Configurar la pantalla de consentimiento para la cuenta familiar. Si la app sigue en modo de prueba, incluir `famordcast@gmail.com` entre los usuarios de prueba.
3. Crear un cliente OAuth de tipo **Aplicación web**.
4. Registrar exactamente esta **URI de redirección autorizada**, incluida la barra final:

   `http://127.0.0.1:8005/api/v1/calendar/oauth/callback/`

No hace falta registrar un origen JavaScript: el intercambio del código y las llamadas a Google se hacen en Django. La URI apunta al loopback de la **computadora que abre el navegador**. Un túnel SSH lleva ese puerto a Django en lugia; `127.0.0.1` por sí solo no apunta a lugia.

## Permisos solicitados

- `https://www.googleapis.com/auth/calendar.calendarlist.readonly`: enumerar calendarios y seleccionar el familiar.
- `https://www.googleapis.com/auth/calendar.events`: leer, crear, editar y eliminar eventos del calendario seleccionado.

Google concede el alcance de eventos sobre los calendarios accesibles a la cuenta, no sobre un único calendario. Home Together restringe sus llamadas al ID familiar seleccionado y comprueba que la cuenta tenga rol `owner` o `writer` antes de guardarlo. No se solicitan Gmail, Drive, contactos, el alcance general `calendar` ni permisos para modificar la lista de calendarios.

## Credenciales y acceso local

Guardar `HT_GOOGLE_CLIENT_ID` y `HT_GOOGLE_CLIENT_SECRET` directamente en `.env` **en lugia** (`/home/alexandrr/dev/repos/HomeTogether/.env`). Ambos ya están configurados. Ese archivo está excluido de Git y conserva permisos `0600`. No pegar credenciales en chats, comandos de shell, documentación ni capturas. El backend guardará allí también `HT_GOOGLE_REFRESH_TOKEN` después del consentimiento; el token de acceso temporal se mantiene solo en memoria.

PostgreSQL local de Home Together escucha solo en `127.0.0.1:5434` y tiene volumen propio. Las migraciones y las cuentas administrativas `alexander` y `lastenia` ya están creadas. Sus contraseñas iniciales aleatorias se guardaron en las claves `HT_BOOTSTRAP_ALEXANDER_PASSWORD` y `HT_BOOTSTRAP_LASTENIA_PASSWORD` del mismo `.env`; conviene cambiarlas en Django Admin después del primer acceso y retirar esas claves. No se incluyen contraseñas en el código ni en esta guía.

El puerto 8000 de lugia ya lo usa otra aplicación. Iniciar Django en `127.0.0.1:8005` en lugia con `HT_LOCAL_OAUTH_HTTP=1` **solo para esta conexión por túnel**:

```bash
cd /home/alexandrr/dev/repos/HomeTogether/backend
HT_LOCAL_OAUTH_HTTP=1 .venv/bin/python manage.py runserver 127.0.0.1:8005
```

Desde la computadora, crear el túnel:

```bash
ssh -N -L 127.0.0.1:8005:127.0.0.1:8005 <usuario>@<dirección-ssh-de-lugia>
```

En ese navegador, abrir `http://127.0.0.1:8005/admin/login/` y acceder con una cuenta administradora de Django. Luego visitar `http://127.0.0.1:8005/api/v1/calendar/oauth/start/`. Tras autorizar `famordcast@gmail.com`, Django recibe el código, comprueba el estado OAuth, obtiene el token de renovación y lo guarda sin mostrarlo. La página de resultado enumera los calendarios con permiso de escritura y permite seleccionar el familiar. La API también ofrece `GET /api/v1/calendar/options/` y `POST /api/v1/calendar/select/` con CSRF para la futura interfaz.

El callback no coloca tokens en el navegador. El servidor de desarrollo tiene desactivado el registro de líneas de petición para que el código OAuth de la URL no aparezca en su log. No usar un proxy con registro de consultas para este flujo local. En mewtwo se registrará una nueva URI HTTPS del dominio final y las credenciales se trasladarán a secretos del despliegue.

**Estado actual:** el cliente OAuth está configurado y Django responde localmente en el puerto 8005. La cuenta familiar ya fue autorizada y se seleccionó su único calendario con rol `owner`. Se verificaron lectura, creación, edición y eliminación de tres eventos temporales, incluidos un evento de día completo y una serie de dos ocurrencias. El usuario confirmó su aparición, edición y desaparición en Google Calendar. No quedan eventos temporales activos.

Si el proyecto OAuth externo permanece en **Testing**, Google indica que el token de renovación obtenido para estos permisos vence a los **7 días**. Esto sirve para comprobar la conexión, pero antes del uso continuo habrá que revisar el estado de publicación y los requisitos de Google para una app privada con estos permisos.

Fuentes: [OAuth para servidores web](https://developers.google.com/identity/protocols/oauth2/web-server), [permisos de CalendarList](https://developers.google.com/workspace/calendar/api/v3/reference/calendarList/list), [permisos de Events](https://developers.google.com/workspace/calendar/api/v3/reference/events/insert), [vencimiento de tokens en Testing](https://developers.google.com/identity/protocols/oauth2).
