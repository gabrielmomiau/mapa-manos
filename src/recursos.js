import configuracionAnclajes from "../assets/anclajes_mano.json";

const modulosImagen = import.meta.glob(
  [
    "../assets/animales/*.png",
    "../assets/barcos/*.png",
    "../assets/nombres-lugares/*.png",
    "../assets/paisaje/*.png",
  ],
  { eager: true, query: "?url", import: "default" },
);

const imagenesPorRuta = new Map(
  Object.entries(modulosImagen).map(([ruta, url]) => [
    ruta.replace("../assets/", "").replaceAll("\\", "/"),
    url,
  ]),
);

export const anclajes = configuracionAnclajes;

export function resolverImagen(ruta) {
  return imagenesPorRuta.get(String(ruta).replaceAll("\\", "/")) ?? null;
}
