<script setup lang="ts">
/** Per-event email notification switches (a missing server row means on). */
import { onMounted, ref } from 'vue'
import { notificationPrefsApi, type NotificationPref } from '@/api/curationReports'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Switch } from '@/components/ui/switch'

const prefs = ref<NotificationPref[]>([])
const error = ref('')

onMounted(async () => {
  try {
    prefs.value = await notificationPrefsApi.list()
  } catch {
    error.value = 'Could not load your notification preferences.'
  }
})

async function toggle(pref: NotificationPref, enabled: boolean) {
  error.value = ''
  try {
    prefs.value = await notificationPrefsApi.update({ [pref.event]: enabled })
  } catch {
    error.value = 'Could not save your notification preferences.'
  }
}
</script>

<template>
  <Card>
    <CardHeader>
      <CardTitle tag="h2" class="text-base font-semibold">Email notifications</CardTitle>
      <CardDescription>Only sent when the server has email configured.</CardDescription>
    </CardHeader>
    <CardContent class="space-y-3">
      <div v-for="pref in prefs" :key="pref.event" class="flex items-center justify-between gap-4">
        <label :for="`pref-${pref.event}`" class="text-sm">{{ pref.label }}</label>
        <Switch
          :id="`pref-${pref.event}`"
          :model-value="pref.enabled"
          @update:model-value="(v: boolean) => toggle(pref, v)"
        />
      </div>
      <p v-if="error" role="alert" class="text-sm text-destructive">{{ error }}</p>
    </CardContent>
  </Card>
</template>
