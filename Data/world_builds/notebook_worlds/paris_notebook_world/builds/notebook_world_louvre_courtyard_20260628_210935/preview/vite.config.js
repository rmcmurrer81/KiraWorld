import { defineConfig } from "../../../../../../../Avatar/runtime3d/node_modules/vite/dist/node/index.js";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";

const here = dirname(fileURLToPath(import.meta.url));
const projectRoot = resolve(here, "../../../../../../../");
const threeRoot = resolve(projectRoot, "Avatar/runtime3d/node_modules/three");

export default defineConfig({
  resolve: {
    alias: [
      { find: /^three$/, replacement: resolve(threeRoot, "build/three.module.js") },
      { find: /^three\/examples\/(.*)$/, replacement: `${threeRoot}/examples/$1` },
    ],
  },
  server: {
    host: "127.0.0.1",
    fs: {
      allow: [projectRoot],
    },
  },
  optimizeDeps: {
    entries: ["index.html"],
  },
});
