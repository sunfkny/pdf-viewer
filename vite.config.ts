import { defineConfig } from "vite";
export default defineConfig({
  base: "/pdf-viewer/",
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
