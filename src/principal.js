import "./styles.css";
import { guardarCaptura } from "./almacen.js";
import { crearDetectorManos } from "./detector.js";
import { procesarResultadoManos } from "./logica-manos.js";
import { calcularCapas } from "./mapeador.js";
import { anclajes, resolverImagen } from "./recursos.js";

const video = document.getElementById("camara");
const lienzo = document.getElementById("escena");
const contexto = lienzo.getContext("2d", { alpha: false });
const inicio = document.getElementById("inicio");
const botonActivar = document.getElementById("activarCamara");
const estadoInicio = document.getElementById("estadoInicio");
const statusCard = document.getElementById("statusCard");
const cacheImagenes = new Map();

const TIEMPO_INICIAL_RELACION = 5000;
const TIEMPO_PALMAS = 3000;
const TIEMPO_QUIETO = 1200;
const DURACION_FLASH = 2000;
const INTERVALO_DETECCION = 1000 / 24;

let detector = null;
let datosManos = { manos: [], hayManos: false };
let capas = [];
let ultimaMarcaVideo = -1;
let ultimaDeteccion = 0;
let capturaEnCurso = false;
let animacion = 0;
let estadoSecuencia = estadoSecuenciaInicial();

preparar();

async function preparar() {
  ajustarLienzo();
  window.addEventListener("resize", ajustarLienzo);
  botonActivar.addEventListener("click", activarCamara);

  try {
    detector = await crearDetectorManos();
    estadoInicio.textContent = "Todo está listo.";
    botonActivar.disabled = false;
  } catch (error) {
    console.error(error);
    estadoInicio.textContent = "No fue posible cargar el reconocimiento de manos.";
  }
}

async function activarCamara() {
  botonActivar.disabled = true;
  estadoInicio.textContent = "Solicitando acceso a la cámara…";

  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      audio: false,
      video: {
        width: { ideal: 640 },
        height: { ideal: 480 },
        facingMode: "user",
      },
    });
    video.srcObject = stream;
    await video.play();
    inicio.classList.add("oculto");
    mostrarFeedbackPorDefecto();
    animacion = requestAnimationFrame(ciclo);
  } catch (error) {
    console.error(error);
    estadoInicio.textContent = mensajeErrorCamara(error);
    botonActivar.disabled = false;
  }
}

function ciclo(marcaTiempo) {
  if (video.readyState >= HTMLMediaElement.HAVE_CURRENT_DATA) {
    detectar(marcaTiempo);
    renderizar();
  }
  animacion = requestAnimationFrame(ciclo);
}

function detectar(marcaTiempo) {
  if (
    !detector ||
    video.currentTime === ultimaMarcaVideo ||
    marcaTiempo - ultimaDeteccion < INTERVALO_DETECCION
  ) {
    return;
  }

  ultimaMarcaVideo = video.currentTime;
  ultimaDeteccion = marcaTiempo;

  try {
    const resultado = detector.detectForVideo(video, marcaTiempo);
    datosManos = procesarResultadoManos(resultado, video.videoWidth, video.videoHeight);
    capas = calcularCapas(datosManos, anclajes, resolverImagen);
    actualizarSecuenciaCaptura(marcaTiempo);
  } catch (error) {
    console.error("Falló una detección de manos", error);
  }
}

function renderizar() {
  contexto.clearRect(0, 0, lienzo.width, lienzo.height);
  const meta = dibujarFotogramaCobertura(video, true);

  for (const capa of capas) {
    const imagen = obtenerImagen(capa.src);
    if (!imagen.complete || imagen.naturalWidth === 0) {
      continue;
    }

    const ancla = mapearPunto(capa.x, capa.y, meta, true);
    const ancho = imagen.naturalWidth * capa.escala * meta.escala;
    const alto = imagen.naturalHeight * capa.escala * meta.escala;

    contexto.save();
    contexto.globalAlpha = capa.opacidad;
    contexto.globalCompositeOperation = capa.fusion;
    contexto.translate(ancla.x, ancla.y);
    contexto.rotate(capa.rotacion);
    contexto.drawImage(imagen, -ancho / 2, -alto / 2, ancho, alto);
    contexto.restore();
  }
}

function dibujarFotogramaCobertura(origen, espejo) {
  const anchoOrigen = origen.videoWidth || 640;
  const altoOrigen = origen.videoHeight || 480;
  const escala = Math.max(lienzo.width / anchoOrigen, lienzo.height / altoOrigen);
  const anchoDibujo = anchoOrigen * escala;
  const altoDibujo = altoOrigen * escala;
  const desplazamientoX = (lienzo.width - anchoDibujo) / 2;
  const desplazamientoY = (lienzo.height - altoDibujo) / 2;

  contexto.save();
  if (espejo) {
    contexto.translate(lienzo.width, 0);
    contexto.scale(-1, 1);
  }
  contexto.drawImage(origen, desplazamientoX, desplazamientoY, anchoDibujo, altoDibujo);
  contexto.restore();

  return { anchoOrigen, altoOrigen, escala, desplazamientoX, desplazamientoY };
}

function mapearPunto(x, y, meta, espejo) {
  const origenX = espejo ? meta.anchoOrigen - x : x;
  return {
    x: meta.desplazamientoX + origenX * meta.escala,
    y: meta.desplazamientoY + y * meta.escala,
  };
}

function obtenerImagen(src) {
  if (!cacheImagenes.has(src)) {
    const imagen = new Image();
    imagen.src = src;
    cacheImagenes.set(src, imagen);
  }
  return cacheImagenes.get(src);
}

function actualizarSecuenciaCaptura(ahora) {
  if (capturaEnCurso) {
    return;
  }

  const palmas = datosManos.manos.filter((mano) => mano.esPalma).length;
  if (palmas < 2) {
    reiniciarSecuencia();
    mostrarFeedbackPorDefecto();
    return;
  }

  mostrarFeedbackVacio();

  if (!estadoSecuencia.inicioRelacion) {
    estadoSecuencia.inicioRelacion = ahora;
  }
  if (ahora - estadoSecuencia.inicioRelacion < TIEMPO_INICIAL_RELACION) {
    return;
  }

  if (!estadoSecuencia.inicioPalmas) {
    estadoSecuencia.inicioPalmas = ahora;
  }
  if (ahora - estadoSecuencia.inicioPalmas < TIEMPO_PALMAS) {
    mostrarMensaje("Mantén las dos palmas para tomar una foto");
    return;
  }

  if (!estadoSecuencia.momentoCaptura) {
    estadoSecuencia.momentoCaptura = ahora + TIEMPO_QUIETO;
    return;
  }

  if (ahora >= estadoSecuencia.momentoCaptura) {
    iniciarCaptura();
  }
}

function iniciarCaptura() {
  capturaEnCurso = true;
  statusCard.textContent = "";
  statusCard.className = "status-card visible capture-flash";

  window.setTimeout(async () => {
    try {
      const blob = await canvasABlob(lienzo);
      await guardarCaptura(blob);
      mostrarMensaje("Captura guardada");
    } catch (error) {
      console.error(error);
      mostrarMensaje("No se pudo guardar la captura");
    } finally {
      capturaEnCurso = false;
      reiniciarSecuencia();
      window.setTimeout(mostrarFeedbackPorDefecto, 1500);
    }
  }, DURACION_FLASH);
}

function mostrarMensaje(mensaje) {
  statusCard.textContent = mensaje;
  statusCard.className = "status-card visible feedback-live";
}

function mostrarFeedbackVacio() {
  statusCard.textContent = "";
  statusCard.className = "status-card visible feedback-live";
}

function mostrarFeedbackPorDefecto() {
  statusCard.textContent = "";
  statusCard.className = "status-card visible portada";
}

function reiniciarSecuencia() {
  estadoSecuencia = estadoSecuenciaInicial();
}

function estadoSecuenciaInicial() {
  return { inicioRelacion: 0, inicioPalmas: 0, momentoCaptura: 0 };
}

function canvasABlob(canvas) {
  return new Promise((resolve, reject) => {
    canvas.toBlob((blob) => (blob ? resolve(blob) : reject(new Error("Canvas vacío"))), "image/png");
  });
}

function ajustarLienzo() {
  const pixelRatio = Math.min(window.devicePixelRatio || 1, 2);
  lienzo.width = Math.round(window.innerWidth * pixelRatio);
  lienzo.height = Math.round(window.innerHeight * pixelRatio);
}

function mensajeErrorCamara(error) {
  if (!window.isSecureContext) {
    return "La cámara necesita HTTPS o localhost.";
  }
  if (error?.name === "NotAllowedError") {
    return "Necesitamos permiso para usar la cámara.";
  }
  if (error?.name === "NotFoundError") {
    return "No encontramos una cámara disponible.";
  }
  return "No fue posible iniciar la cámara.";
}

window.addEventListener("beforeunload", () => {
  cancelAnimationFrame(animacion);
  for (const pista of video.srcObject?.getTracks?.() ?? []) {
    pista.stop();
  }
  detector?.close();
});
