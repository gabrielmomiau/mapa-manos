import asyncio
import base64
import json
import logging
import os
import re
import smtplib
import time
from email.message import EmailMessage
from pathlib import Path
from typing import Any

import cv2
import numpy as np
from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .camara import FlujoCamara
from .configuracion import (
    CALIDAD_JPEG,
    DIRECTORIO_ASSETS,
    DIRECTORIO_CAPTURAS,
    DIRECTORIO_ESTATICO,
    ENVIAR_CAPA_BORDES,
    ENVIAR_FOTOGRAMA,
    FPS_OBJETIVO,
    UMBRAL_BORDE_ALTO,
    UMBRAL_BORDE_BAJO,
)
from .mapeador_palma import MapeadorPalma, generar_documento_anclajes
from .rastreador_mano import RastreadorMano

load_dotenv()

logging.basicConfig(level=logging.INFO)
LOGGER = logging.getLogger(__name__)

app = FastAPI(title="Mapa Manos")

DIRECTORIO_CAPTURAS.mkdir(parents=True, exist_ok=True)
app.mount("/estatico", StaticFiles(directory=str(DIRECTORIO_ESTATICO)), name="estatico")
app.mount("/assets", StaticFiles(directory=str(Path(DIRECTORIO_ASSETS))), name="assets")
app.mount("/capturas", StaticFiles(directory=str(DIRECTORIO_CAPTURAS)), name="capturas")

camara = FlujoCamara()
rastreador = RastreadorMano()
mapeador = MapeadorPalma()


@app.on_event("startup")
def startup_event() -> None:
    generar_documento_anclajes()
    camara.start()


@app.on_event("shutdown")
def shutdown_event() -> None:
    rastreador.close()
    camara.stop()


@app.get("/")
def index() -> FileResponse:
    return FileResponse(str(DIRECTORIO_ESTATICO / "index.html"))


@app.get("/archivo")
def archivo() -> FileResponse:
    return FileResponse(str(DIRECTORIO_ESTATICO / "archivo.html"))


@app.post("/api/capturar")
async def capturar(request: Request) -> dict[str, str]:
    content_type = request.headers.get("content-type", "")
    body = await request.body()

    if body:
        if "image/png" in content_type:
            datos = body
            extension = "png"
        elif "image/jpeg" in content_type or "image/jpg" in content_type:
            datos = body
            extension = "jpg"
        else:
            raise HTTPException(status_code=415, detail="Tipo de contenido no soportado")
    else:
        fotograma_bgr = camara.read()
        ok, encoded = cv2.imencode(
            ".jpg",
            fotograma_bgr,
            [int(cv2.IMWRITE_JPEG_QUALITY), int(CALIDAD_JPEG)],
        )
        if not ok:
            raise HTTPException(status_code=500, detail="No se pudo codificar la captura")
        datos = encoded.tobytes()
        extension = "jpg"

    nombre = _generar_nombre_captura(extension)
    ruta = DIRECTORIO_CAPTURAS / nombre
    try:
        ruta.write_bytes(datos)
    except OSError as exc:
        raise HTTPException(status_code=500, detail="No se pudo guardar la captura") from exc

    return {"url": f"/capturas/{nombre}", "nombre": nombre}


@app.get("/api/capturas")
def listar_capturas() -> dict[str, list[dict[str, str]]]:
    capturas = []
    if DIRECTORIO_CAPTURAS.exists():
        archivos = sorted(
            list(DIRECTORIO_CAPTURAS.glob("*.png"))
            + list(DIRECTORIO_CAPTURAS.glob("*.jpg"))
            + list(DIRECTORIO_CAPTURAS.glob("*.jpeg")),
            reverse=True,
        )
        for ruta in archivos:
            capturas.append({"url": f"/capturas/{ruta.name}", "nombre": ruta.name})
    return {"capturas": capturas}


@app.post("/api/enviar-correo")
async def enviar_correo(request: Request) -> dict[str, str]:
    try:
        payload = await request.json()
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=400, detail="JSON inválido") from exc

    email_destino = str(payload.get("email", "")).strip().lower()
    image_url = str(payload.get("imageUrl", "")).strip()

    if not email_destino or not image_url:
        raise HTTPException(status_code=400, detail="Correo e imagen son obligatorios")

    if not _enviar_correo_por_smtp(email_destino, image_url):
        raise HTTPException(status_code=500, detail="No se pudo enviar el correo desde el servidor de Enflujo")

    return {"mensaje": "La foto fue enviada al correo indicado."}


@app.delete("/api/capturas/{nombre}")
def eliminar_captura(nombre: str) -> dict[str, str]:
    ruta = DIRECTORIO_CAPTURAS / nombre
    if not ruta.exists() or not ruta.is_file():
        raise HTTPException(status_code=404, detail="La captura no existe")

    try:
        ruta.unlink()
    except OSError as exc:
        raise HTTPException(status_code=500, detail="No se pudo eliminar la captura") from exc

    return {"mensaje": f"Se eliminó la captura {nombre}"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.websocket("/ws/vivo")
async def flujo_vivo(ws: WebSocket) -> None:
    await ws.accept()
    LOGGER.info("WebSocket conectado")

    # Informá al cliente el modo de cámara para que decida si enviar frames
    await ws.send_text(json.dumps({"tipo": "config", "modoCamara": camara.mode or "desconocido"}))

    if camara.mode == "navegador":
        await _flujo_navegador(ws)
    else:
        await _flujo_servidor(ws)


async def _flujo_servidor(ws: WebSocket) -> None:
    """El servidor lee su cámara física y envía fotogramas al cliente."""
    intervalo_fotograma = 1.0 / max(FPS_OBJETIVO, 1)

    try:
        while True:
            inicio = time.perf_counter()
            fotograma_bgr = camara.read()
            datos_manos = rastreador.procesar(fotograma_bgr)
            capas = mapeador.calcular(datos_manos)

            carga_util: dict[str, Any] = {
                "tipo": "fotograma",
                "marcaTiempo": time.time(),
                "manos": datos_manos.get("manos", []),
                "hayManos": datos_manos.get("hayManos", False),
                "capas": capas,
                "modoCamara": camara.mode,
            }

            if ENVIAR_FOTOGRAMA:
                carga_util["fotograma"] = _codificar_jpeg(fotograma_bgr)

            if ENVIAR_CAPA_BORDES:
                carga_util["capaBordes"] = _codificar_capa_bordes(fotograma_bgr)

            await ws.send_text(json.dumps(carga_util))

            transcurrido = time.perf_counter() - inicio
            await asyncio.sleep(max(0.0, intervalo_fotograma - transcurrido))

    except WebSocketDisconnect:
        LOGGER.info("WebSocket desconectado")
    except Exception as exc:  # pragma: no cover
        LOGGER.exception("Error en flujo servidor: %s", exc)
        await ws.close(code=1011)


async def _flujo_navegador(ws: WebSocket) -> None:
    """El navegador envía fotogramas JPEG; el servidor devuelve detección de manos y capas."""
    try:
        while True:
            datos_raw = await ws.receive_bytes()
            arr = np.frombuffer(datos_raw, np.uint8)
            fotograma_bgr = cv2.imdecode(arr, cv2.IMREAD_COLOR)
            if fotograma_bgr is None:
                continue

            camara.inject(fotograma_bgr)
            datos_manos = rastreador.procesar(fotograma_bgr)
            capas = mapeador.calcular(datos_manos)

            carga_util: dict[str, Any] = {
                "tipo": "fotograma",
                "marcaTiempo": time.time(),
                "manos": datos_manos.get("manos", []),
                "hayManos": datos_manos.get("hayManos", False),
                "capas": capas,
                "modoCamara": camara.mode,
            }
            await ws.send_text(json.dumps(carga_util))

    except WebSocketDisconnect:
        LOGGER.info("WebSocket desconectado")
    except Exception as exc:  # pragma: no cover
        LOGGER.exception("Error en flujo navegador: %s", exc)
        await ws.close(code=1011)


def _generar_nombre_captura(extension: str) -> str:
    patron = re.compile(r"^graciasporvenir(\d{3})\.(.+)$")
    max_numero = 0

    for ruta in DIRECTORIO_CAPTURAS.glob(f"graciasporvenir*.{extension}"):
        coincidencia = patron.match(ruta.name)
        if coincidencia:
            max_numero = max(max_numero, int(coincidencia.group(1)))

    siguiente = max_numero + 1
    return f"graciasporvenir{str(siguiente).zfill(3)}.{extension}"


def _enviar_correo_por_smtp(destino: str, image_url: str) -> bool:
    host = os.getenv("ENFLUJO_SMTP_HOST")
    puerto = int(os.getenv("ENFLUJO_SMTP_PORT", "587"))
    usuario = os.getenv("ENFLUJO_SMTP_USER")
    password = os.getenv("ENFLUJO_SMTP_PASSWORD")
    remitente = os.getenv("ENFLUJO_EMAIL_FROM", usuario or "")

    if not all([host, puerto, usuario, password, remitente]):
        LOGGER.warning("Faltan variables SMTP de Enflujo para enviar correos")
        return False

    mensaje = EmailMessage()
    mensaje["Subject"] = "Gracias por venir"
    mensaje["From"] = remitente
    mensaje["To"] = destino
    mensaje.set_content(
        "Gracias por venir. Aquí está la foto de la instalación:\n\n"
        f"{image_url}\n"
    )

    try:
        with smtplib.SMTP(host, puerto) as servidor:
            servidor.starttls()
            servidor.login(usuario, password)
            servidor.send_message(mensaje)
    except smtplib.SMTPException as exc:
        LOGGER.exception("Error al enviar correo desde Enflujo: %s", exc)
        return False

    return True


def _codificar_jpeg(fotograma_bgr) -> str:
    ok, encoded = cv2.imencode(
        ".jpg",
        fotograma_bgr,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(CALIDAD_JPEG)],
    )
    if not ok:
        return ""
    return base64.b64encode(encoded.tobytes()).decode("ascii")


def _codificar_capa_bordes(fotograma_bgr) -> str:
    grises = cv2.cvtColor(fotograma_bgr, cv2.COLOR_BGR2GRAY)
    bordes = cv2.Canny(grises, UMBRAL_BORDE_BAJO, UMBRAL_BORDE_ALTO)
    borde_bgr = cv2.cvtColor(bordes, cv2.COLOR_GRAY2BGR)
    ok, encoded = cv2.imencode(
        ".jpg",
        borde_bgr,
        [int(cv2.IMWRITE_JPEG_QUALITY), int(CALIDAD_JPEG)],
    )
    if not ok:
        return ""
    return base64.b64encode(encoded.tobytes()).decode("ascii")
