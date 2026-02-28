<template>
  <TooltipProvider v-if="tier">
    <Tooltip>
      <TooltipTrigger as-child>
        <Badge
          :class="[sizeClasses, 'cursor-help font-medium']"
          :style="{
            backgroundColor: tierConfig.color + '20',
            color: tierConfig.color,
            borderColor: tierConfig.color + '40'
          }"
          variant="outline"
        >
          <component :is="tierConfig.icon" :size="iconSize" class="mr-1" />
          {{ tierConfig.label }}
        </Badge>
      </TooltipTrigger>
      <TooltipContent>
        <p class="font-medium">{{ tierConfig.label }}</p>
        <p class="text-xs text-muted-foreground">{{ tierConfig.description }}</p>
      </TooltipContent>
    </Tooltip>
  </TooltipProvider>
</template>

<script setup>
import { computed } from 'vue'
import { Tooltip, TooltipContent, TooltipProvider, TooltipTrigger } from '@/components/ui/tooltip'
import { Badge } from '@/components/ui/badge'
import { getTierConfig } from '@/utils/evidenceTiers'

const props = defineProps({
  tier: {
    type: String,
    default: null
  },
  size: {
    type: String,
    default: 'small',
    validator: value => ['x-small', 'small', 'default'].includes(value)
  }
})

const tierConfig = computed(() => getTierConfig(props.tier))

const sizeClasses = computed(() => {
  switch (props.size) {
    case 'x-small':
      return 'text-[10px] px-1.5 py-0'
    case 'small':
      return 'text-xs px-2 py-0.5'
    default:
      return 'text-sm px-2.5 py-1'
  }
})

const iconSize = computed(() => (props.size === 'x-small' ? 10 : props.size === 'small' ? 12 : 14))
</script>
