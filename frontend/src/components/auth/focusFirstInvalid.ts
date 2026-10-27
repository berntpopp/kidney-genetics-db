import { nextTick } from 'vue'

/** Move focus to the first invalid field so screen readers announce its error (issue 327) */
export function focusFirstInvalid(form: HTMLElement | null | undefined): void {
  void nextTick(() => form?.querySelector<HTMLElement>('[aria-invalid="true"]')?.focus())
}
