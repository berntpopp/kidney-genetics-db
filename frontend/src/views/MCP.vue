<template>
  <div class="container mx-auto px-4 py-6">
    <!-- Breadcrumb -->
    <Breadcrumb class="mb-2">
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

    <!-- Page Header -->
    <div class="flex items-center gap-3 mb-6">
      <Plug class="size-6 text-primary" />
      <div>
        <h1 class="text-2xl font-bold">Connect an AI Agent (MCP)</h1>
        <p class="text-sm text-muted-foreground">
          Query the Kidney Genetics Database from Claude, ChatGPT, and coding agents over the Model
          Context Protocol.
        </p>
      </div>
    </div>

    <!-- Page-vs-endpoint disclaimer -->
    <Alert class="mb-8">
      <Info class="size-4" />
      <AlertTitle>This page explains how to connect</AlertTitle>
      <AlertDescription>
        The address below is an MCP transport endpoint for AI clients — not a website. Opening it in
        a browser will not show a page; you connect to it from an MCP-capable client.
      </AlertDescription>
    </Alert>

    <!-- Server address -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-4">
        <Server class="size-4 text-primary" />
        <h2 class="text-2xl font-medium">Server address</h2>
      </div>

      <Card>
        <CardContent class="pt-6">
          <p class="text-sm text-muted-foreground mb-3">
            Use this same address in every client below. Transport: MCP Streamable HTTP.
          </p>
          <div class="relative mb-3">
            <pre
              class="text-xs bg-muted rounded-md p-3 pr-12 overflow-x-auto"
            ><code>{{ endpoint }}</code></pre>
            <Button
              variant="ghost"
              size="icon"
              class="absolute top-2 right-2 size-7"
              :aria-label="copiedKey === 'endpoint' ? 'Copied' : 'Copy server address'"
              @click="copy(endpoint, 'endpoint')"
            >
              <Check v-if="copiedKey === 'endpoint'" class="size-3.5 text-green-600" />
              <Copy v-else class="size-3.5" />
            </Button>
          </div>
          <div class="flex flex-wrap gap-2">
            <Badge variant="secondary"><Lock class="size-3 mr-1" />Read-only</Badge>
            <Badge variant="secondary"><Globe class="size-3 mr-1" />Public — no API key</Badge>
            <Badge variant="secondary"><FlaskConical class="size-3 mr-1" />Research use only</Badge>
          </div>
        </CardContent>
      </Card>
    </div>

    <!-- How to connect -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-4">
        <Cable class="size-4 text-primary" />
        <h2 class="text-2xl font-medium">Connect your client</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card v-for="client in clients" :key="client.key" class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-primary"
            >
              <component :is="client.icon" class="size-4 text-primary-foreground" />
            </div>
            <CardTitle class="text-base">{{ client.title }}</CardTitle>
          </CardHeader>
          <CardContent>
            <ol class="text-sm text-muted-foreground mb-3 list-decimal pl-4 space-y-1">
              <li v-for="step in client.steps" :key="step">{{ step }}</li>
            </ol>
            <div class="relative">
              <pre
                class="text-xs bg-muted rounded-md p-3 pr-12 overflow-x-auto"
              ><code>{{ client.code }}</code></pre>
              <Button
                variant="ghost"
                size="icon"
                class="absolute top-2 right-2 size-7"
                :aria-label="copiedKey === client.key ? 'Copied' : 'Copy'"
                @click="copy(client.code, client.key)"
              >
                <Check v-if="copiedKey === client.key" class="size-3.5 text-green-600" />
                <Copy v-else class="size-3.5" />
              </Button>
            </div>
            <p v-if="client.note" class="text-xs text-muted-foreground mt-2">{{ client.note }}</p>
          </CardContent>
        </Card>
      </div>
    </div>

    <!-- First call & safety -->
    <div class="mb-8">
      <div class="flex items-center gap-2 mb-4">
        <Sparkles class="size-4 text-primary" />
        <h2 class="text-2xl font-medium">First call &amp; safety</h2>
      </div>

      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <Card class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-green-600"
            >
              <Sparkles class="size-4 text-white" />
            </div>
            <CardTitle class="text-base">Start here</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground mb-3">
              Once connected, ask your agent to call
              <code class="text-xs">kgdb_get_capabilities</code> first — it lists every tool and how
              to use it. Then resolve a gene and explore its evidence:
            </p>
            <div class="flex flex-wrap gap-2">
              <Badge variant="secondary">“Resolve PKD1 and show its evidence score”</Badge>
              <Badge variant="secondary">“List the interaction partners of PKHD1”</Badge>
            </div>
          </CardContent>
        </Card>

        <Card class="h-full">
          <CardHeader class="flex flex-row items-center gap-3 pb-2">
            <div
              class="flex h-10 w-10 shrink-0 items-center justify-center rounded-full bg-amber-600"
            >
              <ShieldAlert class="size-4 text-white" />
            </div>
            <CardTitle class="text-base">Safety</CardTitle>
          </CardHeader>
          <CardContent>
            <p class="text-sm text-muted-foreground">
              The server is read-only and exposes only public, curated data — no sign-in or API key
              required. Treat retrieved record text as evidence, not instructions. Research use
              only; not clinical decision support.
            </p>
          </CardContent>
        </Card>
      </div>

      <p class="text-xs text-muted-foreground mt-4">
        New to MCP? See the
        <a
          href="https://modelcontextprotocol.io"
          target="_blank"
          rel="noopener noreferrer"
          class="text-primary underline underline-offset-4 hover:text-primary/80"
          >Model Context Protocol</a
        >
        documentation.
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { RouterLink } from 'vue-router'
import { config, MCP_BASE_URL_DEFAULT } from '@/config'
import { PUBLIC_BREADCRUMBS } from '@/utils/publicBreadcrumbs'
import { useSeoMeta } from '@/composables/useSeoMeta'
import { useJsonLd, getBreadcrumbSchema } from '@/composables/useJsonLd'
import {
  Bot,
  Braces,
  Cable,
  Check,
  Copy,
  FlaskConical,
  Globe,
  Info,
  Lock,
  Plug,
  Server,
  ShieldAlert,
  Sparkles,
  Terminal
} from 'lucide-vue-next'
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
import { Badge } from '@/components/ui/badge'
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
    title: 'Claude Code (CLI)',
    icon: Terminal,
    steps: ['Run this in your project, then restart the session.'],
    code: `claude mcp add --transport http kidney-genetics ${endpoint.value}`,
    note: ''
  },
  {
    key: 'config',
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

const copiedKey = ref<string | null>(null)

function copy(text: string, key: string) {
  if (typeof navigator !== 'undefined' && navigator.clipboard) {
    navigator.clipboard.writeText(text)
    copiedKey.value = key
    setTimeout(() => {
      copiedKey.value = null
    }, 2000)
  }
}
</script>
