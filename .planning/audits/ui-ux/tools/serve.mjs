// Static server that mirrors nginx.prod.conf: try_files fallback, gzip_static, on-the-fly gzip, /api proxy.
// Keep it in sync with nginx.prod.conf, otherwise the audit stops measuring what production serves.
// usage: node serve.mjs <distDir> <port>   (API_URL defaults to http://127.0.0.1:8000)
import { Buffer } from 'node:buffer'
import fs from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import zlib from 'node:zlib'

const [root, port] = [process.argv[2], Number(process.argv[3])]
const api = process.env.API_URL || 'http://127.0.0.1:8000'
const types = {
  '.html': 'text/html; charset=utf-8',
  '.js': 'application/javascript',
  '.css': 'text/css',
  '.svg': 'image/svg+xml',
  '.png': 'image/png',
  '.ico': 'image/x-icon',
  '.json': 'application/json',
  '.webmanifest': 'application/manifest+json',
  '.txt': 'text/plain',
  '.woff2': 'font/woff2',
  '.xml': 'application/xml'
}
const isFile = p => {
  try {
    return fs.statSync(p).isFile()
  } catch {
    return false
  }
}
const wantsGzip = req => /gzip/.test(req.headers['accept-encoding'] || '')

http
  .createServer(async (req, res) => {
    const url = new URL(req.url, 'http://x')
    if (url.pathname.startsWith('/api/') || url.pathname === '/sitemap.xml') {
      const chunks = []
      for await (const c of req) chunks.push(c)
      const r = await fetch(api + req.url, {
        method: req.method,
        headers: { ...req.headers, host: new URL(api).host, 'accept-encoding': 'identity' },
        body: chunks.length ? Buffer.concat(chunks) : undefined
      }).catch(() => null)
      if (!r) return res.writeHead(502).end()
      const body = Buffer.from(await r.arrayBuffer())
      const h = { 'content-type': r.headers.get('content-type') || 'application/json' }
      if (wantsGzip(req) && body.length > 1000) {
        res.writeHead(r.status, { ...h, 'content-encoding': 'gzip' })
        return res.end(zlib.gzipSync(body))
      }
      return res.writeHead(r.status, h).end(body)
    }
    const p = path.join(root, decodeURIComponent(url.pathname))
    const file = [p, path.join(p, 'index.html'), p + '.html', path.join(root, 'index.html')].find(
      isFile
    )
    const h = {
      'content-type': types[path.extname(file)] || 'application/octet-stream',
      'cache-control': url.pathname.startsWith('/assets/')
        ? 'public, max-age=31536000, immutable'
        : 'public, max-age=3600, must-revalidate',
      vary: 'Accept-Encoding'
    }
    if (wantsGzip(req) && isFile(file + '.gz')) {
      res.writeHead(200, { ...h, 'content-encoding': 'gzip' })
      return fs.createReadStream(file + '.gz').pipe(res)
    }
    const buf = fs.readFileSync(file)
    if (
      wantsGzip(req) &&
      /text|javascript|json|xml|svg/.test(h['content-type']) &&
      buf.length > 1000
    ) {
      res.writeHead(200, { ...h, 'content-encoding': 'gzip' })
      return res.end(zlib.gzipSync(buf))
    }
    res.writeHead(200, h).end(buf)
  })
  .listen(port, '127.0.0.1', () => console.log(`serving ${root} on :${port}`))
