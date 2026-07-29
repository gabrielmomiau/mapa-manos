import math
import warnings
from typing import Any

import cv2
import mediapipe as mp
import numpy as np

from .configuracion import (
    CONFIANZA_MINIMA_DETECCION,
    CONFIANZA_MINIMA_SEGUIMIENTO,
    MAXIMO_MANOS,
)

warnings.filterwarnings(
    "ignore",
    message=r"SymbolDatabase\.GetPrototype\(\) is deprecated.*",
)


class RastreadorMano:
    def __init__(self) -> None:
        self.mp_hands = mp.solutions.hands
        self.hands = self.mp_hands.Hands(
            static_image_mode=False,
            max_num_hands=MAXIMO_MANOS,
            min_detection_confidence=CONFIANZA_MINIMA_DETECCION,
            min_tracking_confidence=CONFIANZA_MINIMA_SEGUIMIENTO,
        )

    def procesar(self, frame_bgr: np.ndarray) -> dict[str, Any]:
        h, w, _ = frame_bgr.shape
        frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
        result = self.hands.process(frame_rgb)

        if not result.multi_hand_landmarks:
            return {"hayManos": False, "manos": [], "anchoFrame": w, "altoFrame": h}

        manos: list[dict[str, Any]] = []
        for idx, hand_landmarks in enumerate(result.multi_hand_landmarks):
            lateralidad = "Unknown"
            confianza_lado = 0.0
            if result.multi_handedness and idx < len(result.multi_handedness):
                lateralidad = result.multi_handedness[idx].classification[0].label
                confianza_lado = float(result.multi_handedness[idx].classification[0].score)
            lado = self._normalizar_lado(lateralidad)

            puntos_norm: list[dict[str, float]] = []
            puntos_px: list[tuple[float, float]] = []
            for lm in hand_landmarks.landmark:
                puntos_norm.append({"x": lm.x, "y": lm.y, "z": lm.z})
                puntos_px.append((lm.x * w, lm.y * h))

            anclas = {
                "muneca": self._pt(puntos_px, 0),
                "base_pulgar": self._pt(puntos_px, 2),
                "punta_pulgar": self._pt(puntos_px, 4),
                "base_indice": self._pt(puntos_px, 5),
                "punta_indice": self._pt(puntos_px, 8),
                "base_medio": self._pt(puntos_px, 9),
                "punta_medio": self._pt(puntos_px, 12),
                "base_anular": self._pt(puntos_px, 13),
                "punta_anular": self._pt(puntos_px, 16),
                "base_menique": self._pt(puntos_px, 17),
                "punta_menique": self._pt(puntos_px, 20),
            }
            anclas["centro_palma"] = self._centroid(
                [
                    anclas["muneca"],
                    anclas["base_indice"],
                    anclas["base_medio"],
                    anclas["base_anular"],
                    anclas["base_menique"],
                ]
            )

            ancho_palma = self._distance(anclas["base_indice"], anclas["base_menique"])
            angulo_palma = math.atan2(
                anclas["base_menique"][1] - anclas["base_indice"][1],
                anclas["base_menique"][0] - anclas["base_indice"][0],
            )

            apertura = self._puntuacion_apertura(puntos_norm)
            es_palma = apertura >= 2

            manos.append(
                {
                    "idMano": idx,
                    "presente": True,
                    "esPalma": es_palma,
                    "lateralidad": lateralidad,
                    "lado": lado,
                    "confianzaLado": confianza_lado,
                    "puntuacionApertura": apertura,
                    "puntos": puntos_norm,
                    "anclas": {k: {"x": v[0], "y": v[1]} for k, v in anclas.items()},
                    "anchoPalma": ancho_palma,
                    "anguloPalma": angulo_palma,
                }
            )

        return {
            "hayManos": len(manos) > 0,
            "manos": manos,
            "anchoFrame": w,
            "altoFrame": h,
        }

    @staticmethod
    def _pt(landmarks_px: list[tuple[float, float]], idx: int) -> tuple[float, float]:
        return landmarks_px[idx]

    @staticmethod
    def _centroid(points: list[tuple[float, float]]) -> tuple[float, float]:
        x = sum(p[0] for p in points) / len(points)
        y = sum(p[1] for p in points) / len(points)
        return (x, y)

    @staticmethod
    def _distance(a: tuple[float, float], b: tuple[float, float]) -> float:
        return math.hypot(a[0] - b[0], a[1] - b[1])

    @staticmethod
    def _puntuacion_apertura(landmarks_norm: list[dict[str, float]]) -> int:
        # Heuristica simple: tip mas arriba que PIP en 4 dedos (coordenadas normalizadas).
        fingers = [(8, 6), (12, 10), (16, 14), (20, 18)]
        score = 0
        for tip, pip in fingers:
            if landmarks_norm[tip]["y"] < landmarks_norm[pip]["y"]:
                score += 1
        return score

    @staticmethod
    def _normalizar_lado(lateralidad: str) -> str:
        texto = str(lateralidad).strip().lower()
        if texto in {"left", "izquierda", "left hand", "mano izquierda", "palma izquierda"}:
            return "palma izquierda"
        if texto in {"right", "derecha", "right hand", "mano derecha", "palma derecha"}:
            return "palma derecha"
        return "desconocida"

    def close(self) -> None:
        self.hands.close()
