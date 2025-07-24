import { defineConfig } from "vite";
export default defineConfig({
  build: {
    rollupOptions: {
      output: {
        manualChunks: (id, meta) => {
          if (id.includes("node_modules")) {
            return "vendor";
          }
          return '[name].[ext]';
        },
      },
    },
  },
});
