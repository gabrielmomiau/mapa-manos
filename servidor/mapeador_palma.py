from __future__ import annotations

import json
import logging
import re
from pathlib import Path
from typing import Any
from urllib.parse import quote, unquote

import cv2
import numpy as np

from .configuracion import (
    CATEGORIAS_ILUSTRACIONES,
    CORRECCION_ROTACION_DERECHA,
    CORRECCION_ROTACION_IZQUIERDA,
    DIRECTORIO_ASSETS,
    ESTILO_POR_CATEGORIA,
    RUTA_ANCLAJES_MANO,
    RUTA_MODELO_MAPA,
)

LOGGER = logging.getLogger(__name__)


class MapeadorPalma:
    def __init__(self) -> None:
        self.archivo_anclajes_existe = RUTA_ANCLAJES_MANO.exists()
        self.capas_modelo = self._construir_capas_desde_modelo()
        self.capas_ancladas = self._cargar_capas_desde_json()
        # Solo usa el modelo automatico si no existe archivo manual.
        if not self.archivo_anclajes_existe and not self.capas_ancladas and self.capas_modelo:
            self.capas_ancladas = self._anclajes_desde_modelo()

    def calcular(self, datos_manos: dict[str, Any]) -> list[dict[str, Any]]:
        manos = datos_manos.get("manos", [])
        if not manos:
            return []

        manos_palma = [m for m in manos if m.get("esPalma")]
        if not manos_palma:
            return []

        if self.capas_ancladas:
            return self._calcular_desde_anclajes(manos_palma)
        return self._calcular_desde_modelo(manos_palma, datos_manos)

    def _calcular_desde_anclajes(self, manos_palma: list[dict[str, Any]]) -> list[dict[str, Any]]:
        salida: list[dict[str, Any]] = []

        for capa in self.capas_ancladas:
            objetivo = capa.get("manoObjetivo", "ambas")
            for mano in manos_palma:
                lado = self._normalizar_lado_mano(mano)
                if objetivo != "ambas" and lado != objetivo:
                    continue

                ancla_nombre = capa.get("ancla", "centro_palma")
                ancla = mano.get("anclas", {}).get(ancla_nombre)
                if ancla is None:
                    ancla = mano.get("anclas", {}).get("centro_palma")
                if ancla is None:
                    continue

                ancho_palma = max(float(mano.get("anchoPalma", 0.0)), 1.0)
                angulo_palma = float(mano.get("anguloPalma", 0.0))

                dx = float(capa.get("desplazamientoRel", [0.0, 0.0])[0])
                dy = float(capa.get("desplazamientoRel", [0.0, 0.0])[1])
                x = float(ancla["x"]) + dx * ancho_palma
                y = float(ancla["y"]) + dy * ancho_palma

                salida.append(
                    {
                        "id": capa["id"],
                        "src": capa["src"],
                        "x": x,
                        "y": y,
                        "rotacion": angulo_palma
                        + self._correccion_rotacion_por_lado(lado)
                        + float(capa.get("rotacionExtra", 0.0)),
                        "escala": float(capa.get("escalaRel", 1.0)) * (ancho_palma / 190.0),
                        "opacidad": float(capa.get("opacidad", 1.0)),
                        "fusion": capa.get("fusion", "source-over"),
                        "idMano": mano.get("idMano"),
                        "ladoDetectado": lado,
                        "ancla": ancla_nombre,
                    }
                )

        return salida

    def _calcular_desde_modelo(
        self, manos_palma: list[dict[str, Any]], datos_manos: dict[str, Any]
    ) -> list[dict[str, Any]]:
        manos_ordenadas = sorted(
            manos_palma, key=lambda m: float(m["anclas"]["centro_palma"]["x"])
        )
        mapa_lados = self._mapa_lados_deteccion(manos_ordenadas, datos_manos)

        salida: list[dict[str, Any]] = []
        for capa in self.capas_modelo:
            mano_objetivo = mapa_lados.get(capa["ladoModelo"])
            if mano_objetivo is None:
                continue

            ancla = mano_objetivo["anclas"].get("centro_palma")
            if ancla is None:
                continue

            ancho_palma = max(float(mano_objetivo.get("anchoPalma", 0.0)), 1.0)
            angulo_palma = float(mano_objetivo.get("anguloPalma", 0.0))

            x = float(ancla["x"]) + float(capa["dxRel"]) * ancho_palma
            y = float(ancla["y"]) + float(capa["dyRel"]) * ancho_palma

            salida.append(
                {
                    "id": capa["id"],
                    "src": capa["src"],
                    "x": x,
                    "y": y,
                    "rotacion": angulo_palma
                    + self._correccion_rotacion_por_lado(capa["ladoModelo"]),
                    "escala": float(capa["escalaBase"]) * (ancho_palma / 190.0),
                    "opacidad": float(capa["opacidad"]),
                    "fusion": capa["fusion"],
                    "idMano": mano_objetivo.get("idMano"),
                    "ladoModelo": capa["ladoModelo"],
                    "scoreModelo": capa["score"],
                }
            )

        return salida

    def _cargar_capas_desde_json(self) -> list[dict[str, Any]]:
        if not RUTA_ANCLAJES_MANO.exists():
            return []

        try:
            texto = RUTA_ANCLAJES_MANO.read_text(encoding="utf-8")
            texto = self._limpiar_comentarios_json(texto)
            data = json.loads(texto)
        except Exception as exc:
            LOGGER.warning("No se pudo parsear anclajes_mano.json: %s", exc)
            return []

        capas_json = data.get("capas", []) if isinstance(data, dict) else []
        salida: list[dict[str, Any]] = []
        for idx, capa in enumerate(capas_json):
            if not isinstance(capa, dict):
                continue

            archivo = str(capa.get("archivo", "")).strip()
            if not archivo:
                continue
            ruta_local = DIRECTORIO_ASSETS / archivo
            if not ruta_local.exists():
                continue

            desplazamiento = capa.get("desplazamientoRel", [0.0, 0.0])
            if not isinstance(desplazamiento, list) or len(desplazamiento) != 2:
                desplazamiento = [0.0, 0.0]

            id_capa = str(capa.get("id", "")).strip() or f"capa_{idx + 1}"
            salida.append(
                {
                    "id": id_capa,
                    "src": "/assets/" + quote(Path(archivo).as_posix(), safe="/"),
                    "manoObjetivo": str(capa.get("manoObjetivo", "ambas")).lower(),
                    "ancla": str(capa.get("ancla", "centro_palma")),
                    "desplazamientoRel": [
                        float(desplazamiento[0]),
                        float(desplazamiento[1]),
                    ],
                    "escalaRel": float(capa.get("escalaRel", 1.0)),
                    "opacidad": float(capa.get("opacidad", 1.0)),
                    "fusion": str(capa.get("fusion", "source-over")),
                    "rotacionExtra": float(capa.get("rotacionExtra", 0.0)),
                }
            )
        return salida

    def _anclajes_desde_modelo(self) -> list[dict[str, Any]]:
        salida: list[dict[str, Any]] = []
        for capa in self.capas_modelo:
            salida.append(
                {
                    "id": capa["id"],
                    "src": capa["src"],
                    "manoObjetivo": capa["ladoModelo"],
                    "ancla": "centro_palma",
                    "desplazamientoRel": [float(capa["dxRel"]), float(capa["dyRel"])],
                    "escalaRel": float(capa["escalaBase"]),
                    "opacidad": float(capa.get("opacidad", 1.0)),
                    "fusion": str(capa.get("fusion", "source-over")),
                    "rotacionExtra": 0.0,
                }
            )
        return salida

    @staticmethod
    def _normalizar_lado_mano(mano: dict[str, Any]) -> str:
        lado = str(mano.get("lado", "")).strip().lower()
        if lado in {"palma izquierda", "palma derecha"}:
            return lado
        if lado in {"izquierda", "left", "left hand", "mano izquierda"}:
            return "palma izquierda"
        if lado in {"derecha", "right", "right hand", "mano derecha"}:
            return "palma derecha"

        lateralidad = str(mano.get("lateralidad", "")).strip().lower()
        if lateralidad in {"left", "left hand", "izquierda", "mano izquierda", "palma izquierda"}:
            return "palma izquierda"
        if lateralidad in {"right", "right hand", "derecha", "mano derecha", "palma derecha"}:
            return "palma derecha"
        return "desconocida"

    def _mapa_lados_deteccion(
        self, manos_ordenadas: list[dict[str, Any]], datos_manos: dict[str, Any]
    ) -> dict[str, dict[str, Any] | None]:
        if len(manos_ordenadas) >= 2:
            return {
                "palma derecha": manos_ordenadas[0],
                "palma izquierda": manos_ordenadas[-1],
            }

        mano = manos_ordenadas[0]
        ancho_frame = max(int(datos_manos.get("anchoFrame", 1)), 1)
        centro_x = float(mano["anclas"]["centro_palma"]["x"])
        lado = "izquierda" if centro_x < (ancho_frame * 0.5) else "derecha"

        if lado == "izquierda":
            return {"palma derecha": mano, "palma izquierda": None}
        return {"palma derecha": None, "palma izquierda": mano}

    def _construir_capas_desde_modelo(self) -> list[dict[str, Any]]:
        if not RUTA_MODELO_MAPA.exists():
            return self._capas_por_defecto()

        imagen_modelo = cv2.imread(str(RUTA_MODELO_MAPA), cv2.IMREAD_UNCHANGED)
        if imagen_modelo is None:
            return self._capas_por_defecto()

        h_modelo, w_modelo = imagen_modelo.shape[:2]
        max_lado = max(h_modelo, w_modelo)
        escala_modelo = 1.0
        if max_lado > 1800:
            escala_modelo = 1800.0 / float(max_lado)
            imagen_modelo = cv2.resize(
                imagen_modelo,
                (int(w_modelo * escala_modelo), int(h_modelo * escala_modelo)),
                interpolation=cv2.INTER_AREA,
            )

        gris_modelo = cv2.cvtColor(imagen_modelo[:, :, :3], cv2.COLOR_BGR2GRAY)
        manos_modelo = self._detectar_manos_modelo(imagen_modelo)
        if not manos_modelo:
            return self._capas_por_defecto()

        capas: list[dict[str, Any]] = []
        for categoria in CATEGORIAS_ILUSTRACIONES:
            carpeta = DIRECTORIO_ASSETS / categoria
            if not carpeta.exists():
                continue

            estilo = ESTILO_POR_CATEGORIA.get(categoria, {})
            for ruta_archivo in sorted(carpeta.glob("*.png")):
                info = self._buscar_en_modelo(gris_modelo, ruta_archivo, escala_modelo)
                if info is None:
                    continue

                lado = self._lado_mas_cercano(info["centro"], manos_modelo)
                centro_mano = manos_modelo[lado]["centro"]
                ancho_mano = max(float(manos_modelo[lado]["ancho"]), 1.0)

                dx_rel = (float(info["centro"][0]) - float(centro_mano[0])) / ancho_mano
                dy_rel = (float(info["centro"][1]) - float(centro_mano[1])) / ancho_mano

                escala_categoria = float(estilo.get("escala", 1.0))
                escala_base = (190.0 / ancho_mano) * escala_categoria

                ruta_relativa = str(Path(categoria) / ruta_archivo.name)
                ruta_web = "/assets/" + quote(Path(ruta_relativa).as_posix(), safe="/")

                capas.append(
                    {
                        "id": self._normalizar_id(ruta_archivo.stem),
                        "src": ruta_web,
                        "ladoModelo": lado,
                        "dxRel": dx_rel,
                        "dyRel": dy_rel,
                        "escalaBase": escala_base,
                        "opacidad": float(estilo.get("opacidad", 0.9)),
                        "fusion": estilo.get("fusion", "source-over"),
                        "score": float(info["score"]),
                    }
                )

        return capas if capas else self._capas_por_defecto()

    @staticmethod
    def _detectar_manos_modelo(imagen_modelo: np.ndarray) -> dict[str, dict[str, Any]]:
        bgr = imagen_modelo[:, :, :3]
        b = bgr[:, :, 0].astype(np.int16)
        g = bgr[:, :, 1].astype(np.int16)
        r = bgr[:, :, 2].astype(np.int16)

        mascara = ((r > 125) & (r > g + 12) & (r > b + 8)).astype(np.uint8) * 255
        mascara = cv2.medianBlur(mascara, 7)
        h, w = mascara.shape[:2]
        mitad = w // 2
        salida: dict[str, dict[str, Any]] = {}

        for lado, x0, x1 in [
            ("palma izquierda", 0, mitad),
            ("palma derecha", mitad, w),
        ]:
            sub = mascara[:, x0:x1]
            ys, xs = np.where(sub > 0)
            if len(xs) < 50:
                continue

            min_x = int(xs.min()) + x0
            max_x = int(xs.max()) + x0
            min_y = int(ys.min())
            max_y = int(ys.max())
            ancho = max(1, max_x - min_x + 1)
            alto = max(1, max_y - min_y + 1)
            salida[lado] = {
                "bbox": (min_x, min_y, ancho, alto),
                "centro": (min_x + (ancho / 2.0), min_y + (alto / 2.0)),
                "ancho": float(ancho),
                "alto": float(alto),
            }

        if "palma izquierda" not in salida or "palma derecha" not in salida:
            return {}
        return salida

    @staticmethod
    def _buscar_en_modelo(
        gris_modelo: np.ndarray, ruta_archivo: Path, escala_modelo: float
    ) -> dict[str, Any] | None:
        img = cv2.imread(str(ruta_archivo), cv2.IMREAD_UNCHANGED)
        if img is None:
            return None

        if escala_modelo < 0.999:
            h, w = img.shape[:2]
            nuevo_w = max(12, int(w * escala_modelo))
            nuevo_h = max(12, int(h * escala_modelo))
            img = cv2.resize(img, (nuevo_w, nuevo_h), interpolation=cv2.INTER_AREA)

        if img.ndim == 2:
            gris = img
            mascara = (gris > 8).astype(np.uint8) * 255
        else:
            gris = cv2.cvtColor(img[:, :, :3], cv2.COLOR_BGR2GRAY)
            if img.shape[2] == 4:
                mascara = (img[:, :, 3] > 8).astype(np.uint8) * 255
            else:
                mascara = (gris > 8).astype(np.uint8) * 255

        ys, xs = np.where(mascara > 0)
        if len(xs) < 12:
            return None

        x0, x1 = int(xs.min()), int(xs.max())
        y0, y1 = int(ys.min()), int(ys.max())
        gris_crop = gris[y0 : y1 + 1, x0 : x1 + 1]

        if (
            gris_modelo.shape[0] < gris_crop.shape[0]
            or gris_modelo.shape[1] < gris_crop.shape[1]
        ):
            return None

        resultado = cv2.matchTemplate(gris_modelo, gris_crop, cv2.TM_CCOEFF_NORMED)
        _, maxv, _, maxloc = cv2.minMaxLoc(resultado)

        h, w = gris_crop.shape[:2]
        centro = (maxloc[0] + (w / 2.0), maxloc[1] + (h / 2.0))
        return {"centro": centro, "score": float(maxv), "ancho": w, "alto": h}

    @staticmethod
    def _lado_mas_cercano(
        centro: tuple[float, float], manos_modelo: dict[str, dict[str, Any]]
    ) -> str:
        cx = centro[0]
        izq = manos_modelo["palma izquierda"]["centro"][0]
        der = manos_modelo["palma derecha"]["centro"][0]
        return "palma izquierda" if abs(cx - izq) <= abs(cx - der) else "palma derecha"

    @staticmethod
    def _normalizar_id(texto: str) -> str:
        return re.sub(r"[^a-z0-9_]+", "_", texto.lower()).strip("_")

    @staticmethod
    def _capas_por_defecto() -> list[dict[str, Any]]:
        return []

    @staticmethod
    def _limpiar_comentarios_json(texto: str) -> str:
        # Permite comentarios tipo // y /* */ para facilitar edicion manual.
        sin_bloques = re.sub(r"/\*.*?\*/", "", texto, flags=re.DOTALL)
        sin_linea = re.sub(r"(^|\s)//.*$", "", sin_bloques, flags=re.MULTILINE)
        return sin_linea

    @staticmethod
    def _correccion_rotacion_por_lado(lado: str) -> float:
        lado_norm = str(lado).strip().lower()
        if lado_norm == "palma izquierda":
            return float(CORRECCION_ROTACION_IZQUIERDA)
        if lado_norm == "palma derecha":
            return float(CORRECCION_ROTACION_DERECHA)
        return 0.0


def generar_documento_anclajes() -> None:
    m = MapeadorPalma()
    if RUTA_ANCLAJES_MANO.exists():
        return

    capas = []
    for capa in m.capas_ancladas:
        src = str(capa.get("src", ""))
        if not src.startswith("/assets/"):
            continue
        archivo_rel = unquote(src.replace("/assets/", "", 1))
        capas.append(
            {
                "id": capa["id"],
                "archivo": archivo_rel,
                "manoObjetivo": capa.get("manoObjetivo", "ambas"),
                "ancla": capa.get("ancla", "centro_palma"),
                "desplazamientoRel": capa.get("desplazamientoRel", [0.0, 0.0]),
                "escalaRel": capa.get("escalaRel", 1.0),
                "opacidad": capa.get("opacidad", 1.0),
                "fusion": capa.get("fusion", "source-over"),
                "rotacionExtra": capa.get("rotacionExtra", 0.0),
            }
        )

    payload = {
        "version": 1,
        "descripcion": "Anclajes manuales de capas por mano y por punto.",
        "anclasDisponibles": [
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
        ],
        "manosDisponibles": ["palma izquierda", "palma derecha", "ambas"],
        "capas": capas,
    }

    RUTA_ANCLAJES_MANO.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
