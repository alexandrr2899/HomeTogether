# Interfaz de Home Together

React, TypeScript y Vite. Los datos llegan de Django por `/api/v1/`; el navegador no recibe credenciales externas. Las pantallas muestran `Sin configurar`, `Sin conexión` o `Sin datos` cuando faltan fuentes reales.

Para desarrollo local, inicia Django en `127.0.0.1:8005` y después:

```bash
cd frontend
npm install
npm run dev
```

Vite reenvía `/api` al backend local. Para que Django acepte los formularios desde el puerto de Vite, `.env` incluye `HT_CSRF_TRUSTED_ORIGINS=http://127.0.0.1:5173` solo para este origen local. La interfaz exige una cuenta de Django; no tiene registro público. Calendario consulta Google en vivo. Las listas se leen y escriben mediante Home Assistant; los cambios se confirman por relectura. Organizar incluye recetas, menú y viajes propios, sin datos de ejemplo. La vista previa de ingredientes no añade compras hasta que el usuario confirme la selección. Jaime muestra el estado real del chat y propuestas para revisar; OpenClaw y voz permanecen sin configurar en lugia.

`npm run build` comprueba TypeScript y genera el shell PWA con manifiesto, iconos y service worker. Solo se cachean el shell y los recursos estáticos. Las llamadas a la API y los documentos privados no se cachean; los cambios no se envían sin conexión. La instalación y actualización en iPhone aún necesitan comprobación real.

Inicio muestra los tres indicadores Garmin solo al titular de la cuenta vinculada. Configuración ofrece permisos separados para compartir pasos, sueño y actividad, más un permiso propio para Jaime. Los cuatro están desactivados por defecto. La vista no recibe coordenadas ni rutas del sensor de actividad.
