import { copyFile, mkdir, readdir, stat, writeFile } from "node:fs/promises";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const raiz = dirname(dirname(fileURLToPath(import.meta.url)));
const origenWasm = join(raiz, "node_modules", "@mediapipe", "tasks-vision", "wasm");
const destinoWasm = join(raiz, "public", "wasm");
const rutaModelo = join(raiz, "public", "models", "hand_landmarker.task");
const urlModelo =
  "https://storage.googleapis.com/mediapipe-models/hand_landmarker/hand_landmarker/float16/1/hand_landmarker.task";

await mkdir(destinoWasm, { recursive: true });
await mkdir(dirname(rutaModelo), { recursive: true });

for (const nombre of await readdir(origenWasm)) {
  await copyFile(join(origenWasm, nombre), join(destinoWasm, nombre));
}

let modeloListo = false;
try {
  modeloListo = (await stat(rutaModelo)).size > 0;
} catch {
  modeloListo = false;
}

if (!modeloListo) {
  const respuesta = await fetch(urlModelo);
  if (!respuesta.ok) {
    throw new Error(`No se pudo descargar el modelo de manos (${respuesta.status})`);
  }
  await writeFile(rutaModelo, new Uint8Array(await respuesta.arrayBuffer()));
}
