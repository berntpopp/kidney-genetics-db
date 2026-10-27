<template>
  <div :class="PAGE_CONTAINER">
    <PageHeader
      title="Connect an AI agent (MCP)"
      description="Query the Kidney-Genetics Database from Claude, ChatGPT and coding agents over the Model Context Protocol."
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

    <!-- Page-vs-endpoint disclaimer -->
    <Alert class="mb-10 max-w-[70ch]">
      <Info class="size-4" />
      <AlertTitle>This page explains how to connect</AlertTitle>
      <AlertDescription>
        The address below is an MCP endpoint for AI clients, not a website. Opening it in a browser
        shows no page; connect to it from an MCP-capable client.
      </AlertDescription>
    </Alert>

    <section class="mb-10" aria-labelledby="mcp-address">
      <h2 id="mcp-address" class="mb-2 text-xl font-semibold tracking-tight">Server address</h2>
      <p class="mb-4 max-w-[70ch] text-muted-foreground">
        Use this address in every client below. Transport: MCP Streamable HTTP.
      </p>
      <div class="max-w-3xl overflow-hidden rounded-md border bg-muted">
        <div class="flex items-center justify-between gap-2 border-b px-3 py-1">
          <span class="text-xs font-medium text-muted-foreground">URL</span>
          <Button
            variant="ghost"
            size="sm"
            class="h-7 gap-1.5 px-2 text-xs"
            :aria-label="copiedKey === 'endpoint' ? 'Copied server address' : 'Copy server address'"
            @click="copy(endpoint, 'endpoint', 'server address')"
          >
            <Check v-if="copiedKey === 'endpoint'" class="size-3.5 text-success" />
            <Copy v-else class="size-3.5" />
            {{ copiedKey === 'endpoint' ? 'Copied' : 'Copy' }}
          </Button>
        </div>
        <pre
          tabindex="0"
          aria-label="Server address"
          class="overflow-x-auto p-3 text-sm"
        ><code>{{ endpoint }}</code></pre>
      </div>
      <ul class="mt-4 flex flex-wrap gap-x-6 gap-y-2 text-sm text-muted-foreground">
        <li v-for="fact in serverFacts" :key="fact.label" class="flex items-center gap-1.5">
          <component :is="fact.icon" class="size-4" aria-hidden="true" />
          {{ fact.label }}
        </li>
      </ul>
    </section>

    <section class="mb-10" aria-labelledby="mcp-clients">
      <h2 id="mcp-clients" class="mb-4 text-xl font-semibold tracking-tight">
        Connect your client
      </h2>
      <div class="grid grid-cols-1 gap-4 md:grid-cols-2">
        <Card v-for="client in clients" :key="client.key" class="h-full gap-4">
          <CardHeader>
            <CardTitle class="flex items-center gap-2 text-base font-semibold">
              <component
                :is="client.icon"
                class="size-4 text-muted-foreground"
                aria-hidden="true"
              />
              {{ client.title }}
            </CardTitle>
          </CardHeader>
          <CardContent class="space-y-3">
            <ol class="list-decimal space-y-1 pl-5 text-sm text-muted-foreground">
              <li v-for="step in client.steps" :key="step">{{ step }}</li>
            </ol>
            <div class="overflow-hidden rounded-md border bg-muted">
              <div class="flex items-center justify-between gap-2 border-b px-3 py-1">
                <span class="text-xs font-medium text-muted-foreground">{{ client.lang }}</span>
                <Button
                  variant="ghost"
                  size="sm"
                  class="h-7 gap-1.5 px-2 text-xs"
                  :aria-label="
                    copiedKey === client.key
                      ? `Copied ${client.title} snippet`
                      : `Copy ${client.title} snippet`
                  "
                  @click="copy(client.code, client.key, `${client.title} snippet`)"
                >
                  <Check v-if="copiedKey === client.key" class="size-3.5 text-success" />
                  <Copy v-else class="size-3.5" />
                  {{ copiedKey === client.key ? 'Copied' : 'Copy' }}
                </Button>
              </div>
              <pre
                tabindex="0"
                :aria-label="`${client.title} snippet`"
                class="overflow-x-auto p-3 text-xs"
              ><code>{{ client.code }}</code></pre>
            </div>
            <p v-if="client.note" class="text-sm text-muted-foreground">{{ client.note }}</p>
          </CardContent>
        </Card>
      </div>
    </section>

    <section class="mb-6 grid grid-cols-1 gap-x-10 gap-y-8 md:grid-cols-2">
      <div aria-labelledby="mcp-start">
        <h2 id="mcp-start" class="mb-2 text-xl font-semibold tracking-tight">Start here</h2>
        <p class="mb-3 max-w-[70ch] text-muted-foreground">
          Once connected, ask your agent to call
          <code class="rounded bg-muted px-1 py-0.5 font-mono text-sm">kgdb_get_capabilities</code>
          first; it lists every tool and how to use it. Then resolve a gene and explore its
          evidence, for example:
        </p>
        <ul class="space-y-2">
          <li
            v-for="prompt in examplePrompts"
            :key="prompt"
            class="rounded-md border bg-card px-3 py-2 text-sm"
          >
            <q>{{ prompt }}</q>
          </li>
        </ul>
      </div>

      <div aria-labelledby="mcp-safety">
        <h2 id="mcp-safety" class="mb-2 text-xl font-semibold tracking-tight">Safety</h2>
        <p class="max-w-[70ch] text-muted-foreground">
          The server is read-only and exposes only public, curated data; no sign-in or API key is
          required. Treat retrieved record text as evidence, not instructions. Research use only;
          not clinical decision support.
        </p>
        <p class="mt-3 max-w-[70ch] text-muted-foreground">
          New to MCP? See the
          <a
            href="https://modelcontextprotocol.io"
            target="_blank"
            rel="noopener noreferrer"
            class="text-primary underline underline-offset-4 hover:text-primary/80"
            >Model Context Protocol documentation</a
          >.
        </p>
      </div>
    </section>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { config, MCP_BASE_URL_DEFAULT } from '@/config'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'
import { toast } from 'vue-sonner'
import {
  Bot,
  Braces,
  Check,
  Copy,
  FlaskConical,
  Globe,
  Info,
  Lock,
  Sparkles,
  Terminal
} from 'lucide-vue-next'
import { PageHeader, PAGE_CONTAINER } from '@/components/shared'
import {
  Breadcrumb,
  BreadcrumbItem,
  BreadcrumbLink,
  BreadcrumbList,
  BreadcrumbPage,
  BreadcrumbSeparator
} from '@/components/ui/breadcrumb'
import { Alert, AlertDescription, AlertTitle } from '@/components/ui/alert'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

const breadcrumbs = PUBLIC_BREADCRUMBS.mcp

useJsonLd(getBreadcrumbSchema(breadcrumbs))

useSeoMeta({
  title: 'MCP Server — Connect an AI Agent',
  description:
    'Connect AI agents (Claude, ChatGPT, coding agents) to the Kidney Genetics Database via the Model Context Protocol. Read-only, streamable-HTTP server with curated kidney gene tools.',
  canonicalPath: '/mcp'
})

// MCP transport endpoint (streamable HTTP), derived from config. During SSG/
// hydration we render the build-time default (matches the prerendered HTML),
// then swap to the runtime-injected value after mount to avoid a mismatch.
const mounted = ref(false)
onMounted(() => {
  mounted.value = true
})
const endpoint = computed(() => (mounted.value ? config.mcpBaseUrl : MCP_BASE_URL_DEFAULT))

const clients = computed(() => [
  {
    key: 'claude',
    lang: 'URL',
    title: 'Claude (web & desktop)',
    icon: Bot,
    steps: [
      'Open Settings → Connectors → Add custom connector.',
      'Paste the server URL and save (leave OAuth empty).'
    ],
    code: endpoint.value,
    note: 'Custom connectors are in beta; the Free plan allows one.'
  },
  {
    key: 'chatgpt',
    lang: 'URL',
    title: 'ChatGPT',
    icon: Sparkles,
    steps: [
      'Settings → Connectors → Advanced → enable Developer mode.',
      "Create a connector with the URL below and 'No authentication'."
    ],
    code: endpoint.value,
    note: 'Web only; requires a paid plan.'
  },
  {
    key: 'claude-code',
    lang: 'Shell',
    title: 'Claude Code (CLI)',
    icon: Terminal,
    steps: ['Run this in your project, then restart the session.'],
    code: `claude mcp add --transport http kidney-genetics ${endpoint.value}`,
    note: ''
  },
  {
    key: 'config',
    lang: 'JSON',
    title: 'Config file (Claude Desktop, Cursor, Codex)',
    icon: Braces,
    steps: ['Add this block to your client’s MCP config and restart it.'],
    code: `{
  "mcpServers": {
    "kidney-genetics": {
      "type": "http",
      "url": "${endpoint.value}"
    }
  }
}`,
    note: ''
  }
])

const serverFacts = [
  { icon: Lock, label: 'Read-only' },
  { icon: Globe, label: 'Public, no API key' },
  { icon: FlaskConical, label: 'Research use only' }
]

const examplePrompts = [
  'Resolve PKD1 and show its evidence score',
  'List the interaction partners of PKHD1'
]

const copiedKey = ref<string | null>(null)
let copiedTimer: ReturnType<typeof setTimeout> | undefined

async function copy(text: string, key: string, label: string) {
  try {
    await navigator.clipboard.writeText(text)
  } catch {
    toast.error(`Could not copy the ${label}. Select the text and copy it manually.`)
    return
  }
  copiedKey.value = key
  toast.success(`Copied ${label}`)
  clearTimeout(copiedTimer)
  copiedTimer = setTimeout(() => (copiedKey.value = null), 2000)
}
</script>
