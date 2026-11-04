import { bindings, defineConfig } from "cf/config";

export default defineConfig({
  worker: {
    name: "__WORKER_NAME__",
    compatibilityDate: "2026-09-28",
    compatibilityFlags: ["nodejs_compat"],
    entrypoint: "src/index.ts",
    env: {
      // cf dev talks to the real Browser Run.
      BROWSER: bindings.browser({ dev: { remote: true } }),
      // Bearer token required on every request; deploy.sh uploads it with `cf deploy --secrets-file`.
      API_TOKEN: bindings.secret(),
    },
  },
});
