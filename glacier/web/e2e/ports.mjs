import net from 'node:net'

async function freePort() {
  const server = net.createServer()
  await new Promise((resolve, reject) => {
    server.once('error', reject)
    server.listen(0, '127.0.0.1', resolve)
  })
  const { port } = server.address()
  await new Promise((resolve, reject) => server.close(error => error ? reject(error) : resolve()))
  return port
}

// Each spec gets its own mock and preview ports. Explicit values remain useful
// for debugging; normal runs reserve ephemeral ports instead of sharing defaults.
export async function e2ePorts() {
  const mockPort = Number(process.env.MOCK_PORT) || await freePort()
  const uiPort = Number(process.env.UI_PORT) || await freePort()
  const api = process.env.GLACIER_API || process.env.API_URL || `http://localhost:${mockPort}`
  return { mockPort, uiPort, api, ui: `http://localhost:${uiPort}` }
}
