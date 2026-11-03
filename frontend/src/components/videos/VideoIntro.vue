<script setup lang="ts">
/**
 * "n-min intro" chips for the videos whose `pages` match the current route; each opens the
 * player in place. Renders nothing without the bundle or without a matching video.
 */
import { computed, inject, ref } from 'vue'
import { RouterLink, routeLocationKey } from 'vue-router'
import { CirclePlay } from 'lucide-vue-next'
import { Chip } from '@/components/shared'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogHeader,
  DialogTitle
} from '@/components/ui/dialog'
import VideoPlayer from './VideoPlayer.vue'
import { durationMinutes, videoMatchesRoute, type Video } from '@/api/videos'
import { useVideos } from '@/composables/useVideos'

// Optional injection: PageHeader also renders in tests and views mounted without a router
const route = inject(routeLocationKey, null)
const { manifest } = useVideos()

const videos = computed(() => {
  if (!manifest.value || !route) return []
  const pattern = route.matched[route.matched.length - 1]?.path
  return manifest.value.videos.filter(v => videoMatchesRoute(v, route.path, pattern))
})

const open = ref<Video | null>(null)
</script>

<template>
  <div v-if="manifest && videos.length" class="flex shrink-0 items-center gap-2">
    <Chip
      v-for="video in videos"
      :key="video.id"
      kind="neutral"
      :icon="CirclePlay"
      :label="`${durationMinutes(video.duration)}-min intro`"
      :tooltip="`Watch: ${video.title}`"
      :aria-label="`Watch the ${durationMinutes(video.duration)}-minute intro: ${video.title}`"
      aria-haspopup="dialog"
      class="h-6"
      @click="open = video"
    />

    <Dialog :open="!!open" @update:open="value => !value && (open = null)">
      <DialogContent v-if="open" class="gap-4 sm:max-w-3xl">
        <DialogHeader>
          <DialogTitle>{{ open.title }}</DialogTitle>
          <DialogDescription>{{ open.summary }}</DialogDescription>
        </DialogHeader>
        <VideoPlayer :key="open.id" :manifest="manifest" :video="open" />
        <p class="text-xs text-muted-foreground">
          <RouterLink
            :to="{ path: '/tutorials', hash: `#${open.id}` }"
            class="font-medium text-primary underline-offset-4 hover:underline"
            @click="open = null"
          >
            All tutorials
          </RouterLink>
          <template v-if="manifest.license"> · Licensed {{ manifest.license }}</template>
        </p>
      </DialogContent>
    </Dialog>
  </div>
</template>
