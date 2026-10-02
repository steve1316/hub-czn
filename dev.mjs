// Runs the app from source with one command: the Python sidecar, then `tauri dev`. Started by `npm start`.
//
// A dev build of the Tauri shell does not spawn the sidecar, so without this it needs a second terminal. The sidecar gets this
// process's PID and watches it, so it undoes any capture and exits on its own once the app closes, the same as in a release build.

import { spawn, spawnSync } from "node:child_process"
import net from "node:net"
import path from "node:path"
import { fileURLToPath } from "node:url"

const ROOT = path.dirname(fileURLToPath(import.meta.url))

// The dev frontend is hard-wired to this port and token in .env.development.
const PORT = 7842
const TOKEN = "dev"

/**
 * Checks whether this terminal runs as Administrator. The app's manifest requires it, so `tauri dev` cannot launch it otherwise.
 * @returns True when elevated. `net session` only succeeds for an elevated process.
 */
function isElevated() {
  return spawnSync("net", ["session"], { stdio: "ignore" }).status === 0
}

/**
 * Checks whether something is already listening on the sidecar's port.
 * @param port - The port to try.
 * @returns True if the port can be bound.
 */
function portIsFree(port) {
  return new Promise(resolve => {
    const server = net.createServer()
    server.once("error", () => resolve(false))
    server.once("listening", () => server.close(() => resolve(true)))
    server.listen(port, "127.0.0.1")
  })
}

/**
 * Starts the sidecar and waits until it reports its port.
 * @returns The running child process.
 */
function startSidecar() {
  const env = { ...process.env, HUB_CZN_API_TOKEN: TOKEN, HUB_CZN_PORT: String(PORT), HUB_CZN_PARENT_PID: String(process.pid) }
  // Detached puts it in its own process group, so Ctrl+C reaches only the app. It then exits through its parent watcher,
  // which runs the capture cleanup, instead of being interrupted mid-way.
  const child = spawn("python", ["-u", "-m", "api.main"], { cwd: ROOT, env, detached: true, windowsHide: true, stdio: ["ignore", "pipe", "pipe"] })
  const relay = stream => stream.on("data", chunk => process.stdout.write(String(chunk).replace(/^(?=.)/gm, "[api] ")))
  relay(child.stdout)
  relay(child.stderr)

  return new Promise((resolve, reject) => {
    const onData = chunk => {
      if (String(chunk).includes("PORT:")) {
        child.stdout.off("data", onData)
        resolve(child)
      }
    }
    child.stdout.on("data", onData)
    child.once("error", reject)
    child.once("exit", code => reject(new Error(`sidecar exited with code ${code} before it was ready`)))
  })
}

if (!isElevated()) {
  console.error("Run this from an Administrator terminal. The app requires elevation, so Windows refuses to launch it otherwise.")
  process.exit(1)
}

if (!(await portIsFree(PORT))) {
  console.error(`Port ${PORT} is in use. Close the installed Hub CZN or any other sidecar first, since the dev frontend only talks to ${PORT}.`)
  process.exit(1)
}

try {
  await startSidecar()
} catch (err) {
  console.error(`Could not start the sidecar: ${err.message}`)
  process.exit(1)
}

// Ctrl+C goes to the app, and this process exits when the app does.
process.on("SIGINT", () => {})
const app = spawn("npm", ["run", "tauri", "dev"], { cwd: ROOT, stdio: "inherit", shell: true })
app.on("exit", code => process.exit(code ?? 0))
