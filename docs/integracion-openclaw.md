# Integración de Jaime con OpenClaw en mewtwo

**Estado:** Home Together usa en desarrollo el agente existente `main` de OpenClaw, el mismo que atiende Telegram. El Gateway de mewtwo (`10.0.0.63:18789`) permanece en loopback y exige token. Lugia llega a él por un túnel SSH local en `127.0.0.1:18790`; URL, token y agente están solo en `.env` ignorado por Git. Se verificaron una conversación directa, el adaptador HTTP y una petición a la ruta de Django con sesión y CSRF. Se comprobó que Alexander y Lastenia ven el chat conectado en la interfaz, pero aún no se envió un mensaje desde el navegador. Falta preparar el enlace privado para Portainer en mewtwo.

## Flujo elegido

```text
Móvil o tablet → sesión/CSRF de Django (contenedor Portainer) → Jaime en Django
                                      ├→ Google Calendar / Home Assistant / PostgreSQL
                                      └→ Gateway de OpenClaw (proceso del host mewtwo)
                                           └→ respuesta o solicitud de función
                                      Django valida la función y devuelve su resultado
```

La interfaz de Home Together habla únicamente con Django. Django identifica a Alexander o Lastenia mediante su sesión y llama desde el servidor a `POST /v1/chat/completions` del Gateway, apuntando a `openclaw/main`. OpenClaw acepta funciones aportadas por el cliente; cuando devuelve una llamada de esas funciones, **Django** decide si la ejecuta. El agente también conserva sus herramientas internas actuales. No se instala en OpenClaw un token de Home Assistant ni credenciales de Google desde Home Together. [Contrato de chat y funciones de OpenClaw](https://docs.openclaw.ai/gateway/openai-http-api).

La configuración real usa `agents.entries` y contiene únicamente `main`; `GET /v1/models` devolvió `openclaw`, `openclaw/default` y `openclaw/main`. Una petición autenticada de prueba a `openclaw/default` devolvió HTTP 200 y la respuesta esperada, sin llamadas de función. Home Together configura `HT_OPENCLAW_AGENT_ID=main` y solo declara la conexión activa cuando ese modelo aparece en `GET /v1/models`.

Las funciones que Home Together ofrece en la petición HTTP **no limitan las herramientas internas del agente OpenClaw**. El usuario quiere que Jaime sea un asistente general: `main` conserva el perfil global `coding` y sus capacidades actuales. Por ello, la confirmación que exige Django aplica a las `ActionProposal` de Home Together; una acción ejecutada por una herramienta propia de OpenClaw sigue las reglas de OpenClaw y no pasa por esa confirmación. La interfaz indica expresamente esta diferencia.

La conversación real aún **no ha invocado** las funciones aportadas por Django: una petición automática respondió sin `tool_calls`, incluso cuando se le indicó consultar Compras; una petición que exigió una función devolvió HTTP 502 con el motivo «el agente no produjo la llamada requerida». En ese intento, Django no leyó ni transmitió ítems de Compras. Por tanto, el chat general está conectado, pero agenda, listas, presencia y propuestas **desde el chat** siguen pendientes de verificación. Se investigará la compatibilidad de funciones con OpenClaw 2026.9.6 antes de prometer esos recorridos.

No se añadió otro agente ni un binding de Telegram. OpenClaw mantiene un único agente `main`, y la ruta implícita de Telegram conserva su configuración actual. Las conversaciones de Home Together usan un identificador estable distinto por cuenta y conversación; esto separa sesiones de chat, aunque comparten el agente y su espacio de trabajo. [Sesiones HTTP de OpenClaw](https://docs.openclaw.ai/gateway/openai-http-api).

En el primer alcance, las funciones **aportadas por Home Together** son agenda acotada, listas, presencia y bienestar autorizado por el titular. `allow_jaime` debe estar activo para cualquier consulta de sus indicadores; otra cuenta solo puede pedirlos mediante Jaime si figura expresamente en `jaime_viewers`. Esto no los muestra en Inicio. Sus funciones de cambio solo crean una `ActionProposal` usando el usuario autenticado: añadir a To-do, añadir a Compras o completar una tarea. El usuario ve la propuesta en Home Together y la confirma por otra petición con sesión y CSRF. Estas reglas no gobiernan las herramientas internas de OpenClaw; futuras funciones propias para acciones del hogar requerirán una lista explícita de entidades y operaciones permitidas en Django.

Django tratará argumentos y texto devueltos por OpenClaw como entrada no confiable: validará el esquema, el usuario, el intervalo de fechas, los límites de consulta y los IDs externos; limitará los ciclos de funciones y el tamaño de respuestas. Un texto generado no se mostrará como confirmación de una escritura. La respuesta de una función de lectura indicará fuente, estado y momento de consulta. El historial de conversaciones se separará por usuario y conversación; no se usará un identificador compartido de cuenta para todas las sesiones. La API de OpenClaw permite un valor `user` estable por conversación. [Sesiones en la API de chat](https://docs.openclaw.ai/gateway/openai-http-api).

## Red entre Portainer y el host

`localhost` dentro del contenedor Django apunta al contenedor, no a mewtwo. En Linux, Compose puede añadir `extra_hosts: ["host.docker.internal:host-gateway"]` al **backend**; Django llamaría, por ejemplo, a `http://host.docker.internal:18789`, siempre que esa dirección resuelva a una interfaz donde escuche el Gateway. El valor `host-gateway` suele resolver a la IP del bridge predeterminado del host, que se comprobará en mewtwo antes de fijar la URL. [Redes de Docker Compose](https://docs.docker.com/compose/how-tos/networking/).

La inspección directa en mewtwo confirmó un bind solo a `127.0.0.1` y `[::1]`. En ese estado, el contenedor **no puede** alcanzarlo mediante `host.docker.internal`: la petición llega a la IP del bridge, no al loopback del host. Para producción se estudiará un proxy local restringido a la interfaz Docker que reenvíe a loopback; así se conserva la configuración actual del Gateway. También puede evaluarse un bind específico del Gateway si la red real lo exige. Se verificará que el puerto no sea público y que Telegram siga funcionando. No se pondrá `bind: "lan"` a ciegas. [Modos de bind de OpenClaw](https://docs.openclaw.ai/gateway/config-gateway), [exposición de red](https://docs.openclaw.ai/gateway/security/network-exposure).

El proxy **en el host** escucharía solo en la interfaz Docker y reenviaría a `127.0.0.1:18789`, idealmente limitando las rutas a `/v1/models` y `/v1/chat/completions`. Se elegirá al preparar Portainer, después de identificar la red real. El teléfono seguirá entrando solo al dominio HTTPS de Home Together; nunca llamará al Gateway directamente.

## Secretos

En lugia, el token está en `.env` con permisos `0600`. En producción se guardará en la configuración privada de Portainer y se entregará solo al backend. Es una credencial de operador del Gateway, **no** un token limitado a Home Together; la red se restringirá entre Django y el Gateway. No se pondrá el token en React, Git, logs o mensajes. El acceso a Jaime seguirá limitado a las dos cuentas administradoras de Home Together. [Límite de seguridad de la API HTTP](https://docs.openclaw.ai/gateway/openai-http-api), [política de herramientas](https://docs.openclaw.ai/gateway/config-tools/tool-policy).

Las consultas de Jaime envían al Gateway el texto del usuario y, cuando funcionen las llamadas de función, sus resultados, que pueden incluir agenda, listas o bienestar autorizado. Antes del despliegue de Home Together en mewtwo habrá que revisar el proveedor de modelo, la retención del historial y quién puede acceder a esas conversaciones. La pantalla actual mantiene los mensajes solo en memoria mientras permanece abierta; la sesión del Gateway puede conservar contexto según su configuración.

Alexander autorizó que Lastenia consulte sus indicadores Garmin mediante Jaime. La autorización se registra por destinatario en Django y se puede revocar en Configuración; no activa el bienestar compartido en Inicio. El ajuste `allow_jaime` y la lista de destinatarios controlan únicamente la función de bienestar de Django. La configuración revisada de OpenClaw no declara un complemento ni un servidor MCP de Home Assistant. Sí mantiene el perfil general `coding`, que incluye herramientas fuera del control de Django; por ello, estos ajustes no constituyen una barrera global contra otras vías de acceso. Esta limitación se muestra en Configuración.

## Activación y verificación

1. **Verificado:** en mewtwo, `GET /v1/models` y `POST /v1/chat/completions` autenticados con `openclaw/default` respondieron HTTP 200. Desde lugia, el cliente HTTP de Django y la ruta privada `/api/v1/jaime/chat/` funcionaron con el agente `main` a través de un túnel SSH; la ruta devolvió HTTP 200, sin ejecutar funciones ni crear propuestas. No se mostraron secretos ni datos familiares.
2. **Configurado en desarrollo:** URL local, token y agente `main` en `.env` ignorado por Git; túnel SSH local en `127.0.0.1:18790`. Se comprobó la pantalla autenticada de Alexander y Lastenia a 390 px. Faltan mensajes de prueba desde cada cuenta y comprobar la separación de contexto entre sus conversaciones. No se cambiaron agentes, herramientas, rutas de Telegram ni configuración del Gateway.
3. Añadir el mapeo `host.docker.internal:host-gateway` solo al backend de Portainer, comprobar resolución y alcance desde ese contenedor y probar `GET /v1/models` sin imprimir el token; comprobar que el agente objetivo aparece.
4. La conversación general ya respondió desde Django; la función de lectura no se ejecutó en OpenClaw 2026.9.6. Resolver esa compatibilidad y probar desde la interfaz la separación entre Alexander y Lastenia, los estados de fuente y la privacidad de Garmin.
5. Probar una propuesta sin ejecutarla; después, con destino y elemento temporal autorizados, confirmarla desde la interfaz y verificar el origen real. Comprobar rechazo a llamadas no permitidas, fallos de red y resultados inciertos.
6. Solo después revisar voz. La presencia de Alexa en casa y el funcionamiento de sus listas no demuestran que Alexa pueda abrir una conversación con Jaime; ese recorrido necesita configuración y prueba aparte.

El `compose.prod.yml` ya añade `host.docker.internal:host-gateway` únicamente al backend y admite URL, token y agente mediante variables privadas de Portainer. Esas variables de producción quedan vacías hasta preparar un enlace privado alcanzable desde Docker: el Gateway real sigue en loopback y `host.docker.internal` por sí solo no lo alcanza. OpenClaw seguirá fuera de Portainer y Home Together permanece en lugia durante el desarrollo.

En lugia se comprobó el cliente HTTP contra un Gateway local de prueba: descubrimiento del agente, autenticación, respuesta con llamada de función y propuesta pendiente sin escritura externa. Configuración muestra el estado del Gateway con una comprobación acotada a tres segundos. La conversación sí se verificó después con el Gateway real de mewtwo; las llamadas de función continúan pendientes.
