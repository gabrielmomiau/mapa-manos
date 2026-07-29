const statusCardEl = document.getElementById("statusCard");
const lienzo = document.getElementById("escena");
const contexto = lienzo ? lienzo.getContext("2d") : null;
const galleryGridEl = document.getElementById("galleryGrid");
const archivoHintEl = document.getElementById("archivoHint");
const archivoMailModalEl = document.getElementById("archivoMailModal");
const archivoMailCloseEl = document.getElementById("archivoMailClose");
const archivoMailCancelEl = document.getElementById("archivoMailCancel");
const archivoMailFormEl = document.getElementById("archivoMailForm");
const archivoMailInputEl = document.getElementById("archivoMailInput");
const archivoMailImageEl = document.getElementById("archivoMailImage");
const archivoMailMessageEl = document.getElementById("archivoMailMessage");
const archivoMailAtButtonEl = document.getElementById("archivoMailAtButton");
const archivoPreviewModalEl = document.getElementById("archivoPreviewModal");
const archivoPreviewCloseEl = document.getElementById("archivoPreviewClose");
const archivoPreviewImageEl = document.getElementById("archivoPreviewImage");

const imagenFotograma = new Image();
const imagenBordes = new Image();
const cacheCapas = new Map();

let modoNavegador = false;
let videoLocal = null;
let wsRef = null;

const FPS_CAMARA_NAVEGADOR = 24;
const canvasOffscreen = document.createElement("canvas");
canvasOffscreen.width = 640;
canvasOffscreen.height = 480;
const ctxOffscreen = canvasOffscreen.getContext("2d");

async function iniciarCamaraNavegador() {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({
      video: { width: { ideal: 640 }, height: { ideal: 480 }, facingMode: "user" },
    });
    videoLocal = document.createElement("video");
    videoLocal.autoplay = true;
    videoLocal.playsInline = true;
    videoLocal.muted = true;
    videoLocal.srcObject = stream;
    await new Promise((resolve) => {
      videoLocal.onloadedmetadata = resolve;
    });
    videoLocal.play();
    setInterval(enviarFrameAlServidor, 1000 / FPS_CAMARA_NAVEGADOR);
  } catch (err) {
    console.error("No se pudo acceder a la cámara:", err);
    mostrarMensaje("Se necesita permiso de cámara para continuar", "warning");
  }
}

function enviarFrameAlServidor() {
  if (!wsRef || wsRef.readyState !== WebSocket.OPEN || !videoLocal) {
    return;
  }
  if (videoLocal.readyState < 2) {
    return;
  }
  ctxOffscreen.drawImage(videoLocal, 0, 0, 640, 480);
  canvasOffscreen.toBlob(
    (blob) => {
      if (blob && wsRef && wsRef.readyState === WebSocket.OPEN) {
        wsRef.send(blob);
      }
    },
    "image/jpeg",
    0.75,
  );
}

let ultimoDato = {
  fotograma: "",
  capaBordes: "",
  manos: [],
  capas: [],
  modoCamara: "",
};

function definirEstado() {
  // No-op: el estado ya no se muestra en la interfaz.
}

function definirFeedback(mensaje, tipo = "info", visible = true) {
  if (!statusCardEl) {
    return;
  }

  statusCardEl.textContent = "";
  statusCardEl.dataset.type = tipo;

  if (visible) {
    statusCardEl.classList.add("visible");
  } else {
    statusCardEl.classList.remove("visible");
  }
}

function ocultarFeedback() {
  if (statusCardEl) {
    statusCardEl.classList.remove("capture-flash", "feedback-live", "portada");
  }
  definirFeedback("", "info", false);
}

function mostrarFeedbackPorDefecto() {
  if (!statusCardEl) {
    return;
  }

  statusCardEl.classList.remove("capture-flash", "feedback-live");
  statusCardEl.classList.add("portada");
  statusCardEl.textContent = "";
  statusCardEl.dataset.type = "info";
  statusCardEl.classList.add("visible");
}

let capturaEnCurso = false;
const TIEMPO_INICIAL_RELACION = 5000;
const TIEMPO_PALMAS = 3000;
const TIEMPO_QUIETO = 1200;
const DURACION_FLASH = 2000;

let estadoSecuencia = {
  inicioRelacion: 0,
  inicioPalmas: 0,
  esperandoQuieto: false,
  yaMostroQuieto: false,
};

function resetSecuenciaCaptura() {
  estadoSecuencia = {
    inicioRelacion: 0,
    inicioPalmas: 0,
    esperandoQuieto: false,
    yaMostroQuieto: false,
  };
}

function mostrarMensaje(mensaje, tipo = "info") {
  if (!statusCardEl) {
    return;
  }

  statusCardEl.textContent = mensaje;
  statusCardEl.dataset.type = tipo;
  statusCardEl.classList.remove("capture-flash", "portada");
  statusCardEl.classList.add("visible", "feedback-live");
}

function iniciarCaptura() {
  if (capturaEnCurso) {
    return;
  }

  capturaEnCurso = true;
  if (statusCardEl) {
    statusCardEl.classList.remove("capture-flash");
  }
  statusCardEl.classList.add("capture-flash");
  statusCardEl.textContent = "";
  setTimeout(() => {
    if (statusCardEl) {
      statusCardEl.classList.remove("capture-flash");
    }
    enviarCaptura();
  }, DURACION_FLASH);
}

async function generarNombreCaptura(extension = "png") {
  const prefijo = "graciasporvenir";
  const patron = new RegExp(`^${prefijo}(\\d{3})\\.${extension}$`);
  let maxNumero = 0;

  if (galleryGridEl) {
    const existentes = Array.from(galleryGridEl.querySelectorAll(".gallery-item"))
      .map((item) => item.dataset.nombre || "")
      .filter(Boolean);

    for (const nombre of existentes) {
      const coincidencia = nombre.match(patron);
      if (coincidencia) {
        maxNumero = Math.max(maxNumero, Number.parseInt(coincidencia[1], 10));
      }
    }
  }

  const siguiente = `${maxNumero + 1}`.padStart(3, "0");
  return `${prefijo}${siguiente}.${extension}`;
}

async function enviarCaptura() {
  if (!lienzo) {
    definirFeedback("Canvas no disponible", "warning", true);
    countdownActivo = false;
    return;
  }

  const blob = await new Promise((resolve) => lienzo.toBlob(resolve, "image/png"));
  if (!blob) {
    definirFeedback("No se pudo generar la imagen", "warning", true);
    countdownActivo = false;
    return;
  }

  try {
    const respuesta = await fetch("/api/capturar", {
      method: "POST",
      headers: { "Content-Type": "image/png" },
      body: blob,
    });
    if (!respuesta.ok) {
      throw new Error("Error al guardar la captura");
    }

    mostrarMensaje("Captura guardada", "success");
    actualizarGaleriaDesdeApi();
  } catch (error) {
    console.error(error);
    mostrarMensaje("No se pudo guardar la captura", "warning");
  } finally {
    capturaEnCurso = false;
    resetSecuenciaCaptura();
    setTimeout(mostrarFeedbackPorDefecto, 1500);
  }
}

function abrirPopupCorreo(imagenUrl, nombre) {
  if (!archivoMailModalEl || !archivoMailInputEl || !archivoMailImageEl || !archivoMailMessageEl) {
    return;
  }

  archivoMailImageEl.value = `${window.location.origin}${imagenUrl}`;
  archivoMailMessageEl.textContent = "";
  archivoMailInputEl.value = "";
  archivoMailModalEl.classList.add("visible");
  archivoMailModalEl.setAttribute("aria-hidden", "false");
  archivoMailInputEl.focus();
}

function cerrarPopupCorreo() {
  if (!archivoMailModalEl || !archivoMailInputEl || !archivoMailMessageEl) {
    return;
  }

  archivoMailModalEl.classList.remove("visible");
  archivoMailModalEl.setAttribute("aria-hidden", "true");
  archivoMailInputEl.value = "";
  archivoMailMessageEl.textContent = "";
}

function abrirPreviewFoto(imagenUrl) {
  if (!archivoPreviewModalEl || !archivoPreviewImageEl) {
    return;
  }

  archivoPreviewImageEl.src = imagenUrl;
  archivoPreviewModalEl.classList.add("visible");
  archivoPreviewModalEl.setAttribute("aria-hidden", "false");
}

function cerrarPreviewFoto() {
  if (!archivoPreviewModalEl || !archivoPreviewImageEl) {
    return;
  }

  archivoPreviewModalEl.classList.remove("visible");
  archivoPreviewModalEl.setAttribute("aria-hidden", "true");
  archivoPreviewImageEl.src = "";
}

function insertarArrobaEnCorreo() {
  if (!archivoMailInputEl) {
    return;
  }

  const input = archivoMailInputEl;
  const inicio = input.selectionStart ?? input.value.length;
  const fin = input.selectionEnd ?? input.value.length;
  const valorActual = input.value;
  const siguiente = `${valorActual.slice(0, inicio)}@${valorActual.slice(fin)}`;

  input.value = siguiente;
  const nuevaPosicion = inicio + 1;
  input.focus();
  input.setSelectionRange(nuevaPosicion, nuevaPosicion);
}

async function enviarCorreoPopup(evento) {
  evento.preventDefault();

  if (!archivoMailFormEl || !archivoMailInputEl || !archivoMailImageEl || !archivoMailMessageEl) {
    return;
  }

  const correo = archivoMailInputEl.value.trim();
  const imageUrl = archivoMailImageEl.value.trim();

  if (!correo || !imageUrl) {
    archivoMailMessageEl.textContent = "Completa tu correo para continuar.";
    return;
  }

  try {
    archivoMailMessageEl.textContent = "Enviando...";
    const respuesta = await fetch("/api/enviar-correo", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ email: correo, imageUrl }),
    });

    const datos = await respuesta.json();
    if (!respuesta.ok) {
      throw new Error(datos.detail || "No se pudo enviar el correo");
    }

    archivoMailMessageEl.textContent = datos.mensaje || "La foto fue enviada.";
    setTimeout(cerrarPopupCorreo, 1200);
  } catch (error) {
    console.error(error);
    archivoMailMessageEl.textContent = error.message || "No se pudo enviar el correo.";
  }
}

async function actualizarGaleriaDesdeApi() {
  if (!galleryGridEl) {
    return;
  }

  try {
    const respuesta = await fetch("/api/capturas");
    if (!respuesta.ok) {
      throw new Error("No se pudo cargar la galería");
    }

    const datos = await respuesta.json();
    const capturas = Array.isArray(datos.capturas) ? datos.capturas : [];

    if (galleryGridEl) {
      galleryGridEl.innerHTML = capturas
        .map((captura) => {
          return `<div class="gallery-item" data-nombre="${captura.nombre}">
            <button class="gallery-image-link" type="button" data-preview-url="${captura.url}" aria-label="Abrir foto en vista previa">
              <img src="${captura.url}" alt="${captura.nombre}" />
            </button>
            <div class="gallery-meta">
              <span>${captura.nombre}</span>
              <div class="gallery-actions">
                <button class="gallery-mail" type="button" data-image-url="${captura.url}" aria-label="Enviar foto por correo">✉</button>
                <button class="gallery-delete" type="button" data-nombre="${captura.nombre}" aria-label="Eliminar foto del archivo">🗑</button>
              </div>
            </div>
          </div>`;
        })
        .join("");

      galleryGridEl.querySelectorAll(".gallery-image-link").forEach((boton) => {
        boton.addEventListener("click", (evento) => {
          evento.preventDefault();
          const previewUrl = boton.dataset.previewUrl || "";
          abrirPreviewFoto(previewUrl);
        });
      });

      galleryGridEl.querySelectorAll(".gallery-mail").forEach((boton) => {
        boton.addEventListener("click", (evento) => {
          evento.preventDefault();
          const imagenUrl = boton.dataset.imageUrl || "";
          abrirPopupCorreo(imagenUrl, boton.closest(".gallery-item")?.dataset.nombre || "");
        });
      });

      galleryGridEl.querySelectorAll(".gallery-delete").forEach((boton) => {
        boton.addEventListener("click", async (evento) => {
          evento.preventDefault();
          const nombre = boton.dataset.nombre || "";

          if (!nombre) {
            return;
          }

          try {
            const respuesta = await fetch(`/api/capturas/${encodeURIComponent(nombre)}`, {
              method: "DELETE",
            });

            if (!respuesta.ok) {
              throw new Error("No se pudo eliminar la captura");
            }

            await actualizarGaleriaDesdeApi();
          } catch (error) {
            console.error(error);
          }
        });
      });
    }

    if (archivoHintEl) {
      archivoHintEl.style.display = capturas.length > 0 ? "none" : "block";
    }
  } catch (error) {
    console.error(error);
    if (archivoHintEl) {
      archivoHintEl.textContent = "No se pudo cargar las capturas.";
    }
  }
}

function obtenerImagenCapa(src) {
  if (!cacheCapas.has(src)) {
    const imagen = new Image();
    imagen.src = src;
    cacheCapas.set(src, imagen);
  }
  return cacheCapas.get(src);
}

function dibujarFotogramaCobertura(imagen, espejo = false) {
  const anchoOrigen = imagen.naturalWidth || imagen.videoWidth || 640;
  const altoOrigen = imagen.naturalHeight || imagen.videoHeight || 480;
  const anchoDestino = lienzo.width;
  const altoDestino = lienzo.height;

  const escala = Math.max(anchoDestino / anchoOrigen, altoDestino / altoOrigen);
  const anchoDibujo = anchoOrigen * escala;
  const altoDibujo = altoOrigen * escala;
  const desplazamientoX = (anchoDestino - anchoDibujo) * 0.5;
  const desplazamientoY = (altoDestino - altoDibujo) * 0.5;

  contexto.save();
  if (espejo) {
    contexto.setTransform(-1, 0, 0, 1, lienzo.width, 0);
  }
  contexto.drawImage(imagen, desplazamientoX, desplazamientoY, anchoDibujo, altoDibujo);
  contexto.restore();

  return {
    anchoOrigen,
    altoOrigen,
    escala,
    desplazamientoX,
    desplazamientoY,
  };
}

function mapearPuntoALienzo(x, y, metaFotograma, espejo = false) {
  const origenX = espejo ? metaFotograma.anchoOrigen - x : x;
  return {
    x: metaFotograma.desplazamientoX + origenX * metaFotograma.escala,
    y: metaFotograma.desplazamientoY + y * metaFotograma.escala,
  };
}

function dibujarCapas(metaFotograma) {
  for (const capa of ultimoDato.capas || []) {
    const imagen = obtenerImagenCapa(capa.src);
    if (!imagen.complete || imagen.naturalWidth === 0) {
      continue;
    }

    const puntoAncla = mapearPuntoALienzo(capa.x, capa.y, metaFotograma, true);
    const ancho = imagen.naturalWidth * capa.escala * metaFotograma.escala;
    const alto = imagen.naturalHeight * capa.escala * metaFotograma.escala;

    contexto.save();
    contexto.globalAlpha = capa.opacidad ?? 1;
    contexto.globalCompositeOperation = capa.fusion || "source-over";
    contexto.translate(puntoAncla.x, puntoAncla.y);
    contexto.rotate(capa.rotacion || 0);
    contexto.drawImage(imagen, -ancho * 0.5, -alto * 0.5, ancho, alto);
    contexto.restore();
  }
}

function dibujarPuntosMano(metaFotograma) {
  // Los nodos de la mano quedan ocultos para mantener la proyección limpia.
  return;
}

function renderizar() {
  if (!contexto || !lienzo) {
    return;
  }

  contexto.clearRect(0, 0, lienzo.width, lienzo.height);

  if (modoNavegador && videoLocal && videoLocal.readyState >= 2) {
    const metaFotograma = dibujarFotogramaCobertura(videoLocal, true);
    dibujarCapas(metaFotograma);
    dibujarPuntosMano(metaFotograma);
  } else if (imagenFotograma.complete && imagenFotograma.naturalWidth > 0) {
    const metaFotograma = dibujarFotogramaCobertura(imagenFotograma, true);

    if (imagenBordes.complete && imagenBordes.naturalWidth > 0) {
      contexto.save();
      contexto.globalAlpha = 0.24;
      contexto.globalCompositeOperation = "screen";
      dibujarFotogramaCobertura(imagenBordes, true);
      contexto.restore();
    }

    dibujarCapas(metaFotograma);
    dibujarPuntosMano(metaFotograma);
  }

  requestAnimationFrame(renderizar);
}

function conectarWebSocket() {
  if (!lienzo) {
    return;
  }

  const protocolo = window.location.protocol === "https:" ? "wss" : "ws";
  const ws = new WebSocket(`${protocolo}://${window.location.host}/ws/vivo`);
  wsRef = ws;

  ws.addEventListener("open", () => definirEstado("Conectado"));

  ws.addEventListener("message", (evento) => {
    const dato = JSON.parse(evento.data);

    // Primer mensaje: configuración del servidor
    if (dato.tipo === "config") {
      if (dato.modoCamara === "navegador") {
        modoNavegador = true;
        iniciarCamaraNavegador();
      }
      return;
    }

    ultimoDato = dato;

    if (dato.fotograma) {
      imagenFotograma.src = `data:image/jpeg;base64,${dato.fotograma}`;
    }

    if (dato.capaBordes) {
      imagenBordes.src = `data:image/jpeg;base64,${dato.capaBordes}`;
    }

    const palmas = Array.isArray(dato.manos)
      ? dato.manos.filter((m) => m.esPalma).length
      : 0;

    if (palmas >= 2) {
      if (!estadoSecuencia.inicioRelacion) {
        estadoSecuencia.inicioRelacion = performance.now();
      }

      if (statusCardEl) {
        statusCardEl.classList.remove("portada");
        statusCardEl.classList.add("feedback-live", "visible");
        statusCardEl.textContent = "";
      }

      const tiempoRelacion = performance.now() - estadoSecuencia.inicioRelacion;
      if (tiempoRelacion < TIEMPO_INICIAL_RELACION) {
        return;
      }

      if (!estadoSecuencia.inicioPalmas) {
        estadoSecuencia.inicioPalmas = performance.now();
      }

      const transcurrido = performance.now() - estadoSecuencia.inicioPalmas;
      if (transcurrido >= TIEMPO_PALMAS && !estadoSecuencia.yaMostroQuieto) {
        estadoSecuencia.yaMostroQuieto = true;
        estadoSecuencia.esperandoQuieto = true;
        mostrarMensaje("Quédate quieto para tomar una foto", "success");

        setTimeout(() => {
          if (!capturaEnCurso && estadoSecuencia.esperandoQuieto) {
            iniciarCaptura();
          }
        }, TIEMPO_QUIETO);
      } else if (!estadoSecuencia.yaMostroQuieto) {
        mostrarMensaje("Mantén las dos palmas para tomar una foto", "info");
      }
    } else {
      resetSecuenciaCaptura();
      mostrarFeedbackPorDefecto();
    }
  });

  ws.addEventListener("close", () => {
    wsRef = null;
    definirEstado("Desconectado. Reintentando...");
    setTimeout(conectarWebSocket, 1200);
  });

  ws.addEventListener("error", () => {
    wsRef = null;
    ws.close();
  });
}

if (galleryGridEl) {
  actualizarGaleriaDesdeApi();
}

if (archivoMailCloseEl) {
  archivoMailCloseEl.addEventListener("click", cerrarPopupCorreo);
}

if (archivoPreviewCloseEl) {
  archivoPreviewCloseEl.addEventListener("click", cerrarPreviewFoto);
}

if (archivoMailCancelEl) {
  archivoMailCancelEl.addEventListener("click", cerrarPopupCorreo);
}

if (archivoMailAtButtonEl) {
  archivoMailAtButtonEl.addEventListener("click", insertarArrobaEnCorreo);
}

if (archivoMailModalEl) {
  archivoMailModalEl.addEventListener("click", (evento) => {
    if (evento.target === archivoMailModalEl) {
      cerrarPopupCorreo();
    }
  });
}

if (archivoPreviewModalEl) {
  archivoPreviewModalEl.addEventListener("click", (evento) => {
    if (evento.target === archivoPreviewModalEl) {
      cerrarPreviewFoto();
    }
  });
}

if (archivoMailFormEl) {
  archivoMailFormEl.addEventListener("submit", enviarCorreoPopup);
}

mostrarFeedbackPorDefecto();
conectarWebSocket();
renderizar();
