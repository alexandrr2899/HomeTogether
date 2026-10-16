# Backend de Home Together

Base Django 5.2 + Django REST Framework, organizada por dominios:

| Paquete | Responsabilidad |
| --- | --- |
| `apps.accounts` | Sesiones privadas, CSRF e identidad del usuario. |
| `apps.family` | Perfiles familiares y datos propios. |
| `apps.integrations` | Estado y configuración de conexiones, sin secretos en las respuestas. |
| `apps.calendar` | API y adaptador independiente para Google Calendar. |
| `apps.lists` | Tareas y compras de las listas existentes. |
| `apps.home` | Presencia y acciones permitidas de Home Assistant. |
| `apps.planning` | Recetas, menú semanal, viajes y vista previa de ingredientes. |
| `apps.jaime` | Propuestas de acciones que requieren confirmación del administrador. |

`config` contiene únicamente la configuración y el enrutamiento. Los adaptadores de cada proveedor permanecerán en el dominio que los utiliza; las rutas HTTP no llamarán a proveedores directamente.

## Estado actual

- Home Assistant está configurado localmente mediante `.env`. `GET /api/v1/lists/` lee en vivo las tres listas existentes: «Compras», «Súper» y «To-do». Cada lista informa `Conectado`, `Sin conexión` o `Sin configurar`; no hay datos de demostración ni copias locales.
- `GET /api/v1/calendar/options/` enumera calendarios visibles para la cuenta OAuth y `GET /api/v1/calendar/events/?start=...&end=...` consulta un intervalo de hasta 31 días del calendario seleccionado. Los endpoints `/oauth/start/`, `/oauth/callback/` y `/oauth/result/` gestionan el consentimiento solo para administradores; `POST /api/v1/calendar/select/` selecciona un calendario con rol de escritura. El backend renueva el token OAuth y no entrega credenciales al navegador. Véase [la guía de OAuth](../docs/google-calendar-oauth.md). En lugia se seleccionó `famordcast@gmail.com`; lectura y CRUD de eventos temporales se verificaron contra Google Calendar.
- El adaptador de Google Calendar puede crear eventos con ID estable y editar o eliminar con ETag. Las tres operaciones se verificaron sobre eventos temporales autorizados. La API expone `POST /api/v1/calendar/events/` y `PATCH`/`DELETE /api/v1/calendar/events/{id}/` solo para administradores con CSRF. Un `operation_id` UUID conserva el mismo ID en Google durante reintentos y el backend consulta el estado antes de repetir una creación incierta. No hay cachés locales de eventos o tareas ni sincronización.
- La autenticación usa usuarios de Django sin registro público. Hay endpoints para obtener cookie CSRF, iniciar/cerrar sesión y consultar el usuario actual. Las demás rutas exigen sesión.
- Las tres listas existentes tienen lectura directa por `GET /api/v1/lists/`. Los administradores pueden crear mediante `POST /api/v1/lists/{list_id}/items/` con `operation_id` UUID y `summary`, y actualizar o borrar por UID externo mediante `PATCH` o `DELETE /api/v1/lists/{list_id}/items/{uid}/`. La escritura exige CSRF, capacidad declarada por la entidad y relectura de confirmación. Los registros mínimos de creación evitan reenviar una operación de resultado incierto. La interfaz muestra errores sin marcar cambios no confirmados como guardados. Crear, renombrar y completar un temporal desde estas rutas y la interfaz se verificó; reabrir y eliminar desde la nueva pantalla de detalle sigue pendiente de prueba visual, aunque ambas rutas se comprobaron por API.
- `GET /api/v1/home/presence/` lee los vínculos de cuentas con entidades `person.*` guardados en PostgreSQL y devuelve solo estado y hora, sin atributos de localización. Alexander y Lastenia tienen sus entidades confirmadas en lugia. `/api/v1/home/wellness/catalog/` enumera indicadores Garmin revisados y su disponibilidad; `/wellness/me/` lee en vivo solo los indicadores elegidos por el titular. `/wellness/preferences/` guarda por cuenta la selección visible, los indicadores compartidos y el permiso separado de Jaime. `/wellness/shared/` devuelve únicamente los indicadores compartidos. Inicialmente se muestran pasos, sueño y última actividad, mientras que compartir y Jaime empiezan desactivados. No se guardan mediciones ni rutas GPS.
- `GET /api/v1/integrations/connections/` incluye `web_url` para Home Assistant cuando `HOME_ASSISTANT_URL` es un origen HTTPS válido. Solo expone la dirección de navegación; el token y las credenciales de servicio permanecen en Django.
- `apps.family` expone perfiles, fechas, responsabilidades y documentos bajo `/api/v1/family/profiles/`; todas las rutas exigen administrador. Los documentos se descargan únicamente desde la API con sesión y se guardan en `HT_PRIVATE_FILES_DIR` (por defecto `private_uploads/`, ignorado por Git). El directorio deberá ser persistente en producción. La base de uso real comienza sin perfiles ni archivos.
- `apps.planning` expone `/api/v1/planning/recipes/`, `/menu/`, `/menu/shopping-preview/` y `/trips/`. El menú y los viajes son datos propios. La vista previa consulta «Compras» sin escribir y señala ingredientes cuyo nombre ya está en esa lista. La interfaz solicita una confirmación adicional para usar el endpoint de listas real. Los documentos de viaje comparten el almacenamiento privado. La base real no contiene recetas, comidas ni viajes de demostración.
- `apps.jaime` expone `/api/v1/jaime/chat/`, `/proposals/` y `/proposals/{uuid}/confirm/`. El chat usa el agente existente `main` de OpenClaw cuando el backend tiene URL y token; Django valida las funciones aportadas por Home Together y solo permite lecturas acotadas o propuestas por esas funciones. Las herramientas internas del agente conservan sus permisos de OpenClaw y no pasan por las propuestas de Django. Las propuestas de tareas o compras no escriben al crearse; su confirmación reutiliza `apps.lists.operations`, registra el resultado y bloquea reenvíos de estado incierto. La conexión de desarrollo con OpenClaw real está verificada por túnel SSH; la voz y el enlace de producción siguen pendientes.

## Desarrollo y comprobación

Desde la raíz del repositorio:

```bash
python3 -m venv backend/.venv
backend/.venv/bin/pip install -r backend/requirements.txt
cd backend
HT_TEST_SQLITE=1 .venv/bin/python manage.py test apps.accounts apps.calendar apps.lists apps.home apps.family apps.planning apps.jaime
```

`HT_TEST_SQLITE=1` usa SQLite solo para pruebas aisladas. La configuración normal usa PostgreSQL mediante `HT_DB_NAME`, `HT_DB_USER`, `HT_DB_PASSWORD`, `HT_DB_HOST` y `HT_DB_PORT`. La clave de Django se lee de `HT_DJANGO_SECRET_KEY`; no se incluye una clave en el código.

El backend también lee los valores de configuración no vacíos de `../.env` para desarrollo local, sin ejecutar el archivo como script. Ese archivo está ignorado por Git y debe mantenerse con permisos `0600`. Allí se colocan `HT_DJANGO_SECRET_KEY`, `HOME_ASSISTANT_URL`, `HOME_ASSISTANT_TOKEN` y las tres claves `HT_LIST_*_ENTITY_ID` de `.env.example`. Para Google Calendar se necesitan `HT_GOOGLE_CLIENT_ID`, `HT_GOOGLE_CLIENT_SECRET`, `HT_GOOGLE_REFRESH_TOKEN` y, una vez escogido, `HT_GOOGLE_CALENDAR_ID`; ningún valor debe guardarse en Git. Para inspeccionar Home Assistant se ejecuta `python3 scripts/inspect_ha.py` desde la raíz. Si Cloudflare Access protege el dominio, se añadirán `CLOUDFLARE_ACCESS_CLIENT_ID` y `CLOUDFLARE_ACCESS_CLIENT_SECRET`; no se desactivará Access.

En producción, la aplicación debe servirse por HTTPS. Las cookies de sesión y CSRF son seguras cuando `HT_DEBUG` está desactivado. `HT_ALLOWED_HOSTS`, `HT_CSRF_TRUSTED_ORIGINS`, `HT_TRUST_PROXY`, `HT_SSL_REDIRECT` y `HT_HSTS` se ajustarán al proxy y dominio reales durante el despliegue.

Para el cliente web: primero GET `/api/v1/accounts/csrf/`, luego POST `/api/v1/accounts/login/` con JSON `username` y `password`, cookie de sesión y encabezado `X-CSRFToken`. Django rota el token CSRF al iniciar sesión; el cliente debe leer de nuevo la cookie antes de la siguiente escritura.
