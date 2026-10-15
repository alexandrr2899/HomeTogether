# Home Together en móvil y tablet de pared

La misma aplicación adapta Inicio a una columna en móvil o tablet vertical y dos columnas en tablet horizontal cuando hay espacio. Calendario usa una cuadrícula mensual; Familia se abre desde Configuración. Organizar y Jaime conservan sus rutas y permisos. No hay una segunda aplicación ni una segunda fuente de datos.

El botón **Hogar** abre la interfaz HTTPS de Home Assistant en otra ventana o app del navegador. Home Assistant exige su propia sesión. Django solo entrega al navegador la dirección pública limpia de Home Assistant; el token de API y las credenciales de Cloudflare Access siguen en el backend. La vista de Home Assistant no está incrustada en Home Together. La forma exacta de alternar entre ambas interfaces debe probarse en el iPad o tablet elegido.

## Cuando se elija la tablet

1. Instalar Home Together como web app desde Safari en el iPad y probar el inicio de sesión, navegación, actualización y pérdida de red. [Apple explica cómo añadir un sitio como web app](https://support.apple.com/en-mide/guide/ipad/ipad8f1f7a29/ipados).
2. Preparar en Home Assistant un panel específico para la pared con solo las tarjetas y controles convenientes. [Home Assistant permite varios paneles](https://www.home-assistant.io/dashboards/dashboards/) y recomienda un usuario separado cuando la tablet necesita un panel predeterminado distinto al de los teléfonos. No se creará ni modificará ese panel o usuario sin acordar antes su alcance.
3. Decidir qué puede verse o cambiarse desde una pantalla accesible en la pared. La sesión actual de Alexander o Lastenia es administradora y puede mostrar documentos, bienestar u otros datos privados; antes del uso permanente hará falta una sesión de tablet con permisos y contenido definidos para ese dispositivo.
4. Probar orientación vertical y horizontal, tamaño de los controles, brillo y bloqueo de pantalla en el dispositivo físico. [Acceso guiado de iPad](https://support.apple.com/guide/ipad/lock-ipad-to-one-app-ipada16d1374/27/ipados/27) limita el uso a una sola app, por lo que no se asumirá que permite alternar libremente entre Home Together y Home Assistant. [Home Assistant ofrece modo quiosco en su app iOS](https://companion.home-assistant.io/docs/integrations/ios-kiosk-mode/) para un panel dedicado, pero su comportamiento con Home Together se verificará después.

**Estado:** adaptación de ancho y enlace implementados en lugia; pendiente la prueba visual y de navegación en una tablet real. No se ha instalado ni configurado ningún dispositivo de pared.
