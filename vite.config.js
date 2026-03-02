import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

function normalizeBasePath(value) {
  const raw = value && String(value).trim() ? String(value).trim() : "/";
  const withLeading = raw.startsWith("/") ? raw : `/${raw}`;
  return withLeading.endsWith("/") ? withLeading : `${withLeading}/`;
}

export default defineConfig({
  plugins: [vue()],
  base: normalizeBasePath(process.env.VITE_BASE_PATH),
});
