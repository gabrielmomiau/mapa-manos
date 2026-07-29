# Mapa Manos (Raspberry Pi 5)

Base de proyecto para capturar video en vivo con una camara OV5647, detectar palmas de manos y superponer elementos visuales (PNG) como un "mapa vivo" que se mueve con la mano.

## Arquitectura

- Servidor Python (FastAPI): captura camara, detecta mano/palma y publica datos por WebSocket.
- Vision por computador: Picamera2 (si esta disponible), MediaPipe Hands y OpenCV.
- Interfaz web (Canvas): recibe fotogramas + puntos de mano + transformaciones y compone capas en tiempo real.

## Estructura

- `servidor/`: logica de captura, rastreo y API web.
- `servidor/estatico/`: interfaz web para visualizacion/proyeccion.
- `assets/`: ilustraciones PNG separadas por categoria.
- `guiones/`: utilidades para preparar y ejecutar en Raspberry Pi.

## Requisitos del sistema (Raspberry Pi OS)

1. Camara habilitada:
   - `sudo raspi-config` -> Interface Options -> Camera -> Enable
2. Librerias de sistema:
   - `sudo apt update`
   - `sudo apt install -y python3-venv python3-pip libatlas-base-dev libopenblas-dev libjpeg-dev`

## Instalacion

```bash
cd /home/enflujo/mapa-manos
./guiones/preparar_pi.sh
```

## Ejecutar

```bash
./guiones/ejecutar_dev.sh
```

## Verificar camara

```bash
./guiones/probar_camara.sh
```

Abrir en navegador:

- `http://<IP_DE_TU_PI>:8000`

## Como usar tus PNG

1. Organiza tus PNG en carpetas dentro de `assets/`.
2. Ya estan soportadas estas categorias: `nombres-lugares`, `rios`, `barcos`, `paisaje`, `animales`.
3. Ajusta estilo por categoria en `servidor/configuracion.py` (`ESTILO_POR_CATEGORIA`).
4. Mueve la mano frente a la camara: las capas seguiran la palma.

## Anclaje manual por mano y punto

Al iniciar el servidor se crea (si no existe) el archivo `assets/anclajes_mano.json`.

Ese documento te permite fijar cada dibujo a:

1. Mano objetivo: `palma izquierda`, `palma derecha` o `ambas`.
2. Punto de anclaje: `centro_palma`, `muneca`, `base_pulgar`, `punta_pulgar`, `base_indice`, `punta_indice`, `base_medio`, `punta_medio`, `base_anular`, `punta_anular`, `base_menique`, `punta_menique`.
3. Coordenadas relativas al ancla: `desplazamientoRel` como `[dx, dy]` en unidades de ancho de palma.
4. Escala/estilo por capa: `escalaRel`, `opacidad`, `fusion`, `rotacionExtra`.

Ejemplo de entrada por capa:

```json
{
   "id": "manomapa_elementos_mesa_1",
   "archivo": "nombres-lugares/Manomapa elementos_Mesa 1.png",
   "manoObjetivo": "palma derecha",
   "ancla": "centro_palma",
   "desplazamientoRel": [0.12, -0.08],
   "escalaRel": 0.95,
   "opacidad": 0.9,
   "fusion": "source-over",
   "rotacionExtra": 0.0
}
```

## Notas de rendimiento

- Resolucion recomendada para tracking estable: `640x480`.
- Si baja FPS, reduce `FPS_OBJETIVO` o desactiva `ENVIAR_FOTOGRAMA` en `servidor/configuracion.py`.

## Ajuste de orientacion por mano

Si las capas de una mano se ven invertidas, puedes ajustar:

- `CORRECCION_ROTACION_IZQUIERDA`
- `CORRECCION_ROTACION_DERECHA`

en `servidor/configuracion.py` (radianes). Por defecto la izquierda aplica 180 grados (`pi`).

## Solucion de problemas

- Si `mediapipe` no instala en tu imagen de Raspberry Pi OS, prueba una version alternativa para ARM (segun disponibilidad) y ajusta `requirements.txt`.
- Si no abre la camara, verifica con `libcamera-hello` y revisa permisos/dispositivo.
