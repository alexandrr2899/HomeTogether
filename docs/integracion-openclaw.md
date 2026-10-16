# Integración de Jaime con OpenClaw en mewtwo

**Estado:** el adaptador y la pantalla de chat están preparados en lugia. Home Together se desplegará en Portainer; OpenClaw se ejecutará en mewtwo fuera de ese stack. El informe técnico entregado el 15 de octubre de 2026 identifica el Gateway existente en `10.0.0.63:18789`, con bind `loopback`, autenticación por token y Chat Completions habilitado. Desde lugia todavía no se ha completado una prueba autenticada: SSH a `alexandrr@10.0.0.63` rechazó las credenciales disponibles y no hay URL ni token de OpenClaw configurados en Home Together.

## Flujo elegido

```text
Móvil o tablet → sesión/CSRF de Django (contenedor Portainer) → Jaime en Django
                                      ├→ Google Calendar / Home Assistant / PostgreSQL
                                      └→ Gateway de OpenClaw (proceso del host mewtwo)
                                           └→ respuesta o solicitud de función
                                      Django valida la función y devuelve su resultado
```

La interfaz de Home Together habla únicamente con Django. Django identifica a Alexander o Lastenia mediante su sesión y llama desde el servidor a `POST /v1/chat/completions` del Gateway, apuntando al agente configurado (se prevé uno dedicado llamado `jaime`). OpenClaw ofrece este endpoint desactivado por defecto y acepta funciones aportadas por el cliente; cuando devuelve una llamada de función, **Django** decide si la ejecuta. No se instala en OpenClaw un token de Home Assistant ni credenciales de Google. [Contrato de chat y funciones de OpenClaw](https://docs.openclaw.ai/gateway/openai-http-api).

El informe de mewtwo no mostró agentes explícitos en `agents.list`; la prueba local propuesta allí usa `openclaw/default`. El valor `HT_OPENCLAW_AGENT_ID=jaime` del repositorio es una **intención de configuración**, no una entidad confirmada. Primero se comprobará una conversación autenticada con `openclaw/default` y la lista real de modelos. Después se decidirá si un agente dedicado `jaime` puede añadirse sin alterar los recorridos de Telegram y Home Assistant. Home Together no declarará la conexión activa mientras su agente configurado no aparezca en `GET /v1/models`.

Las funciones que Home Together ofrece en la petición HTTP **no limitan las herramientas internas del agente OpenClaw**. Antes de usar un agente real para el chat familiar habrá que comprobar su política de herramientas y su acceso a archivos, canales y otros servicios. La prueba de `openclaw/default` sirve para verificar el transporte y no implica habilitarlo para uso familiar.

En el primer alcance, las funciones de solo lectura serán agenda acotada, listas y presencia. Bienestar se consultará únicamente si el titular mantiene activado `allow_jaime`. Las funciones de cambio solo crearán una `ActionProposal` usando el usuario autenticado: añadir a To-do, añadir a Compras o completar una tarea. El usuario verá la propuesta en Home Together y la confirmará por una segunda petición con sesión y CSRF; Django usará entonces las operaciones actuales que verifican el resultado en el origen. Las acciones del hogar exigirán después una lista explícita de entidades y operaciones autorizadas.

Django tratará argumentos y texto devueltos por OpenClaw como entrada no confiable: validará el esquema, el usuario, el intervalo de fechas, los límites de consulta y los IDs externos; limitará los ciclos de funciones y el tamaño de respuestas. Un texto generado no se mostrará como confirmación de una escritura. La respuesta de una función de lectura indicará fuente, estado y momento de consulta. El historial de conversaciones se separará por usuario y conversación; no se usará un identificador compartido de cuenta para todas las sesiones. La API de OpenClaw permite un valor `user` estable por conversación. [Sesiones en la API de chat](https://docs.openclaw.ai/gateway/openai-http-api).

## Red entre Portainer y el host

`localhost` dentro del contenedor Django apunta al contenedor, no a mewtwo. En Linux, Compose puede añadir `extra_hosts: ["host.docker.internal:host-gateway"]` al **backend**; Django llamaría, por ejemplo, a `http://host.docker.internal:18789`, siempre que esa dirección resuelva a una interfaz donde escuche el Gateway. El valor `host-gateway` suele resolver a la IP del bridge predeterminado del host, que se comprobará en mewtwo antes de fijar la URL. [Redes de Docker Compose](https://docs.docker.com/compose/how-tos/networking/).

El informe de mewtwo confirma un bind solo a `127.0.0.1` y `[::1]`. En ese estado, el contenedor **no puede** alcanzarlo mediante `host.docker.internal`: la petición llega a la IP del bridge, no al loopback del host. Tras inspeccionar la red real, una opción es configurar `gateway.bind: "custom"` con `gateway.customBindHost` igual a una IP del host accesible desde Docker, conservar autenticación por token y bloquear el puerto desde las interfaces públicas. Se verificará que OpenClaw siga disponible por loopback para su uso local. La interfaz Docker y las reglas de red siguen sin comprobar; no se pondrá `bind: "lan"` a ciegas. [Modos de bind de OpenClaw](https://docs.openclaw.ai/gateway/config-gateway), [exposición de red](https://docs.openclaw.ai/gateway/security/network-exposure).

Si la configuración real de OpenClaw impide ese bind, una alternativa es un proxy **en el host** que escuche solo en la interfaz Docker y reenvíe a `127.0.0.1:18789`, idealmente limitando las rutas a `/v1/models` y `/v1/chat/completions`. Se elegirá tras inspeccionar el servicio. El teléfono seguirá entrando solo al dominio HTTPS de Home Together; nunca llamará al Gateway directamente.

## Secretos

`OPENCLAW_GATEWAY_TOKEN` se guardará en la configuración privada de Portainer y se entregará solo al backend. Es una credencial de operador del Gateway, **no** un token limitado a Jaime; por eso el agente dedicado tendrá una política de herramientas estricta y la red se restringirá al backend y Gateway. No se pondrá el token en React, Git, logs o mensajes. Si el Gateway también aloja agentes personales con permisos amplios, se revisará el aislamiento antes de darle al backend este token. [Límite de seguridad de la API HTTP](https://docs.openclaw.ai/gateway/openai-http-api), [política de herramientas](https://docs.openclaw.ai/gateway/config-tools/tool-policy).

Las consultas de Jaime envían al Gateway el texto del usuario y los resultados de las funciones, que pueden incluir agenda, listas o bienestar autorizado. Antes de activarlo en mewtwo habrá que revisar el proveedor de modelo, la retención del historial y quién puede acceder a esas conversaciones. La pantalla actual mantiene los mensajes solo en memoria mientras permanece abierta; la sesión del Gateway puede conservar contexto según su configuración.

## Activación y verificación

1. Confirmar el inventario recibido de mewtwo y ejecutar allí una prueba **autenticada** de `GET /v1/models` y `POST /v1/chat/completions` con `openclaw/default`, sin imprimir el token ni datos personales. La prueba previa sin credenciales solo devolvió HTTP 401; no demuestra que el chat funcione. Comprobar también las herramientas reales del agente predeterminado.
2. Preparar, si procede, el agente `jaime` con herramientas internas restringidas. Chat Completions figura habilitado en el informe; verificarlo en vez de cambiarlo por suposición. Registrar el token solo fuera de Git.
3. Añadir el mapeo `host.docker.internal:host-gateway` solo al backend de Portainer, comprobar resolución y alcance desde ese contenedor y probar `GET /v1/models` sin imprimir el token; comprobar que el agente objetivo aparece.
4. Probar una conversación de solo lectura, una solicitud de función de lectura y la separación entre Alexander y Lastenia. Comprobar estados de fuente y privacidad de Garmin.
5. Probar una propuesta sin ejecutarla; después, con destino y elemento temporal autorizados, confirmarla desde la interfaz y verificar el origen real. Comprobar rechazo a llamadas no permitidas, fallos de red y resultados inciertos.
6. Solo después revisar voz. La presencia de Alexa en casa y el funcionamiento de sus listas no demuestran que Alexa pueda abrir una conversación con Jaime; ese recorrido necesita configuración y prueba aparte.

El `compose.prod.yml` ya añade `host.docker.internal:host-gateway` únicamente al backend y admite URL, token y agente mediante variables privadas de Portainer. Quedan vacías hasta medir la interfaz y el puerto reales de OpenClaw en mewtwo. El backend ya tiene una ruta de chat que usa la API oficial de OpenClaw y funciones limitadas; en lugia informa `Sin configurar` porque no hay Gateway ni token. OpenClaw seguirá fuera de Portainer y Home Together permanece en lugia durante el desarrollo.

En lugia se comprobó el cliente HTTP contra un Gateway local de prueba: descubrimiento del agente, autenticación, respuesta con llamada de función y propuesta pendiente sin escritura externa. Configuración también muestra el estado del Gateway con una comprobación acotada a tres segundos. Estos resultados no confirman conectividad ni comportamiento del OpenClaw real de mewtwo.
