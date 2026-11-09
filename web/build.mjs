// Bundles the figure into one script and one stylesheet that Flask (and the Vercel
// static build) serve from ../static. Commit the output: runtime hosts have no Node.
import { build } from "esbuild";

await build({
  entryPoints: { pipeline: "src/main.tsx" },
  outdir: "../static",
  bundle: true,
  minify: true,
  format: "iife",
  target: "es2020",
  jsx: "automatic",
  define: { "process.env.NODE_ENV": '"production"' },
  logLevel: "info",
});
