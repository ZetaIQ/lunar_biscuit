import { defineConfig } from "vite";
import { resolve } from "node:path";

export default defineConfig({
  build: {
    lib: {
      entry: resolve(__dirname, "web/visualizer/main.js"),
      name: "Visualizer",
      formats: ["es"],
      fileName: () => "visualizer.js"
    },
    outDir: "radiant_chacha/visualization/static/dist",
    emptyOutDir: true,
    rollupOptions: {
      output: {
        assetFileNames: "assets/[name][extname]"
      }
    }
  }
});
