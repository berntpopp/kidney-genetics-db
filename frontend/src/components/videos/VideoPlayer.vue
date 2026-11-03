<script setup lang="ts">
/**
 * Native player for one bundle video: no autoplay, nothing loads before Play, captions on.
 * Key it by video id so switching videos resets the element.
 */
import { videoAsset, type Video, type VideoManifest } from '@/api/videos'

defineProps<{ manifest: VideoManifest; video: Video }>()
</script>

<template>
  <video
    controls
    playsinline
    preload="none"
    :poster="videoAsset(manifest, video.poster)"
    :width="video.width"
    :height="video.height"
    :aria-label="`Video: ${video.title}`"
    class="aspect-video h-auto w-full rounded-lg border bg-muted"
  >
    <source :src="videoAsset(manifest, video.video)" type="video/mp4" />
    <track
      kind="captions"
      :srclang="video.language"
      :label="video.language === 'en' ? 'English' : video.language"
      :src="videoAsset(manifest, video.captions)"
      default
    />
    <p class="p-4 text-sm">
      Your browser cannot play this video.
      <a :href="videoAsset(manifest, video.video)" class="underline">Download the MP4</a>.
    </p>
  </video>
</template>
