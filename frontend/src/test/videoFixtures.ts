// Video bundle manifest fixtures (shape of /videos/videos.json)
export const video = (id: string, extra: Record<string, unknown> = {}) => ({
  id,
  title: `Title ${id}`,
  summary: `Summary ${id}`,
  pages: ['/genes/:symbol', '/about'],
  duration: 199.8,
  video: `${id}.mp4`,
  captions: `${id}.vtt`,
  poster: `${id}.jpg`,
  width: 1920,
  height: 1080,
  language: 'en',
  captured: '2026-11-03',
  ...extra
})

export const manifestJson = (videos: unknown[] = [video('01-evidence-score')]) => ({
  schema: 1,
  version: '1.0.0',
  license: 'CC BY 4.0',
  videos
})
