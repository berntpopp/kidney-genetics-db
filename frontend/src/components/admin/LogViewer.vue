<script setup>
import { ref, computed, watch } from 'vue'
import {
  FileSearch,
  FileX,
  FileJson,
  Download,
  Trash,
  X,
  Search,
  Filter,
  Copy,
  Settings
} from 'lucide-vue-next'
import { useLogStore } from '@/stores/logStore'
import { LogLevel } from '@/services/logService'
import { Sheet, SheetContent, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Input } from '@/components/ui/input'
import {
  Accordion,
  AccordionItem,
  AccordionTrigger,
  AccordionContent
} from '@/components/ui/accordion'

const logStore = useLogStore()

const searchQuery = ref('')
const selectedLevels = ref([
  LogLevel.DEBUG,
  LogLevel.INFO,
  LogLevel.WARN,
  LogLevel.ERROR,
  LogLevel.CRITICAL
])
const maxEntries = ref(logStore.getMaxEntries())

const maxEntriesOptions = [
  { title: '20 entries', value: 20 },
  { title: '50 entries (default)', value: 50 },
  { title: '100 entries', value: 100 },
  { title: '200 entries', value: 200 },
  { title: '500 entries', value: 500 }
]

const logLevelOptions = [
  { title: 'Debug', value: LogLevel.DEBUG },
  { title: 'Info', value: LogLevel.INFO },
  { title: 'Warning', value: LogLevel.WARN },
  { title: 'Error', value: LogLevel.ERROR },
  { title: 'Critical', value: LogLevel.CRITICAL }
]

const filteredLogs = computed(() => {
  let filtered = [...logStore.logs]

  if (selectedLevels.value.length > 0 && selectedLevels.value.length < 5) {
    filtered = filtered.filter(log => selectedLevels.value.includes(log.level))
  }

  if (searchQuery.value) {
    const query = searchQuery.value.toLowerCase()
    filtered = filtered.filter(
      log =>
        log.message.toLowerCase().includes(query) ||
        log.level.toLowerCase().includes(query) ||
        (log.data && JSON.stringify(log.data).toLowerCase().includes(query))
    )
  }

  return filtered.reverse()
})

function getLogColor(level) {
  switch (level) {
    case LogLevel.DEBUG:
      return '#6b7280'
    case LogLevel.INFO:
      return '#3b82f6'
    case LogLevel.WARN:
      return '#f59e0b'
    case LogLevel.ERROR:
      return '#ef4444'
    case LogLevel.CRITICAL:
      return '#ef4444'
    default:
      return '#6b7280'
  }
}

function formatTimestamp(timestamp) {
  return new Date(timestamp).toLocaleTimeString('en-US', {
    hour12: false,
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    fractionalSecondDigits: 3
  })
}

function formatLogData(data) {
  try {
    return JSON.stringify(data, null, 2)
  } catch {
    return String(data)
  }
}

function downloadLogs() {
  try {
    const exportData = logStore.exportLogs({
      format: 'json',
      includeMetadata: true,
      filtered: false
    })
    const blob = new Blob([exportData], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    link.download = `kidney-genetics-logs-${new Date().toISOString().slice(0, 19).replace(/:/g, '-')}.json`
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
    URL.revokeObjectURL(url)
    window.logService.info('Logs exported successfully')
  } catch (error) {
    window.logService.error('Failed to download logs:', error)
  }
}

function clearLogs() {
  if (confirm('Are you sure you want to clear all logs? This action cannot be undone.')) {
    const count = logStore.clearLogs()
    window.logService.info(`Cleared ${count} log entries`)
  }
}

function copyLogEntry(log) {
  try {
    const logText = `[${log.timestamp}] ${log.level}: ${log.message}${
      log.data ? '\nData: ' + JSON.stringify(log.data, null, 2) : ''
    }`
    navigator.clipboard
      .writeText(logText)
      .then(() => {
        window.logService.debug('Log entry copied to clipboard')
      })
      .catch(error => {
        window.logService.error('Failed to copy log entry:', error)
      })
  } catch (error) {
    window.logService.error('Failed to copy log entry:', error)
  }
}

function updateMaxEntries(event) {
  const newValue = Number(event.target.value)
  try {
    logStore.setMaxEntries(newValue)
    maxEntries.value = newValue
    window.logService.info(`Log retention limit updated to ${newValue} entries`)
  } catch (error) {
    window.logService.error('Failed to update max entries:', error)
  }
}

function updateSearch(value) {
  logStore.setSearchQuery(value || '')
}

function toggleLevel(level) {
  const idx = selectedLevels.value.indexOf(level)
  if (idx >= 0) {
    selectedLevels.value.splice(idx, 1)
  } else {
    selectedLevels.value.push(level)
  }
  logStore.setLevelFilter(selectedLevels.value)
}

watch(
  () => logStore.maxEntries,
  newValue => {
    maxEntries.value = newValue
  }
)
</script>

<template>
  <Sheet
    :open="logStore.isViewerVisible"
    @update:open="val => (val ? logStore.showViewer() : logStore.hideViewer())"
  >
    <SheetContent side="right" class="w-[600px] sm:max-w-[600px] flex flex-col p-0">
      <!-- Header -->
      <SheetHeader class="bg-primary text-primary-foreground px-4 py-3">
        <div class="flex items-center justify-between">
          <SheetTitle class="text-primary-foreground flex items-center gap-2">
            <FileSearch :size="18" />
            Application Logs
            <Badge v-if="logStore.logCount > 0" variant="secondary" class="text-xs">
              {{ logStore.logCount }}
            </Badge>
          </SheetTitle>
          <div class="flex items-center gap-1">
            <Button
              variant="ghost"
              size="icon"
              class="h-8 w-8 text-primary-foreground hover:bg-primary-foreground/20"
              :disabled="logStore.logCount === 0"
              title="Download logs as JSON"
              @click="downloadLogs"
            >
              <Download :size="16" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              class="h-8 w-8 text-primary-foreground hover:bg-primary-foreground/20"
              :disabled="logStore.logCount === 0"
              title="Clear all logs"
              @click="clearLogs"
            >
              <Trash :size="16" />
            </Button>
            <Button
              variant="ghost"
              size="icon"
              class="h-8 w-8 text-primary-foreground hover:bg-primary-foreground/20"
              title="Close log viewer"
              @click="logStore.hideViewer"
            >
              <X :size="16" />
            </Button>
          </div>
        </div>
      </SheetHeader>

      <!-- Filter Controls -->
      <div class="px-4 py-3 space-y-3 border-b">
        <!-- Search -->
        <div class="relative">
          <Search
            :size="14"
            class="absolute left-3 top-1/2 -translate-y-1/2 text-muted-foreground"
          />
          <Input
            :model-value="searchQuery"
            placeholder="Search logs..."
            class="pl-9"
            @update:model-value="
              val => {
                searchQuery = val
                updateSearch(val)
              }
            "
          />
        </div>

        <!-- Level filter -->
        <div>
          <div class="flex items-center gap-1 mb-1">
            <Filter :size="12" class="text-muted-foreground" />
            <span class="text-xs text-muted-foreground">Filter by level</span>
          </div>
          <div class="flex flex-wrap gap-1">
            <Badge
              v-for="opt in logLevelOptions"
              :key="opt.value"
              :variant="selectedLevels.includes(opt.value) ? 'default' : 'outline'"
              class="cursor-pointer text-xs"
              @click="toggleLevel(opt.value)"
            >
              {{ opt.title }}
            </Badge>
          </div>
        </div>

        <!-- Max entries + stats -->
        <div class="flex items-center gap-2">
          <div class="flex items-center gap-1">
            <Settings :size="12" class="text-muted-foreground" />
            <select
              :value="maxEntries"
              class="text-xs rounded border border-input bg-background px-2 py-1"
              @change="updateMaxEntries"
            >
              <option v-for="opt in maxEntriesOptions" :key="opt.value" :value="opt.value">
                {{ opt.title }}
              </option>
            </select>
          </div>
          <Badge variant="outline" class="text-xs"> Memory: {{ logStore.memoryUsage.kb }}KB </Badge>
          <Badge variant="outline" class="text-xs">
            {{ logStore.logCount }}/{{ maxEntries }}
          </Badge>
        </div>

        <!-- Level stats -->
        <div v-if="logStore.logCount > 0" class="flex flex-wrap gap-1">
          <template v-for="(count, level) in logStore.logsByLevel" :key="level">
            <Badge
              v-if="count > 0"
              variant="outline"
              class="text-[10px]"
              :style="{ borderColor: getLogColor(level), color: getLogColor(level) }"
            >
              {{ level }}: {{ count }}
            </Badge>
          </template>
        </div>
      </div>

      <Separator />

      <!-- Log Entries -->
      <div class="flex-1 overflow-y-auto p-2 space-y-2">
        <div v-if="filteredLogs.length === 0" class="text-center py-8 text-muted-foreground">
          <FileX class="mx-auto mb-2" :size="48" />
          <p class="text-sm">
            {{ logStore.logCount === 0 ? 'No logs available' : 'No logs match your filters' }}
          </p>
        </div>

        <div
          v-for="(log, index) in filteredLogs"
          :key="`${log.timestamp}-${index}`"
          class="rounded-md border p-2 text-sm hover:shadow-sm transition-all"
          :style="{ borderLeftColor: getLogColor(log.level), borderLeftWidth: '3px' }"
        >
          <!-- Log Header -->
          <div class="flex items-center justify-between mb-1">
            <div class="flex items-center gap-2">
              <Badge
                class="text-[10px]"
                :style="{ backgroundColor: getLogColor(log.level), color: 'white' }"
              >
                {{ log.level }}
              </Badge>
              <span class="text-xs text-muted-foreground">
                {{ formatTimestamp(log.timestamp) }}
              </span>
              <Badge v-if="log.correlationId" variant="outline" class="text-[10px]">
                {{ log.correlationId.substring(0, 8) }}
              </Badge>
            </div>
            <Button
              variant="ghost"
              size="icon"
              class="h-6 w-6"
              title="Copy log entry"
              @click="copyLogEntry(log)"
            >
              <Copy :size="12" />
            </Button>
          </div>

          <!-- Log Message -->
          <div class="font-mono text-xs leading-relaxed break-words mb-1">
            {{ log.message }}
          </div>

          <!-- Log Data -->
          <Accordion v-if="log.data" type="single" collapsible>
            <AccordionItem :value="`data-${index}`" class="border-0">
              <AccordionTrigger class="py-1 text-xs hover:no-underline">
                <div class="flex items-center gap-1">
                  <FileJson :size="12" />
                  Additional Data
                </div>
              </AccordionTrigger>
              <AccordionContent>
                <pre
                  class="text-[11px] leading-tight max-h-[200px] overflow-y-auto bg-muted rounded p-2 whitespace-pre-wrap break-words"
                  >{{ formatLogData(log.data) }}</pre
                >
              </AccordionContent>
            </AccordionItem>
          </Accordion>
        </div>
      </div>
    </SheetContent>
  </Sheet>
</template>
