const INDICES_ANCLAS = {
  muneca: 0,
  base_pulgar: 2,
  punta_pulgar: 4,
  base_indice: 5,
  punta_indice: 8,
  base_medio: 9,
  punta_medio: 12,
  base_anular: 13,
  punta_anular: 16,
  base_menique: 17,
  punta_menique: 20,
};

export function normalizarLado(valor) {
  const texto = String(valor ?? "").trim().toLowerCase();
  if (["left", "izquierda", "left hand", "mano izquierda", "palma izquierda"].includes(texto)) {
    return "palma izquierda";
  }
  if (["right", "derecha", "right hand", "mano derecha", "palma derecha"].includes(texto)) {
    return "palma derecha";
  }
  return "desconocida";
}

export function normalizarLadoMediaPipe(valor) {
  const ladoDetectado = normalizarLado(valor);
  if (ladoDetectado === "palma izquierda") {
    return "palma derecha";
  }
  if (ladoDetectado === "palma derecha") {
    return "palma izquierda";
  }
  return ladoDetectado;
}

function puntoEnPixeles(punto, ancho, alto) {
  return { x: punto.x * ancho, y: punto.y * alto };
}

function centroide(puntos) {
  return {
    x: puntos.reduce((suma, punto) => suma + punto.x, 0) / puntos.length,
    y: puntos.reduce((suma, punto) => suma + punto.y, 0) / puntos.length,
  };
}

function distancia(a, b) {
  return Math.hypot(a.x - b.x, a.y - b.y);
}

export function puntuacionApertura(puntos) {
  return [
    [8, 6],
    [12, 10],
    [16, 14],
    [20, 18],
  ].reduce((total, [punta, articulacion]) => total + (puntos[punta].y < puntos[articulacion].y ? 1 : 0), 0);
}

export function procesarResultadoManos(resultado, anchoFrame, altoFrame) {
  const gruposPuntos = resultado?.landmarks ?? [];
  const gruposLateralidad = resultado?.handednesses ?? resultado?.handedness ?? [];

  const manos = gruposPuntos.map((puntos, indice) => {
    const lateralidad = gruposLateralidad[indice]?.[0];
    const etiqueta = lateralidad?.categoryName ?? lateralidad?.displayName ?? "Unknown";
    const puntosPx = puntos.map((punto) => puntoEnPixeles(punto, anchoFrame, altoFrame));
    const anclas = Object.fromEntries(
      Object.entries(INDICES_ANCLAS).map(([nombre, posicion]) => [nombre, puntosPx[posicion]]),
    );

    anclas.centro_palma = centroide([
      anclas.muneca,
      anclas.base_indice,
      anclas.base_medio,
      anclas.base_anular,
      anclas.base_menique,
    ]);

    const apertura = puntuacionApertura(puntos);
    return {
      idMano: indice,
      presente: true,
      esPalma: apertura >= 2,
      lateralidad: etiqueta,
      // MediaPipe clasifica pensando en una entrada tipo selfie (espejada).
      // El video se procesa sin espejo y se refleja solo al dibujarlo.
      lado: normalizarLadoMediaPipe(etiqueta),
      confianzaLado: lateralidad?.score ?? 0,
      puntuacionApertura: apertura,
      puntos,
      anclas,
      anchoPalma: distancia(anclas.base_indice, anclas.base_menique),
      anguloPalma: Math.atan2(
        anclas.base_menique.y - anclas.base_indice.y,
        anclas.base_menique.x - anclas.base_indice.x,
      ),
    };
  });

  return {
    hayManos: manos.length > 0,
    manos,
    anchoFrame,
    altoFrame,
  };
}
