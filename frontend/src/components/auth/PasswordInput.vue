<script setup lang="ts">
/**
 * Password input with a show/hide toggle. Attributes (id, name, aria-*, autocomplete) go to
 * the <input>, so it works inside FormControl.
 */
import { ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'

defineOptions({ inheritAttrs: false })
defineProps<{ disabled?: boolean }>()
const model = defineModel<string>()
const visible = ref(false)
</script>

<template>
  <div class="relative">
    <Input
      v-bind="$attrs"
      v-model="model"
      :type="visible ? 'text' : 'password'"
      :disabled="disabled"
      class="pr-10"
    />
    <Tooltip>
      <TooltipTrigger as-child>
        <Button
          type="button"
          variant="ghost"
          size="icon"
          :aria-label="visible ? 'Hide password' : 'Show password'"
          :aria-pressed="visible"
          class="absolute right-0 top-0 h-full px-3 text-muted-foreground hover:bg-transparent hover:text-foreground"
          :disabled="disabled"
          @click="visible = !visible"
        >
          <EyeOff v-if="visible" class="size-4" />
          <Eye v-else class="size-4" />
        </Button>
      </TooltipTrigger>
      <TooltipContent>{{ visible ? 'Hide password' : 'Show password' }}</TooltipContent>
    </Tooltip>
  </div>
</template>
