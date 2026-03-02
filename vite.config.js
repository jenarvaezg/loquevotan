import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

function normalizeBasePath(value) {
  const raw = value && String(value).trim() ? String(value).trim() : "/";
  const withLeading = raw.startsWith("/") ? raw : `/${raw}`;
  return withLeading.endsWith("/") ? withLeading : `${withLeading}/`;
}

// NOTE: Si la app se publica en GitHub Pages como proyecto (https://<user>.github.io/loquevotan/),
// compila con: `VITE_BASE_PATH=/loquevotan/ npm run build`
// para evitar 404 de assets por rutas absolutas `/assets/...`.
export default defineConfig({
  plugins: [vue()],
  base: normalizeBasePath(process.env.VITE_BASE_PATH),
});
