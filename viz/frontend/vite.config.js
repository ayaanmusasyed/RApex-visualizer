import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Output goes to viz/frontend/build so graph_component.py can find it
// with _RELEASE = True. Dev server (npm run dev) runs on 5173, matching
// the url used when _RELEASE = False.
export default defineConfig({
  plugins: [react()],
  base: "./",
  server: {
    port: 5173,
  },
  build: {
    outDir: "build",
  },
});
