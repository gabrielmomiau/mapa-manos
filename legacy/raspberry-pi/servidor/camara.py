import logging
import sys
from typing import Optional

import cv2
import numpy as np

from .configuracion import (
    ALTO_CAMARA,
    APLICAR_BALANCE_BLANCO,
    APLICAR_CORRECCION_NOIR,
    ANCHO_CAMARA,
    AUTO_CORREGIR_DOMINANTE_AZUL,
    FPS_OBJETIVO,
    FORMATO_COLOR_PICAMERA,
    FUERZA_BALANCE_BLANCO,
    GANANCIA_NOIR_B,
    GANANCIA_NOIR_G,
    GANANCIA_NOIR_R,
    GANANCIA_BB_MAX,
    GANANCIA_BB_MIN,
    INTERCAMBIAR_CANALES_PICAMERA,
    MODO_CAMARA_NAVEGADOR,
    UMBRAL_DIF_AZUL_ROJO,
    UMBRAL_RATIO_AZUL_ROJO,
)

LOGGER = logging.getLogger(__name__)


def _importar_picamera2():
    try:
        from picamera2 import Picamera2

        return Picamera2
    except Exception:
        pass

    rutas_dist = [
        "/usr/lib/python3/dist-packages",
        f"/usr/lib/python{sys.version_info.major}/dist-packages",
        f"/usr/lib/python{sys.version_info.major}.{sys.version_info.minor}/dist-packages",
    ]
    for ruta in rutas_dist:
        if ruta not in sys.path:
            sys.path.append(ruta)

    from picamera2 import Picamera2

    return Picamera2


class FlujoCamara:
    def __init__(self) -> None:
        self.mode: Optional[str] = None
        self.picam2 = None
        self.cap = None
        self._ganancias_bb = np.array([1.0, 1.0, 1.0], dtype=np.float32)
        self._reporto_correccion_azul = False
        self._frame_fallback = np.zeros((ALTO_CAMARA, ANCHO_CAMARA, 3), dtype=np.uint8)
        self._ultimo_frame_exitoso = self._frame_fallback.copy()
        self._intentos_fallidos = 0

    def inject(self, frame_bgr: np.ndarray) -> None:
        """Inyecta un frame recibido desde el navegador."""
        self._ultimo_frame_exitoso = frame_bgr.copy()

    def start(self) -> None:
        if MODO_CAMARA_NAVEGADOR:
            self.mode = "navegador"
            LOGGER.info("Cámara en modo navegador (frames desde el cliente)")
            return

        try:
            Picamera2 = _importar_picamera2()

            self.picam2 = Picamera2()
            config = self.picam2.create_video_configuration(
                main={"size": (ANCHO_CAMARA, ALTO_CAMARA), "format": FORMATO_COLOR_PICAMERA},
                controls={"FrameRate": float(FPS_OBJETIVO), "AwbEnable": True, "AeEnable": True},
            )
            self.picam2.configure(config)
            self.picam2.start()
            self.mode = "picamera2"
            LOGGER.info("Camara iniciada con Picamera2")
            return
        except Exception as exc:  # pragma: no cover
            LOGGER.warning("Picamera2 no disponible, se usa OpenCV: %s", exc)

        self.cap = cv2.VideoCapture(0)
        if not self.cap or not self.cap.isOpened():
            raise RuntimeError("No se pudo iniciar la camara (ni Picamera2 ni OpenCV)")

        self.cap.set(cv2.CAP_PROP_FRAME_WIDTH, ANCHO_CAMARA)
        self.cap.set(cv2.CAP_PROP_FRAME_HEIGHT, ALTO_CAMARA)
        self.cap.set(cv2.CAP_PROP_FPS, FPS_OBJETIVO)
        self.mode = "opencv"
        LOGGER.info("Camara iniciada con OpenCV VideoCapture")

    def read(self) -> np.ndarray:
        try:
            if self.mode == "picamera2" and self.picam2 is not None:
                frame = self.picam2.capture_array("main")

                # Picamera2 entrega RGB888; convertimos una sola vez a BGR para OpenCV/web.
                if INTERCAMBIAR_CANALES_PICAMERA:
                    frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)

                frame = self._corregir_dominante_azul(frame)

                if APLICAR_CORRECCION_NOIR:
                    frame = self._aplicar_correccion_noir(frame)

                if APLICAR_BALANCE_BLANCO:
                    frame = self._aplicar_balance_blancos(frame)
                
                self._ultimo_frame_exitoso = frame.copy()
                self._intentos_fallidos = 0
                return frame

            if self.mode == "opencv" and self.cap is not None:
                ok, frame = self.cap.read()
                if not ok:
                    raise RuntimeError("No se pudo leer frame desde OpenCV")
                frame = self._corregir_dominante_azul(frame)
                if APLICAR_CORRECCION_NOIR:
                    frame = self._aplicar_correccion_noir(frame)
                if APLICAR_BALANCE_BLANCO:
                    frame = self._aplicar_balance_blancos(frame)
                
                self._ultimo_frame_exitoso = frame.copy()
                self._intentos_fallidos = 0
                return frame

            raise RuntimeError("Camara no inicializada")
        except Exception as exc:
            self._intentos_fallidos += 1
            if self._intentos_fallidos == 1:
                LOGGER.error("Error al leer frame de cámara: %s (usando último frame exitoso)", exc)
            return self._ultimo_frame_exitoso

    def stop(self) -> None:
        if self.picam2 is not None:
            self.picam2.stop()
            self.picam2 = None

        if self.cap is not None:
            self.cap.release()
            self.cap = None

        self.mode = None

    def _aplicar_balance_blancos(self, frame_bgr: np.ndarray) -> np.ndarray:
        media = frame_bgr.reshape(-1, 3).mean(axis=0).astype(np.float32) + 1e-6
        objetivo = float(np.mean(media))
        ganancias_objetivo = np.clip(objetivo / media, GANANCIA_BB_MIN, GANANCIA_BB_MAX)
        self._ganancias_bb = (
            (1.0 - FUERZA_BALANCE_BLANCO) * self._ganancias_bb
            + FUERZA_BALANCE_BLANCO * ganancias_objetivo
        )

        corregido = frame_bgr.astype(np.float32) * self._ganancias_bb.reshape(1, 1, 3)
        return np.clip(corregido, 0, 255).astype(np.uint8)

    def _calcular_ganancias_correcion_color(self, frame_bgr: np.ndarray) -> np.ndarray:
        if not AUTO_CORREGIR_DOMINANTE_AZUL:
            return np.array([1.0, 1.0, 1.0], dtype=np.float32)

        medias = frame_bgr.reshape(-1, 3).mean(axis=0).astype(np.float32)
        azul, _, rojo = float(medias[0]), float(medias[1]), float(medias[2])

        if rojo <= 1e-3:
            return np.array([1.0, 1.0, 1.0], dtype=np.float32)

        ratio = azul / rojo
        dif = azul - rojo
        if ratio >= UMBRAL_RATIO_AZUL_ROJO and dif >= UMBRAL_DIF_AZUL_ROJO:
            factor_azul = max(0.72, 1.0 - min(0.28, dif / 255.0))
            factor_rojo = min(1.28, 1.0 + min(0.28, dif / 255.0))
            return np.array([factor_azul, 1.0, factor_rojo], dtype=np.float32)

        return np.array([1.0, 1.0, 1.0], dtype=np.float32)

    def _corregir_dominante_azul(self, frame_bgr: np.ndarray) -> np.ndarray:
        ganancias = self._calcular_ganancias_correcion_color(frame_bgr)
        if np.allclose(ganancias, [1.0, 1.0, 1.0]):
            return frame_bgr

        if not self._reporto_correccion_azul:
            LOGGER.warning("Dominante azul detectada; se corrigen canales B/G/R de forma suave.")
            self._reporto_correccion_azul = True

        corregido = frame_bgr.astype(np.float32) * ganancias.reshape(1, 1, 3)
        return np.clip(corregido, 0, 255).astype(np.uint8)

    def _aplicar_correccion_noir(self, frame_bgr: np.ndarray) -> np.ndarray:
        ganancias = np.array(
            [GANANCIA_NOIR_B, GANANCIA_NOIR_G, GANANCIA_NOIR_R],
            dtype=np.float32,
        )
        corregido = frame_bgr.astype(np.float32) * ganancias.reshape(1, 1, 3)
        return np.clip(corregido, 0, 255).astype(np.uint8)
