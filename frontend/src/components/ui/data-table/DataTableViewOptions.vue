<script setup lang="ts">
import type { Table } from '@tanstack/vue-table'
import { Settings2 } from 'lucide-vue-next'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger
} from '@/components/ui/dropdown-menu'

interface Props {
  table: Table<any>
}

defineProps<Props>()
</script>

<template>
  <DropdownMenu>
    <DropdownMenuTrigger as-child>
      <Button variant="outline" size="sm" class="ml-auto hidden h-8 lg:flex">
        <Settings2 class="mr-2 h-4 w-4" />
        View
      </Button>
    </DropdownMenuTrigger>
    <DropdownMenuContent align="end" class="w-[150px]">
      <DropdownMenuLabel>Toggle columns</DropdownMenuLabel>
      <DropdownMenuSeparator />
      <DropdownMenuCheckboxItem
        v-for="column in table.getAllColumns().filter(c => c.getCanHide())"
        :key="column.id"
        :checked="column.getIsVisible()"
        @update:checked="val => column.toggleVisibility(!!val)"
      >
        {{ column.id }}
      </DropdownMenuCheckboxItem>
    </DropdownMenuContent>
  </DropdownMenu>
</template>
