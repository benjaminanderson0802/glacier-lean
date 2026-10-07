import { execFileSync } from "node:child_process";
import { cpSync, mkdirSync, rmSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const desktopDir = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const webDir = resolve(desktopDir, "../glacier/web");
const distDir = join(desktopDir, "dist");

execFileSync(process.platform === "win32" ? "npm.cmd" : "npm", ["run", "build"], {
  cwd: webDir,
  stdio: "inherit",
  ...(process.platform === "win32" ? { shell: true } : {}),
});

rmSync(distDir, { recursive: true, force: true });
mkdirSync(distDir, { recursive: true });
cpSync(join(webDir, "dist"), distDir, { recursive: true });
cpSync(join(desktopDir, "first-run"), join(distDir, "first-run"), { recursive: true });
