// Production build into a throwaway directory so frontend/dist is never touched.
import { fileURLToPath } from 'node:url'
import base from '../../../../frontend/vite.config.ts'

const root = fileURLToPath(new URL('../../../../frontend', import.meta.url))

export default {
  ...base,
  root,
  build: { ...base.build, outDir: process.env.UX_AUDIT_DIST, emptyOutDir: true }
}
