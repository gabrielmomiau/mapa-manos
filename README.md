# La soldadura del mundo — Mapa Manos

Experiencia web de realidad aumentada que detecta dos palmas, ancla ilustraciones sobre sus puntos
y toma una captura automática cuando ambas se mantienen abiertas.

La versión actual es un sitio estático: la cámara, MediaPipe, la composición y las capturas se
procesan enteramente en el navegador. No necesita Python, Raspberry Pi ni un servidor de
aplicación.

## Cómo funciona

- `getUserMedia` obtiene la cámara con permiso explícito de la persona.
- MediaPipe Hand Landmarker se ejecuta localmente mediante WebAssembly.
- `assets/anclajes_mano.json` relaciona cada ilustración con una mano y un punto anatómico.
- Canvas compone la cámara y las ilustraciones sin subir fotogramas.
- IndexedDB guarda las capturas únicamente en el navegador que las creó.
- La página Archivo permite previsualizar, compartir/descargar y borrar esas capturas.

El archivo local no se sincroniza entre dispositivos y se pierde si la persona borra los datos del
sitio. El envío automático por correo de la versión Python se retiró porque un sitio estático no
puede proteger credenciales SMTP; si vuelve a ser necesario deberá conectarse una función externa.

## Desarrollo

Requiere Node.js 22 o posterior.

```bash
npm install
npm run dev
```

La primera ejecución descarga el modelo oficial de Hand Landmarker y copia el runtime WebAssembly
a `public/`. Esos archivos generados no se versionan.

Comprobaciones:

```bash
npm test
npm run build
```

El resultado publicable queda en `dist/`. La compilación usa rutas relativas, de modo que funciona
tanto en un dominio propio como en una URL de proyecto del tipo
`https://usuario.github.io/mapa-manos/`.

## Publicación en GitHub Pages

El workflow `.github/workflows/pages.yml` compila y publica automáticamente cada cambio que llegue
a `main`.

En GitHub hay que abrir **Settings → Pages** y seleccionar **GitHub Actions** como fuente. La cámara
funciona allí porque GitHub Pages sirve el sitio por HTTPS.

## Estructura

- `src/`: detección, mapeo, render, almacenamiento y estilos.
- `assets/`: ilustraciones, tipografías y configuración manual de anclajes.
- `public/`: archivos que se copian directamente a la entrega.
- `tests/`: pruebas unitarias de la lógica geométrica.
- `legacy/raspberry-pi/`: prototipo anterior conservado como referencia.

## Privacidad y compatibilidad

La cámara requiere HTTPS o `localhost`. El reconocimiento funciona mejor en navegadores modernos
con WebAssembly y aceleración gráfica; si la GPU no está disponible, la aplicación cambia a CPU.
El rendimiento final depende del dispositivo y conviene probar físicamente móviles y computadores
de gama baja antes de una exhibición.
