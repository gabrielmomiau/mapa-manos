import { defineConfig } from "vite";

export default defineConfig({
  base: "./",
  build: {
    rollupOptions: {
      input: {
        principal: "index.html",
        archivo: "archivo.html",
      },
    },
  },
});
