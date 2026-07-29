from pathlib import Path
import math
import os

RUTA_RAIZ = Path(__file__).resolve().parent.parent
DIRECTORIO_ESTATICO = RUTA_RAIZ / "servidor" / "estatico"
DIRECTORIO_ASSETS = RUTA_RAIZ / "assets"
DIRECTORIO_CAPTURAS = RUTA_RAIZ / "servidor" / "capturas"
RUTA_MODELO_MAPA = DIRECTORIO_ASSETS / "mapamano_modelo.png"
RUTA_ANCLAJES_MANO = DIRECTORIO_ASSETS / "anclajes_mano.json"

ANCHO_CAMARA = 640
ALTO_CAMARA = 480
FPS_OBJETIVO = 24
CALIDAD_JPEG = 75

# Configuracion de color de la camara.
# Para la OV5647 del proyecto es mejor evitar cambios agresivos de canales
# y dejar que el balance de blancos haga la correccion principal.
FORMATO_COLOR_PICAMERA = "RGB888"
INTERCAMBIAR_CANALES_PICAMERA = False
APLICAR_BALANCE_BLANCO = True
FUERZA_BALANCE_BLANCO = 0.16
GANANCIA_BB_MIN = 0.82
GANANCIA_BB_MAX = 1.25

# Si la imagen entra con dominante azul, se corrige suavemente bajando B y subiendo R.
AUTO_CORREGIR_DOMINANTE_AZUL = True
UMBRAL_RATIO_AZUL_ROJO = 1.12
UMBRAL_DIF_AZUL_ROJO = 8.0

# Correccion adicional para sensores NoIR (camara nocturna sin filtro IR-cut).
# Por defecto se mantiene desactivada para la camara estandar del proyecto.
APLICAR_CORRECCION_NOIR = False
GANANCIA_NOIR_B = 0.82
GANANCIA_NOIR_G = 1.00
GANANCIA_NOIR_R = 1.28

# Correccion de rotacion por lado de mano (radianes).
# En algunos setups, la mano izquierda queda invertida visualmente.
CORRECCION_ROTACION_IZQUIERDA = math.pi
CORRECCION_ROTACION_DERECHA = 0.0

ENVIAR_FOTOGRAMA = True
# Desactivamos la capa de bordes para evitar marcas blancas en la vista principal.
ENVIAR_CAPA_BORDES = False
UMBRAL_BORDE_BAJO = 45
UMBRAL_BORDE_ALTO = 120

CONFIANZA_MINIMA_DETECCION = 0.55
CONFIANZA_MINIMA_SEGUIMIENTO = 0.55

# Cuando es True, el servidor no abre cámara física: espera frames del navegador.
MODO_CAMARA_NAVEGADOR = os.getenv("MODO_CAMARA_NAVEGADOR", "0") == "1"
MAXIMO_MANOS = 2

# Carpetas con ilustraciones aportadas por categoria.
CATEGORIAS_ILUSTRACIONES = [
    "nombres-lugares",
    "rios",
    "barcos",
    "paisaje",
    "animales",
]

ESTILO_POR_CATEGORIA = {
    "nombres-lugares": {"escala": 1.0, "opacidad": 0.9, "fusion": "source-over"},
    "rios": {"escala": 1.0, "opacidad": 0.85, "fusion": "screen"},
    "barcos": {"escala": 1.0, "opacidad": 0.92, "fusion": "source-over"},
    "paisaje": {"escala": 1.0, "opacidad": 0.86, "fusion": "multiply"},
    "animales": {"escala": 1.0, "opacidad": 0.9, "fusion": "source-over"},
}

ANCLAS_DISPONIBLES = [
    "centro_palma",
    "muneca",
    "base_pulgar",
    "punta_pulgar",
    "base_indice",
    "punta_indice",
    "base_medio",
    "punta_medio",
    "base_anular",
    "punta_anular",
    "base_menique",
    "punta_menique",
]

DESPLAZAMIENTOS_RELATIVOS = [
    (-0.20, -0.25),
    (-0.05, -0.22),
    (0.12, -0.2),
    (-0.18, -0.07),
    (-0.02, -0.08),
    (0.16, -0.08),
    (-0.2, 0.1),
    (0.0, 0.08),
    (0.18, 0.11),
    (-0.1, 0.22),
    (0.1, 0.23),
]
