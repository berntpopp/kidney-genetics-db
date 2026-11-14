<template>
  <!-- Without the video bundle (other deployments, dev) this address does not exist -->
  <NotFound v-if="status === 'absent'" />
  <div v-else :class="PAGE_CONTAINER">
    <PageHeader
      title="Video tutorials"
      description="Short, captioned walkthroughs of the evidence score and of each part of the database."
    >
      <template #breadcrumb>
        <Breadcrumb>
          <BreadcrumbList>
            <BreadcrumbItem v-for="(crumb, index) in breadcrumbs" :key="index">
              <BreadcrumbLink v-if="!crumb.disabled && crumb.to" as-child>
                <RouterLink :to="crumb.to">{{ crumb.title }}</RouterLink>
              </BreadcrumbLink>
              <BreadcrumbPage v-else>{{ crumb.title }}</BreadcrumbPage>
              <BreadcrumbSeparator v-if="index < breadcrumbs.length - 1" />
            </BreadcrumbItem>
          </BreadcrumbList>
        </Breadcrumb>
      </template>
    </PageHeader>

    <DataState :loading="!manifest || !current">
      <template #loading>
        <div
          class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]"
          aria-hidden="true"
          data-testid="tutorials-skeleton"
        >
          <div class="space-y-3">
            <div class="aspect-video w-full rounded-lg bg-muted motion-safe:animate-pulse" />
            <div class="h-6 w-1/3 rounded-md bg-muted motion-safe:animate-pulse" />
            <div class="h-4 w-2/3 rounded-md bg-muted motion-safe:animate-pulse" />
          </div>
          <div class="space-y-2">
            <div
              v-for="n in 6"
              :key="n"
              class="h-[4.75rem] rounded-lg bg-muted motion-safe:animate-pulse"
            />
          </div>
        </div>
      </template>

      <div v-if="manifest && current" class="grid gap-8 lg:grid-cols-[minmax(0,1fr)_22rem]">
        <!-- The id is the deep link (#<video id>); only the playing video carries it -->
        <section :id="current.id" class="min-w-0 scroll-mt-20" aria-labelledby="tutorial-title">
          <VideoPlayer :key="current.id" :manifest="manifest" :video="current" />
          <h2
            id="tutorial-title"
            ref="titleEl"
            tabindex="-1"
            class="mt-4 text-xl font-semibold tracking-tight text-balance focus:outline-none"
          >
            {{ current.title }}
          </h2>
          <p class="mt-1 max-w-[70ch] text-muted-foreground">{{ current.summary }}</p>
          <dl
            class="mt-3 flex flex-wrap items-center gap-x-4 gap-y-1 text-xs text-muted-foreground"
          >
            <div class="flex items-center gap-1">
              <dt class="sr-only">Duration</dt>
              <Clock class="size-3.5" aria-hidden="true" />
              <dd class="tabular-nums">{{ formatDuration(current.duration) }}</dd>
            </div>
            <div class="flex items-center gap-1">
              <dt class="sr-only">Captions</dt>
              <Captions class="size-3.5" aria-hidden="true" />
              <dd>{{ current.language === 'en' ? 'English' : current.language }} captions</dd>
            </div>
            <div v-if="current.note" class="flex items-center gap-1">
              <dt class="sr-only">Source of the screen captures</dt>
              <Camera class="size-3.5" aria-hidden="true" />
              <dd>{{ current.note }}</dd>
            </div>
          </dl>
          <a
            :href="videoAsset(manifest, current.video)"
            :download="current.video"
            class="mt-3 inline-flex items-center gap-1.5 text-sm font-medium text-primary underline-offset-4 hover:underline"
          >
            <Download class="size-4" aria-hidden="true" />
            Download MP4
          </a>
        </section>

        <nav aria-label="All tutorials" class="min-w-0">
          <h2 class="mb-2 text-sm font-semibold text-muted-foreground">
            {{ manifest.videos.length }} tutorials ·
            <span class="tabular-nums">{{ formatDuration(totalSeconds) }}</span>
          </h2>
          <ol class="space-y-1">
            <li v-for="video in manifest.videos" :key="video.id">
              <RouterLink
                :to="{ hash: `#${video.id}` }"
                replace
                :aria-current="video.id === current.id ? 'true' : undefined"
                class="group flex gap-3 rounded-lg p-2 transition-colors hover:bg-muted focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none aria-[current]:bg-muted"
                @click="userSelected = true"
              >
                <span class="relative w-28 shrink-0 self-start">
                  <img
                    :src="videoAsset(manifest, video.poster)"
                    alt=""
                    :width="video.width"
                    :height="video.height"
                    loading="lazy"
                    class="aspect-video w-full rounded-md border object-cover"
                  />
                  <span
                    class="absolute right-1 bottom-1 rounded-sm bg-background/90 px-1 text-[0.6875rem] font-medium text-foreground tabular-nums"
                  >
                    {{ formatDuration(video.duration) }}
                  </span>
                </span>
                <span class="min-w-0 space-y-0.5">
                  <span
                    class="block text-sm leading-snug font-medium text-foreground group-aria-[current]:font-semibold"
                  >
                    {{ video.title }}
                  </span>
                  <span class="line-clamp-2 block text-xs text-muted-foreground">
                    {{ video.summary }}
                  </span>
                  <span v-if="video.id === current.id" class="sr-only">(now showing)</span>
                </span>
              </RouterLink>
            </li>
          </ol>
          <p class="mt-4 px-2 text-xs text-muted-foreground">
            <template v-if="licenseUrl">
              Videos licensed under
              <a
                :href="licenseUrl"
                target="_blank"
                rel="noopener noreferrer license"
                class="font-medium text-primary underline-offset-4 hover:underline"
                >{{ manifest.license }}</a>.
            </template>
            <template v-else-if="manifest.license"
              >Videos licensed {{ manifest.license }}.</template
            >
            Bundle <span class="font-mono">v{{ manifest.version }}</span>
          </p>
        </nav>
      </div>
    </DataState>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, ref, watch } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import { Camera, Captions, Clock, Download } from 'lucide-vue-next'
import { DataState, PageHeader, PAGE_CONTAINER } from '@/components/shared'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import VideoPlayer from '@/components/videos/VideoPlayer.vue'
import NotFound from '@/views/NotFound.vue'
import { formatDuration, LICENSE_URLS, videoAsset } from '@/api/videos'
import { loadVideos, useVideos } from '@/composables/useVideos'
import { getBreadcrumbSchema, getVideoSchema, useJsonLd } from '@/composables/useJsonLd'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'

const breadcrumbs = PUBLIC_BREADCRUMBS.tutorials!
const route = useRoute()
const { manifest, status } = useVideos()

useSeoMeta({
  title: 'Video tutorials',
  description:
    'Short, captioned video tutorials on the kidney gene evidence score, the gene browser, gene structure, curated associations, the data overview and network analysis.',
  canonicalPath: '/tutorials'
})

// VideoObject entries come from the runtime manifest, so they are added client-side
useJsonLd(() => {
  const { '@context': context, ...crumbs } = getBreadcrumbSchema(breadcrumbs)
  const m = manifest.value
  return {
    '@context': context,
    '@graph': [crumbs, ...(m ? m.videos.map(v => getVideoSchema(m, v)) : [])]
  }
})

const current = computed(() => {
  const videos = manifest.value?.videos ?? []
  return videos.find(v => `#${v.id}` === route.hash) ?? videos[0]
})
const totalSeconds = computed(() =>
  (manifest.value?.videos ?? []).reduce((sum, v) => sum + v.duration, 0)
)
const licenseUrl = computed(() => (manifest.value ? LICENSE_URLS[manifest.value.license] : ''))

// Choosing a tutorial moves focus to its title, so screen readers announce the new video
// eslint-disable-next-line no-undef -- DOM type; the shared ESLint globals list predates it
const titleEl = ref<HTMLElement | null>(null)
const userSelected = ref(false)
watch(current, async () => {
  if (!userSelected.value) return
  userSelected.value = false
  await nextTick()
  titleEl.value?.focus({ preventScroll: true })
})

onMounted(async () => {
  await loadVideos()
  // A deep link arrived before the manifest; the router could not scroll to it yet
  if (route.hash && current.value && `#${current.value.id}` === route.hash) {
    await nextTick()
    document.getElementById(current.value.id)?.scrollIntoView({ block: 'start' })
  }
})
</script>
