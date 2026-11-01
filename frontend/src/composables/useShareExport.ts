import { ref } from 'vue'
import { toast } from 'vue-sonner'
import type { Association } from '@/api/curation'

const csvCell = (value: unknown): string => {
  const s = String(value ?? '')
  return /[",\r\n]/.test(s) ? `"${s.replaceAll('"', '""')}"` : s
}

/** Rows of cells (first row = headers) to RFC 4180 CSV */
export const toCsv = (rows: unknown[][]): string =>
  rows.map(r => r.map(csvCell).join(',')).join('\n')

export const today = () => new Date().toISOString().slice(0, 10)

/** One readable CSV row per published association */
export const associationsCsv = (records: Association[]): string =>
  toCsv([
    [
      'Gene',
      'Disease',
      'MONDO',
      'Mode of inheritance',
      'Relationship',
      'Classification',
      'Points',
      'Methodology',
      'Curator',
      'Reviewer',
      'Status',
      'Approval',
      'ClinGen classification',
      'PMIDs',
      'Synopsis',
      'URL'
    ],
    ...records.map(r => [
      r.gene_symbol,
      r.disease_name,
      r.disease_id,
      r.moi_label ?? r.moi,
      r.relationship_type,
      r.evidence_strength,
      r.scores?.total,
      [r.methodology, r.methodology_version].filter(Boolean).join(' '),
      r.external_curator,
      r.human_reviewer_name ?? r.external_reviewer,
      r.status,
      r.approval_kind,
      r.adopted_clingen?.classification,
      (r.citations ?? []).map(c => c.replace(/^PMID:\s*/i, '')).join(';'),
      r.evidence_summary,
      `${window.location.origin}/curation/associations/${r.gene_symbol}`
    ])
  ])

/** Clipboard copy with a "copied" flag and toast, and Blob download, shared by the public pages */
export function useShareExport() {
  const copied = ref<string | null>(null)
  let timer: ReturnType<typeof setTimeout>

  const copy = async (text: string, key: string, message: string) => {
    try {
      await navigator.clipboard.writeText(text)
      copied.value = key
      clearTimeout(timer)
      timer = setTimeout(() => (copied.value = null), 2000)
      toast.success(message)
    } catch (error) {
      window.logService.warn('Clipboard write failed:', error)
      toast.error('Could not copy to the clipboard')
    }
  }

  const download = (content: string, type: string, filename: string) => {
    const url = URL.createObjectURL(new Blob([content], { type }))
    const a = document.createElement('a')
    a.href = url
    a.download = filename
    a.click()
    URL.revokeObjectURL(url)
  }

  /** Browser print dialog ("Save as PDF"); the title names the saved file */
  const printPdf = (name: string) => {
    const title = document.title
    document.title = name
    window.addEventListener('afterprint', () => (document.title = title), { once: true })
    window.print()
  }

  return { copied, copy, download, printPdf }
}
