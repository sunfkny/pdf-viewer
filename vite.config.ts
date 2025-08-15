import { defineConfig } from "vite";
import legacy from "@vitejs/plugin-legacy";

export default defineConfig({
  base: "/pdf-viewer/",
  plugins: [
    legacy({
      targets: ["defaults", "not IE 11"],
    }),
  ],
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id, meta) => {
          if (id.includes("node_modules")) {
            return "vendor";
          }
          return "[name].[ext]";
        },
      },
    },
  },
});
