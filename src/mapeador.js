import { normalizarLado } from "./logica-manos.js";

const CORRECCION_ROTACION = {
  "palma izquierda": Math.PI,
  "palma derecha": 0,
  desconocida: 0,
};

export function calcularCapas(datosManos, configuracion, resolverImagen) {
  const palmas = (datosManos?.manos ?? []).filter((mano) => mano.esPalma);
  if (palmas.length === 0) {
    return [];
  }

  const salida = [];
  for (const capa of configuracion?.capas ?? []) {
    const objetivo = normalizarObjetivo(capa.manoObjetivo);
    const src = resolverImagen(capa.archivo);
    if (!src) {
      continue;
    }

    for (const mano of palmas) {
      const lado = normalizarLado(mano.lado || mano.lateralidad);
      if (objetivo !== "ambas" && lado !== objetivo) {
        continue;
      }

      const nombreAncla = capa.ancla || "centro_palma";
      const ancla = mano.anclas?.[nombreAncla] ?? mano.anclas?.centro_palma;
      if (!ancla) {
        continue;
      }

      const anchoPalma = Math.max(Number(mano.anchoPalma) || 0, 1);
      const [dx, dy] = Array.isArray(capa.desplazamientoRel)
        ? capa.desplazamientoRel
        : [0, 0];

      salida.push({
        id: capa.id,
        src,
        x: ancla.x + Number(dx || 0) * anchoPalma,
        y: ancla.y + Number(dy || 0) * anchoPalma,
        rotacion:
          Number(mano.anguloPalma || 0) +
          (CORRECCION_ROTACION[lado] ?? 0) +
          Number(capa.rotacionExtra || 0),
        escala: Number(capa.escalaRel ?? 1) * (anchoPalma / 190),
        opacidad: Number(capa.opacidad ?? 1),
        fusion: capa.fusion || "source-over",
        idMano: mano.idMano,
        ladoDetectado: lado,
        ancla: nombreAncla,
      });
    }
  }
  return salida;
}

function normalizarObjetivo(valor) {
  const texto = String(valor ?? "ambas").trim().toLowerCase();
  return texto === "ambas" ? "ambas" : normalizarLado(texto);
}
