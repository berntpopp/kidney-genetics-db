<template>
  <v-card class="network-search-overlay" elevation="3" rounded="lg">
    <v-card-text class="pa-3">
      <!-- Search Input Field -->
      <v-text-field
        v-model="localSearchPattern"
        label="Search genes"
        placeholder="e.g., COL*, PKD1, *A1"
        prepend-inner-icon="mdi-magnify"
        density="compact"
        variant="outlined"
        hide-details="auto"
        clearable
        :error-messages="errorMessage"
        @keyup.enter="handleSearch"
        @click:clear="handleClear"
        @update:model-value="handleInputChange"
      >
        <!-- Match count chip in append slot -->
        <template v-if="matchCount > 0" #append>
          <v-chip size="x-small" color="success" label>
            {{ matchCount }} {{ matchCount === 1 ? 'match' : 'matches' }}
          </v-chip>
        </template>
      </v-text-field>

      <!-- Help text for wildcards -->
      <div v-if="showHelp" class="text-caption text-medium-emphasis mt-1 mb-2">
        <Info class="size-3 mr-1" />
        Use * for multiple chars, ? for single char
      </div>

      <!-- Action Buttons -->
      <div class="d-flex ga-2 mt-2">
        <v-btn
          color="warning"
          size="small"
          prepend-icon="mdi-checkbox-multiple-marked"
          :disabled="matchCount === 0"
          :loading="loading"
          block
          @click="$emit('highlight-all')"
        >
          Highlight All
        </v-btn>
        <v-btn
          color="secondary"
          size="small"
          prepend-icon="mdi-fit-to-screen"
          :disabled="matchCount === 0"
          :loading="loading"
          block
          @click="$emit('fit-view')"
        >
          Fit View
        </v-btn>
      </div>

      <!-- Error message display -->
      <v-alert
        v-if="error && !errorMessage"
        type="error"
        variant="tonal"
        density="compact"
        class="mt-2"
        closable
        @click:close="$emit('clear-error')"
      >
        {{ error }}
      </v-alert>
    </v-card-text>
  </v-card>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Info } from 'lucide-vue-next'

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
  background: rgba(255, 255, 255, 0.98);
  backdrop-filter: blur(8px);
}

/* Dark theme support */
.v-theme--dark .network-search-overlay {
  background: rgba(33, 33, 33, 0.98);
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
