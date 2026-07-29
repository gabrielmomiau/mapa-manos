import test from "node:test";
import assert from "node:assert/strict";
import { access, readFile } from "node:fs/promises";
import { resolve } from "node:path";

test("todos los anclajes apuntan a ilustraciones existentes", async () => {
  const rutaConfiguracion = resolve("assets/anclajes_mano.json");
  const configuracion = JSON.parse(await readFile(rutaConfiguracion, "utf8"));

  assert.equal(configuracion.capas.length, 17);
  await Promise.all(
    configuracion.capas.map((capa) => access(resolve("assets", capa.archivo))),
  );
});
