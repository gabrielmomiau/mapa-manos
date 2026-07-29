import { FilesetResolver, HandLandmarker } from "@mediapipe/tasks-vision";

export async function crearDetectorManos() {
  const base = import.meta.env.BASE_URL;
  const vision = await FilesetResolver.forVisionTasks(`${base}wasm`);
  const opciones = {
    baseOptions: {
      modelAssetPath: `${base}models/hand_landmarker.task`,
      delegate: "GPU",
    },
    runningMode: "VIDEO",
    numHands: 2,
    minHandDetectionConfidence: 0.55,
    minHandPresenceConfidence: 0.55,
    minTrackingConfidence: 0.55,
  };

  try {
    return await HandLandmarker.createFromOptions(vision, opciones);
  } catch (errorGPU) {
    console.warn("No se pudo usar aceleración gráfica; se usará CPU.", errorGPU);
    return HandLandmarker.createFromOptions(vision, {
      ...opciones,
      baseOptions: {
        ...opciones.baseOptions,
        delegate: "CPU",
      },
    });
  }
}
