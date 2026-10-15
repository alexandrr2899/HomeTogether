# Arquitectura de Home Together

## Entorno actual

El desarrollo y las comprobaciones se hacen en **lugia**. El frontend es React/TypeScript con Vite, el backend es Django/DRF y la base normal es PostgreSQL. La base SQLite se usa solo en pruebas aisladas. El despliegue en **mewtwo** desde GitHub por Portainer se preparará cuando la aplicación esté lista; no hay despliegue de producción ni remoto Git configurado todavía.

El navegador usa sesiones y CSRF de Django. Nunca recibe el token de Home Assistant, el Client Secret ni el refresh token de Google. Alexander y Lastenia tienen cuentas administrativas; no hay registro público. Los perfiles familiares son registros propios sin cuenta de acceso.

## Fuentes de verdad

| Datos | Fuente principal | Acceso desde Django | Persistencia en PostgreSQL |
| --- | --- | --- | --- |
| Eventos familiares | Google Calendar `famordcast@gmail.com` | API oficial con OAuth; lectura y CRUD verificados | No se copian eventos. |
| «Compras», «Súper» y «To-do» | Listas Alexa existentes | Entidades `todo.*` de Home Assistant; lectura y operaciones temporales verificadas | No se copian ítems. Solo se registra la creación necesaria para reconciliar un resultado incierto. |
| Presencia | Entidades `person.*` de Home Assistant | Lectura de los dos vínculos confirmados | Solo vínculos cuenta ↔ entidad; no se guardan estados ni coordenadas. |
| Perfiles, fechas, responsabilidades y documentos | Home Together | Django | Datos propios; los documentos usan almacenamiento privado fuera de Git. |
| Recetas, menú, viajes, participantes, preparativos y documentos de viaje | Home Together | Django | Datos propios. La vista previa de ingredientes lee «Compras» sin escribir; solo una confirmación explícita envía compras al origen externo. |
| Indicadores Garmin elegidos por Alexander | Garmin Connect vía Home Assistant | Lectura en vivo de un catálogo limitado de sensores vinculados a su cuenta | No se copian mediciones. Solo vínculos y preferencias de visualización y privacidad por cuenta. |

Home Together no escribe un evento simultáneamente por Google y Home Assistant. No se ha observado una entidad de Google Calendar en Home Assistant. La relación anunciada entre Apple Reminders y Alexa no se ha demostrado en estas listas y el usuario indicó que ya no hace falta comprobarla para el alcance actual; no se diseñará sincronización entre ellas sobre una suposición.

## Lectura y cambios

- El frontend consulta los servicios al entrar, al volver a la ventana y cada 30 segundos mientras está visible. Una respuesta fallida muestra `Sin conexión`; una fuente ausente muestra `Sin configurar`; una consulta vacía muestra `Sin datos`. No hay datos de demostración en la base real.
- Google Calendar conserva los IDs externos. Crear utiliza un ID estable derivado de un UUID de operación y consulta Google antes de repetir una creación incierta. Editar y borrar requieren el ETag leído antes; si cambió en otro cliente, se recarga antes de intentar de nuevo. Las ocurrencias recurrentes se muestran en solo lectura hasta decidir si se cambia una instancia o la serie.
- Las listas conservan el UID que entrega Home Assistant. Renombrar, completar, reabrir y borrar usan ese UID y se confirman por relectura. Crear registra el UUID de operación, nombre y UIDs anteriores para poder reconciliar sin reenviar una petición incierta. Se bloquea un nombre que ya existe en esa lista para evitar duplicados; Alexa normaliza mayúsculas. No se promete un cambio como guardado solo por recibir HTTP 200 de la acción.
- La presencia devuelve `home`, `not_home` o zona traducidos a una etiqueta y la marca `last_updated` de Home Assistant. No se exponen atributos de localización. La precisión depende de los rastreadores configurados en Home Assistant; el usuario confirmó que los dos estados observados coincidían con la situación real en la comprobación del 15 de octubre de 2026.
- Las responsabilidades del perfil son notas propias, no una lista paralela de Alexa. Al crearlas se puede elegir un evento existente de Google Calendar o un ítem de la lista general To-do. El backend confirma que el ID existe en el servicio original antes de guardar solo su origen e ID. La ruta de consulta del vínculo vuelve a leer el elemento externo; si Alexa deja de exponer temporalmente un ítem completado, informa `Sin datos` sin afirmar que se borró. El título y la fecha de la responsabilidad son datos propios y no modifican el elemento vinculado.

## Privacidad y operación

La descarga de documentos familiares y de viaje pasa por rutas autenticadas para administradores. Los archivos se guardan con nombre aleatorio, sin ruta pública y con permisos `0600`; el directorio privado se excluye de Git. En producción será necesario montar ese directorio en un volumen persistente y probar copia de seguridad y restauración. Los permisos de lectura y escritura de perfiles y documentos son de administradores.

La PWA cachea el shell y recursos estáticos, nunca llamadas `/api/` ni archivos privados. Sin conexión no se encolan ni envían cambios. La instalación y las actualizaciones en iPhone requieren verificación antes de considerarse listas.

La interfaz usa una sola aplicación para móvil y tablet. Inicio amplía su distribución en pantallas grandes sin cambiar las fuentes de datos. El acceso «Hogar» abre Home Assistant en su propia sesión mediante una URL HTTPS pública sin credenciales. Antes de dejar una tablet en la pared habrá que definir una sesión y permisos limitados para ese dispositivo, y probar el cambio entre aplicaciones en el hardware elegido. [La guía de tablet](tablet-pared.md) recoge esos pasos.

La navegación principal contiene Inicio, Calendario, Organizar y Jaime. Los perfiles familiares se administran dentro de Configuración. Calendario consulta a Google por el mes visible, con límite de 31 días por petición y paginación, mientras que Inicio consulta solo la semana próxima. Ambas vistas leen la misma fuente externa y no guardan copias locales de eventos.

Jaime conserva propuestas de cambios en PostgreSQL con estado pendiente, confirmado o incierto. Crear una propuesta no envía ningún cambio externo; confirmarla exige sesión de administrador y CSRF, llama a la operación de listas existente y guarda su resultado. Un resultado incierto bloquea otra confirmación automática. [El adaptador para OpenClaw en mewtwo](integracion-openclaw.md) usa Django como único intermediario: invoca el Gateway desde el backend y ejecuta o rechaza funciones de lectura y creación de propuestas según el usuario autenticado. El adaptador y la ruta de chat están preparados; por ahora no hay conexión real con OpenClaw ni acciones del hogar expresamente permitidas.

Bienestar: la API exige sesión. El titular elige qué indicadores del catálogo revisado aparecen en Inicio; por defecto son pasos, tiempo dormido y última actividad. La selección solo guarda claves de sensores, nunca valores. Otra cuenta solo recibe indicadores visibles que el titular haya autorizado individualmente para compartir. Ocultar un indicador compartido también revoca ese permiso. `allow_jaime` es una autorización separada, desactivada por defecto, que deberá comprobarse de nuevo cuando OpenClaw esté conectado. La respuesta excluye atributos del sensor como coordenadas y rutas GPS. Home Assistant y Garmin Connect conservan los datos originales; Home Together solo guarda la relación cuenta ↔ entidad y preferencias.

La configuración OAuth y el token de Home Assistant permanecen en `.env` local (ignorado por Git, `0600`). Para producción, `compose.prod.yml` recibe secretos desde Portainer fuera del repositorio y monta volúmenes para PostgreSQL y documentos privados. [La guía de despliegue](despliegue.md) deja pendientes el dominio HTTPS, la URI OAuth final, las copias externas y la restauración probada antes de publicar el stack.

## Pendientes que afectan la arquitectura

- Verificar desde el navegador la nueva pantalla de detalle de listas y los formularios familiares; las rutas de Familia se han probado solo con base y almacenamiento aislados.
- Verificar desde el navegador la selección de un evento o tarea real para una responsabilidad cuando existan perfiles y elementos adecuados. Las rutas y la validación se probaron con servicios simulados aislados; no se creó ningún perfil ni vínculo de prueba en la base real.
- Consultar la interfaz real de OpenClaw y configurar su acceso antes de conectar chat o voz. Las acciones del hogar requieren una lista de entidades y permisos expresamente aprobados.
- Garmin Connect ya está vinculado para Alexander y los tres indicadores iniciales responden desde Home Assistant y Django. Falta la revisión visual en su sesión y medir la frescura real desde el reloj hasta Garmin Connect; no se ha concedido acceso a Lastenia ni a Jaime.
- Preparar PWA, ejecución sin conexión solo de lectura, imágenes de producción y stack de Portainer para mewtwo.
