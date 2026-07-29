import "./styles.css";
import { eliminarCaptura, listarCapturas } from "./almacen.js";

const galeria = document.getElementById("galleryGrid");
const aviso = document.getElementById("archivoHint");
const modal = document.getElementById("archivoPreviewModal");
const imagenPreview = document.getElementById("archivoPreviewImage");
const cerrarPreview = document.getElementById("archivoPreviewClose");
let urlsTemporales = [];

cerrarPreview.addEventListener("click", cerrarModal);
modal.addEventListener("click", (evento) => {
  if (evento.target === modal) {
    cerrarModal();
  }
});
document.addEventListener("keydown", (evento) => {
  if (evento.key === "Escape") {
    cerrarModal();
  }
});

actualizarGaleria();

async function actualizarGaleria() {
  limpiarUrls();
  galeria.replaceChildren();

  try {
    const capturas = await listarCapturas();
    aviso.hidden = capturas.length > 0;
    aviso.textContent = "Aún no hay capturas en este dispositivo.";

    for (const captura of capturas) {
      galeria.append(crearTarjeta(captura));
    }
  } catch (error) {
    console.error(error);
    aviso.hidden = false;
    aviso.textContent = "No fue posible abrir el archivo local.";
  }
}

function crearTarjeta(captura) {
  const url = URL.createObjectURL(captura.blob);
  urlsTemporales.push(url);

  const tarjeta = document.createElement("article");
  tarjeta.className = "gallery-item";

  const botonImagen = document.createElement("button");
  botonImagen.className = "gallery-image-link";
  botonImagen.type = "button";
  botonImagen.setAttribute("aria-label", `Abrir ${captura.nombre}`);
  botonImagen.addEventListener("click", () => abrirModal(url, captura.nombre));

  const imagen = document.createElement("img");
  imagen.src = url;
  imagen.alt = captura.nombre;
  botonImagen.append(imagen);

  const pie = document.createElement("div");
  pie.className = "gallery-meta";

  const nombre = document.createElement("span");
  nombre.textContent = captura.nombre;

  const acciones = document.createElement("div");
  acciones.className = "gallery-actions";

  const compartir = document.createElement("button");
  compartir.className = "gallery-share";
  compartir.type = "button";
  compartir.textContent = "↗";
  compartir.title = "Compartir";
  compartir.setAttribute("aria-label", `Compartir ${captura.nombre}`);
  compartir.hidden = !puedeCompartirArchivo(captura);
  compartir.addEventListener("click", () => compartirCaptura(captura, url));

  const descargar = document.createElement("button");
  descargar.className = "gallery-download";
  descargar.type = "button";
  descargar.textContent = "↓";
  descargar.title = "Descargar";
  descargar.setAttribute("aria-label", `Descargar ${captura.nombre}`);
  descargar.addEventListener("click", () => descargarCaptura(captura, url));

  const borrar = document.createElement("button");
  borrar.className = "gallery-delete";
  borrar.type = "button";
  borrar.textContent = "×";
  borrar.title = "Borrar";
  borrar.setAttribute("aria-label", `Borrar ${captura.nombre}`);
  borrar.addEventListener("click", async () => {
    await eliminarCaptura(captura.id);
    await actualizarGaleria();
  });

  acciones.append(compartir, descargar, borrar);
  pie.append(nombre, acciones);
  tarjeta.append(botonImagen, pie);
  return tarjeta;
}

async function compartirCaptura(captura, url) {
  const archivo = crearArchivo(captura);
  const datos = { files: [archivo], title: "La soldadura del mundo" };

  if (navigator.share && navigator.canShare?.(datos)) {
    try {
      await navigator.share(datos);
      return;
    } catch (error) {
      if (error?.name === "AbortError") {
        return;
      }
      console.warn("No se pudo compartir; se descargará la imagen.", error);
    }
  }

  descargarCaptura(captura, url);
}

function puedeCompartirArchivo(captura) {
  if (!navigator.share || !navigator.canShare) {
    return false;
  }
  return navigator.canShare({ files: [crearArchivo(captura)] });
}

function crearArchivo(captura) {
  return new File([captura.blob], captura.nombre, { type: "image/png" });
}

function descargarCaptura(captura, url) {
  const enlace = document.createElement("a");
  enlace.href = url;
  enlace.download = captura.nombre;
  enlace.click();
}

function abrirModal(url, nombre) {
  imagenPreview.src = url;
  imagenPreview.alt = nombre;
  modal.classList.add("visible");
  modal.setAttribute("aria-hidden", "false");
  cerrarPreview.focus();
}

function cerrarModal() {
  modal.classList.remove("visible");
  modal.setAttribute("aria-hidden", "true");
  imagenPreview.src = "";
}

function limpiarUrls() {
  for (const url of urlsTemporales) {
    URL.revokeObjectURL(url);
  }
  urlsTemporales = [];
}

window.addEventListener("beforeunload", limpiarUrls);
