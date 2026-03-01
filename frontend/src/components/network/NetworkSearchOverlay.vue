<template>
  <div class="network-search-overlay rounded-lg border bg-card p-3 shadow-md">
    <!-- Search Input Field -->
    <div class="relative">
      <Search class="absolute left-2.5 top-2.5 h-4 w-4 text-muted-foreground" />
      <Input
        v-model="localSearchPattern"
        placeholder="e.g., COL*, PKD1, *A1"
        class="pl-8 h-9 pr-20"
        :class="{ 'border-destructive': errorMessage }"
        @keyup.enter="handleSearch"
        @update:model-value="handleInputChange"
      />
      <!-- Clear button inside input -->
      <button
        v-if="localSearchPattern"
        class="absolute right-2 top-2 h-5 w-5 rounded-full text-muted-foreground hover:text-foreground"
        @click="handleClear"
      >
        <X class="h-4 w-4" />
      </button>
      <!-- Match count badge appended -->
      <Badge v-if="matchCount > 0" class="absolute right-8 top-1.5 bg-green-600 text-white text-xs">
        {{ matchCount }} {{ matchCount === 1 ? 'match' : 'matches' }}
      </Badge>
    </div>

    <!-- Error message below input -->
    <p v-if="errorMessage" class="text-xs text-destructive mt-1">
      {{ errorMessage }}
    </p>

    <!-- Help text for wildcards -->
    <div v-if="showHelp" class="flex items-center text-xs text-muted-foreground mt-1 mb-2">
      <Info class="size-3 mr-1 shrink-0" />
      Use * for multiple chars, ? for single char
    </div>

    <!-- Action Buttons -->
    <div class="flex gap-2 mt-2">
      <Button
        variant="outline"
        size="sm"
        class="flex-1"
        :disabled="matchCount === 0 || loading"
        @click="$emit('highlight-all')"
      >
        <Highlighter class="h-4 w-4 mr-1" />
        Highlight All
      </Button>
      <Button
        variant="secondary"
        size="sm"
        class="flex-1"
        :disabled="matchCount === 0 || loading"
        @click="$emit('fit-view')"
      >
        <Maximize class="h-4 w-4 mr-1" />
        Fit View
      </Button>
    </div>

    <!-- Error alert display -->
    <Alert v-if="error && !errorMessage" variant="destructive" class="mt-2">
      <AlertCircle class="h-4 w-4" />
      <AlertDescription class="flex items-center justify-between">
        <span>{{ error }}</span>
        <button
          class="ml-2 text-destructive hover:text-destructive/80"
          @click="$emit('clear-error')"
        >
          <X class="h-3 w-3" />
        </button>
      </AlertDescription>
    </Alert>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Info, Search, X, Highlighter, Maximize, AlertCircle } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Alert, AlertDescription } from '@/components/ui/alert'

// Props
const props = defineProps({
  matchCount: {
    type: Number,
    default: 0
  },
  loading: {
    type: Boolean,
    default: false
  },
  error: {
    type: String,
    default: null
  },
  showHelp: {
    type: Boolean,
    default: true
  },
  initialPattern: {
    type: String,
    default: ''
  }
})

// Emits
const emit = defineEmits(['search', 'highlight-all', 'fit-view', 'clear', 'clear-error'])

// Local state
const localSearchPattern = ref(props.initialPattern)
const errorMessage = ref(null)

// Watch for error prop changes
watch(
  () => props.error,
  newError => {
    if (newError) {
      errorMessage.value = newError
    } else {
      errorMessage.value = null
    }
  }
)

// Methods
const handleSearch = () => {
  const pattern = localSearchPattern.value?.trim()
  if (pattern) {
    errorMessage.value = null
    emit('search', pattern)
  }
}

const handleClear = () => {
  localSearchPattern.value = ''
  errorMessage.value = null
  emit('clear')
}

const handleInputChange = value => {
  // Clear error when user types
  if (value !== localSearchPattern.value) {
    errorMessage.value = null
  }
}
</script>

<style scoped>
.network-search-overlay {
  position: absolute;
  top: 16px;
  right: 16px;
  z-index: 1000;
  min-width: 320px;
  max-width: 400px;
  background: hsl(var(--card) / 0.98);
  backdrop-filter: blur(8px);
}

/* Hover effect for better interactivity */
.network-search-overlay:hover {
  box-shadow: 0 6px 16px rgba(0, 0, 0, 0.2);
}

/* Ensure overlay doesn't interfere with graph interactions */
.network-search-overlay {
  pointer-events: auto;
}
</style>
