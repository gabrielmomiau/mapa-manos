const NOMBRE_BASE = "mapa-manos";
const VERSION = 1;
const ALMACEN_CAPTURAS = "capturas";

function abrirBase() {
  return new Promise((resolve, reject) => {
    const solicitud = indexedDB.open(NOMBRE_BASE, VERSION);
    solicitud.onupgradeneeded = () => {
      const base = solicitud.result;
      if (!base.objectStoreNames.contains(ALMACEN_CAPTURAS)) {
        base.createObjectStore(ALMACEN_CAPTURAS, { keyPath: "id" });
      }
    };
    solicitud.onsuccess = () => resolve(solicitud.result);
    solicitud.onerror = () => reject(solicitud.error);
  });
}

async function ejecutar(modo, operacion) {
  const base = await abrirBase();
  return new Promise((resolve, reject) => {
    const transaccion = base.transaction(ALMACEN_CAPTURAS, modo);
    const almacen = transaccion.objectStore(ALMACEN_CAPTURAS);
    const solicitud = operacion(almacen);
    solicitud.onsuccess = () => resolve(solicitud.result);
    solicitud.onerror = () => reject(solicitud.error);
    transaccion.oncomplete = () => base.close();
    transaccion.onerror = () => reject(transaccion.error);
  });
}

export async function guardarCaptura(blob) {
  const id = Date.now();
  const fecha = new Date(id);
  const nombre = `graciasporvenir-${formatearFecha(fecha)}.png`;
  const captura = { id, nombre, creado: fecha.toISOString(), blob };
  await ejecutar("readwrite", (almacen) => almacen.put(captura));
  return captura;
}

export async function listarCapturas() {
  const capturas = await ejecutar("readonly", (almacen) => almacen.getAll());
  return capturas.sort((a, b) => b.id - a.id);
}

export function eliminarCaptura(id) {
  return ejecutar("readwrite", (almacen) => almacen.delete(id));
}

function formatearFecha(fecha) {
  const partes = [
    fecha.getFullYear(),
    String(fecha.getMonth() + 1).padStart(2, "0"),
    String(fecha.getDate()).padStart(2, "0"),
    "-",
    String(fecha.getHours()).padStart(2, "0"),
    String(fecha.getMinutes()).padStart(2, "0"),
    String(fecha.getSeconds()).padStart(2, "0"),
  ];
  return partes.join("");
}
