import test from "node:test";
import assert from "node:assert/strict";

import {
  normalizarLado,
  normalizarLadoMediaPipe,
  procesarResultadoManos,
  puntuacionApertura,
} from "../src/logica-manos.js";
import { calcularCapas } from "../src/mapeador.js";

function puntosAbiertos() {
  return Array.from({ length: 21 }, (_, indice) => ({
    x: 0.2 + indice * 0.01,
    y: 0.7,
    z: 0,
  })).map((punto, indice, puntos) => {
    if ([8, 12, 16, 20].includes(indice)) {
      return { ...punto, y: 0.2 };
    }
    if ([6, 10, 14, 18].includes(indice)) {
      return { ...punto, y: 0.4 };
    }
    return puntos[indice];
  });
}

test("normaliza la lateralidad entregada por MediaPipe", () => {
  assert.equal(normalizarLado("Left"), "palma izquierda");
  assert.equal(normalizarLado("Right"), "palma derecha");
  assert.equal(normalizarLadoMediaPipe("Left"), "palma derecha");
  assert.equal(normalizarLadoMediaPipe("Right"), "palma izquierda");
});

test("reconoce una palma abierta y produce anclas en píxeles", () => {
  const puntos = puntosAbiertos();
  assert.equal(puntuacionApertura(puntos), 4);

  const resultado = procesarResultadoManos(
    {
      landmarks: [puntos],
      handednesses: [[{ categoryName: "Right", score: 0.98 }]],
    },
    640,
    480,
  );

  assert.equal(resultado.manos[0].esPalma, true);
  assert.equal(resultado.manos[0].lado, "palma izquierda");
  assert.equal(resultado.manos[0].anclas.punta_indice.x, puntos[8].x * 640);
});

test("mapea una ilustración únicamente a la mano objetivo", () => {
  const mano = {
    idMano: 0,
    esPalma: true,
    lado: "palma derecha",
    anchoPalma: 95,
    anguloPalma: 0.25,
    anclas: { centro_palma: { x: 100, y: 120 } },
  };
  const configuracion = {
    capas: [
      {
        id: "mapa",
        archivo: "mapa.png",
        manoObjetivo: "palma derecha",
        ancla: "centro_palma",
        desplazamientoRel: [0.5, -0.25],
        escalaRel: 0.2,
      },
    ],
  };

  const capas = calcularCapas({ manos: [mano] }, configuracion, () => "mapa.png");
  assert.equal(capas.length, 1);
  assert.equal(capas[0].x, 147.5);
  assert.equal(capas[0].y, 96.25);
  assert.equal(capas[0].escala, 0.1);
});
