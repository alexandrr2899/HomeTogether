# Integración de Jaime con OpenClaw en mewtwo

**Estado:** el adaptador y la pantalla de chat están preparados en lugia. Home Together se desplegará en Portainer; OpenClaw se ejecutará en mewtwo fuera de ese stack. No hay Gateway de OpenClaw accesible desde este entorno, credencial configurada ni prueba real de conversación.

## Flujo elegido

```text
Móvil o tablet → sesión/CSRF de Django (contenedor Portainer) → Jaime en Django
                                      ├→ Google Calendar / Home Assistant / PostgreSQL
                                      └→ Gateway de OpenClaw (proceso del host mewtwo)
                                           └→ respuesta o solicitud de función
                                      Django valida la función y devuelve su resultado
```

La interfaz de Home Together habla únicamente con Django. Django identifica a Alexander o Lastenia mediante su sesión y llama desde el servidor a `POST /v1/chat/completions` del Gateway, apuntando a un agente `jaime`. OpenClaw ofrece este endpoint desactivado por defecto y acepta funciones aportadas por el cliente; cuando devuelve una llamada de función, **Django** decide si la ejecuta. No se instala en OpenClaw un token de Home Assistant ni credenciales de Google. [Contrato de chat y funciones de OpenClaw](https://docs.openclaw.ai/gateway/openai-http-api).

En el primer alcance, las funciones de solo lectura serán agenda acotada, listas y presencia. Bienestar se consultará únicamente si el titular mantiene activado `allow_jaime`. Las funciones de cambio solo crearán una `ActionProposal` usando el usuario autenticado: añadir a To-do, añadir a Compras o completar una tarea. El usuario verá la propuesta en Home Together y la confirmará por una segunda petición con sesión y CSRF; Django usará entonces las operaciones actuales que verifican el resultado en el origen. Las acciones del hogar exigirán después una lista explícita de entidades y operaciones autorizadas.

Django tratará argumentos y texto devueltos por OpenClaw como entrada no confiable: validará el esquema, el usuario, el intervalo de fechas, los límites de consulta y los IDs externos; limitará los ciclos de funciones y el tamaño de respuestas. Un texto generado no se mostrará como confirmación de una escritura. La respuesta de una función de lectura indicará fuente, estado y momento de consulta. El historial de conversaciones se separará por usuario y conversación; no se usará un identificador compartido de cuenta para todas las sesiones. La API de OpenClaw permite un valor `user` estable por conversación. [Sesiones en la API de chat](https://docs.openclaw.ai/gateway/openai-http-api).

## Red entre Portainer y el host

`localhost` dentro del contenedor Django apunta al contenedor, no a mewtwo. En Linux, Compose puede añadir `extra_hosts: ["host.docker.internal:host-gateway"]` al **backend**; Django llamaría, por ejemplo, a `http://host.docker.internal:18789`, siempre que esa dirección resuelva a una interfaz donde escuche el Gateway. El valor `host-gateway` suele resolver a la IP del bridge predeterminado del host, que se comprobará en mewtwo antes de fijar la URL. [Redes de Docker Compose](https://docs.docker.com/compose/how-tos/networking/).

OpenClaw normalmente escucha solo en `127.0.0.1`. En ese estado, el contenedor **no puede** alcanzarlo mediante `host.docker.internal`: la petición llega a la IP del bridge, no al loopback del host. La opción inicial será configurar `gateway.bind: "custom"` con `gateway.customBindHost` igual a la IP del host accesible desde Docker, conservar autenticación por token y bloquear el puerto desde las interfaces públicas. Se verificará que OpenClaw siga disponible por loopback para su uso local. La dirección exacta y las reglas de red dependen del inventario de mewtwo; no se pondrá `bind: "lan"` a ciegas. [Modos de bind de OpenClaw](https://docs.openclaw.ai/gateway/config-gateway), [exposición de red](https://docs.openclaw.ai/gateway/security/network-exposure).

Si la configuración real de OpenClaw impide ese bind, una alternativa es un proxy **en el host** que escuche solo en la interfaz Docker y reenvíe a `127.0.0.1:18789`, idealmente limitando las rutas a `/v1/models` y `/v1/chat/completions`. Se elegirá tras inspeccionar el servicio. El teléfono seguirá entrando solo al dominio HTTPS de Home Together; nunca llamará al Gateway directamente.

## Secretos

`OPENCLAW_GATEWAY_TOKEN` se guardará en la configuración privada de Portainer y se entregará solo al backend. Es una credencial de operador del Gateway, **no** un token limitado a Jaime; por eso el agente dedicado tendrá una política de herramientas estricta y la red se restringirá al backend y Gateway. No se pondrá el token en React, Git, logs o mensajes. Si el Gateway también aloja agentes personales con permisos amplios, se revisará el aislamiento antes de darle al backend este token. [Límite de seguridad de la API HTTP](https://docs.openclaw.ai/gateway/openai-http-api), [política de herramientas](https://docs.openclaw.ai/gateway/config-tools/tool-policy).

Las consultas de Jaime envían al Gateway el texto del usuario y los resultados de las funciones, que pueden incluir agenda, listas o bienestar autorizado. Antes de activarlo en mewtwo habrá que revisar el proveedor de modelo, la retención del historial y quién puede acceder a esas conversaciones. La pantalla actual mantiene los mensajes solo en memoria mientras permanece abierta; la sesión del Gateway puede conservar contexto según su configuración.

## Activación y verificación

1. Inspeccionar la versión, el proceso o servicio del host, el puerto, el bind, el modo de autenticación y las herramientas del OpenClaw real en mewtwo; no modificarlo por suposición.
2. Preparar el agente `jaime` con herramientas internas restringidas y habilitar `gateway.http.endpoints.chatCompletions.enabled` en esa instancia. Registrar el token solo fuera de Git.
3. Añadir el mapeo `host.docker.internal:host-gateway` solo al backend de Portainer, comprobar resolución y alcance desde ese contenedor y probar `GET /v1/models` sin imprimir el token; comprobar que el agente objetivo aparece.
4. Probar una conversación de solo lectura, una solicitud de función de lectura y la separación entre Alexander y Lastenia. Comprobar estados de fuente y privacidad de Garmin.
5. Probar una propuesta sin ejecutarla; después, con destino y elemento temporal autorizados, confirmarla desde la interfaz y verificar el origen real. Comprobar rechazo a llamadas no permitidas, fallos de red y resultados inciertos.
6. Solo después revisar voz. La presencia de Alexa en casa y el funcionamiento de sus listas no demuestran que Alexa pueda abrir una conversación con Jaime; ese recorrido necesita configuración y prueba aparte.

El `compose.prod.yml` ya añade `host.docker.internal:host-gateway` únicamente al backend y admite URL, token y agente mediante variables privadas de Portainer. Quedan vacías hasta medir la interfaz y el puerto reales de OpenClaw en mewtwo. El backend ya tiene una ruta de chat que usa la API oficial de OpenClaw y funciones limitadas; en lugia informa `Sin configurar` porque no hay Gateway ni token. OpenClaw seguirá fuera de Portainer y Home Together permanece en lugia durante el desarrollo.

En lugia se comprobó el cliente HTTP contra un Gateway local de prueba: descubrimiento del agente, autenticación, respuesta con llamada de función y propuesta pendiente sin escritura externa. Configuración también muestra el estado del Gateway con una comprobación acotada a tres segundos. Estos resultados no confirman conectividad ni comportamiento del OpenClaw real de mewtwo.
