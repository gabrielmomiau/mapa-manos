# Guía de Disposición de Manos e Iconos

## Archivo de referencia

- **guia-manos.png**: Imagen maestra que define la disposición correcta de todas las manos, dedos e iconos del proyecto.

## Especificaciones de la guía

### 1. Posición de las manos en pantalla

- **Palma derecha**: debe mostrarse del lado **izquierdo** de la pantalla.
- **Palma izquierda**: debe mostrarse del lado **derecho** de la pantalla.

La guía etiqueta en color rojo exactamente cuál es cuál:
- Mano derecha/izquierda
- Nombre específico de cada dedo (pulgar, índice, medio, anular, meñique)

**Instrucción**: Usa esas etiquetas como referencia exacta, no las reinterpretes.

### 2. Iconos dentro de la palma

Los iconos ubicados al interior de cada palma deben colocarse **exactamente en la misma posición relativa** en la que aparecen en esta guía (mismas coordenadas relativas dentro del contorno de la palma).

### 3. Iconos fuera de la palma

Los iconos ubicados en el exterior de la mano deben conectarse desde el **nodo/articulación específico** que está indicado en la guía para cada uno.

**Instrucción**: Respeta el nodo exacto señalado, no uses uno genérico.

## Fidelidad a la guía

A partir de ahora, cada vez que se genere o ajuste una nueva imagen de manos con iconos, el resultado debe compararse contra esta guía y asegurarse de que coincida **fielmente** con:

- Disposición de manos (izquierda/derecha)
- Disposición de dedos
- Posición exacta de iconos dentro de la palma
- Nodos de conexión para iconos fuera de la palma

**No se deben mover, regenerar ni "interpretar con libertad" la posición de ningún elemento.**

Si hay dudas sobre la posición exacta de algún ícono o nodo, se debe preguntar antes de asumir.

## Nodos disponibles

Según la detección de MediaPipe Hands, los nodos disponibles para anclar iconos son:

- `centro_palma`: centro de la palma
- `muneca`: articulación de la muñeca
- `base_pulgar`, `punta_pulgar`: base y punta del pulgar
- `base_indice`, `punta_indice`: base y punta del índice
- `base_medio`, `punta_medio`: base y punta del dedo medio
- `base_anular`, `punta_anular`: base y punta del dedo anular
- `base_menique`, `punta_menique`: base y punta del dedo meñique

Consulta `guia-manos.png` para ver exactamente qué iconos se conectan a cuál nodo.
