import { build } from "esbuild";
import { mkdir, copyFile } from "node:fs/promises";

await mkdir("dist/server", { recursive: true });
await mkdir("dist/.openai", { recursive: true });
await build({
  entryPoints: ["worker/index.js"],
  outfile: "dist/server/index.js",
  bundle: true,
  platform: "browser",
  format: "esm",
  target: "es2022",
  loader: { ".html": "text", ".css": "text", ".txt": "text" },
  legalComments: "none",
});
await copyFile(".openai/hosting.json", "dist/.openai/hosting.json");
console.log("Built Sites Worker ESM artifact");
