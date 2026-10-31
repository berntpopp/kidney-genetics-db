/** One-shot Gene Curator import page (#448) */

import { describe, it, expect, vi, afterEach } from 'vitest'
import { flushPromises, mount, RouterLinkStub } from '@vue/test-utils'
import type { VueWrapper } from '@vue/test-utils'
import AdminGeneCuratorImport from '@/views/admin/AdminGeneCuratorImport.vue'
import { importGeneCuratorExport } from '@/api/admin/geneCurator'
import { toast } from 'vue-sonner'

vi.mock('@/api/admin/geneCurator', () => ({ importGeneCuratorExport: vi.fn() }))
vi.mock('vue-sonner', () => ({ toast: { success: vi.fn(), info: vi.fn(), error: vi.fn() } }))
const upload = vi.mocked(importGeneCuratorExport)

const ref = (id: string, symbol: string) => ({
  curation_id: `11111111-0000-4000-8000-0000000000${id}`,
  gene_symbol: symbol,
  hgnc_id: `HGNC:${id}`,
  entity_key: `MONDO:00000${id}|AR`
})

let wrapper: VueWrapper | undefined
afterEach(() => {
  wrapper?.unmount()
  vi.clearAllMocks()
})

async function mountPage(withFile = true) {
  wrapper = mount(AdminGeneCuratorImport, {
    global: { stubs: { AdminHeader: true, RouterLink: RouterLinkStub } }
  })
  if (withFile) {
    const input = wrapper.find('input[type="file"]')
    Object.defineProperty(input.element, 'files', {
      value: [new File(['{}'], 'export.json', { type: 'application/json' })]
    })
    await input.trigger('change')
  }
  await wrapper.find('form').trigger('submit')
  await flushPromises()
  return wrapper
}

describe('AdminGeneCuratorImport', () => {
  it('renders a labelled file input and says where imports land', () => {
    wrapper = mount(AdminGeneCuratorImport, {
      global: { stubs: { AdminHeader: true, RouterLink: RouterLinkStub } }
    })
    expect(wrapper.find('label[for="gc-export-file"]').exists()).toBe(true)
    expect(wrapper.find('#gc-export-file').attributes('accept')).toContain('.json')
    expect(wrapper.text()).toContain('gene-curator-import')
    expect(wrapper.find('[aria-live="polite"]').exists()).toBe(true)
  })

  it('asks for a file instead of uploading nothing', async () => {
    const w = await mountPage(false)
    expect(upload).not.toHaveBeenCalled()
    expect(w.find('[data-testid="gc-failure"]').text()).toContain('Choose a file first')
  })

  it('shows every report group with record links and reasons', async () => {
    upload.mockResolvedValue({
      data: {
        rows: 6,
        created: [{ ...ref('01', 'PKD1'), record_id: 7 }],
        already_imported: [{ ...ref('02', 'PKD2'), record_id: 3 }],
        conflicts: [
          {
            ...ref('03', 'NPHS1'),
            reason: 'a KGDB record exists',
            existing_record_id: 9,
            existing_source: 'kgdb',
            existing_status: 'published'
          }
        ],
        rejected: [{ ...ref('04', 'COL4A5'), reason: "unknown MOI 'HP:0000001'" }],
        genes_not_in_kgdb: [ref('05', 'NOTAGENE')],
        dropped_fields: [{ ...ref('01', 'PKD1'), fields: ['diagnostics.foo'] }]
      }
    } as never)
    const w = await mountPage()
    expect(upload).toHaveBeenCalledWith(expect.any(File))
    expect(toast.success).toHaveBeenCalled()
    const group = (key: string) => w.find(`[data-testid="gc-${key}"]`).text()
    expect(group('created')).toContain('Record #7')
    expect(group('already_imported')).toContain('Record #3')
    expect(group('conflicts')).toContain('Record #9')
    expect(group('conflicts')).toContain('a KGDB record exists (kgdb, published)')
    expect(group('rejected')).toContain("unknown MOI 'HP:0000001'")
    expect(group('genes_not_in_kgdb')).toContain('HGNC:05')
    expect(group('dropped_fields')).toContain('diagnostics.foo')
    // Record numbers are text: only the intro links to the workflow list
    expect(w.findAllComponents(RouterLinkStub)).toHaveLength(1)
    // Screen readers hear the summary, not every row
    expect(w.find('[aria-live="polite"]').text()).toContain('6 curations in the file, 1 imported')
    expect(w.find('[aria-live="polite"] [data-testid="gc-created"]').exists()).toBe(false)
  })

  it('does not report a run that imported nothing as a success', async () => {
    const none = { created: [], conflicts: [], genes_not_in_kgdb: [], dropped_fields: [] }
    upload.mockResolvedValue({
      data: { ...none, rows: 1, already_imported: [ref('02', 'PKD2')], rejected: [] }
    } as never)
    await mountPage()
    expect(toast.success).not.toHaveBeenCalled()
    expect(toast.info).toHaveBeenCalledWith('Imported 0 of 1 curations')
  })

  it('lists the schema paths of a 422', async () => {
    upload.mockRejectedValue({
      response: {
        status: 422,
        data: {
          error: {
            message: "Validation failed for 'file': not a Gene Curator export v1: ...",
            details: {
              errors: ['$[0].items[0].hgnc_id: required', "$[0].export_version: must be '1'"]
            }
          }
        }
      }
    })
    const w = await mountPage()
    const items = w.findAll('[data-testid="gc-failure"] li').map(li => li.text())
    expect(items).toEqual(['$[0].items[0].hgnc_id: required', "$[0].export_version: must be '1'"])
    expect(w.find('[data-testid="gc-failure"]').text()).toContain('Not a Gene Curator export v1')
  })

  it('explains a network error', async () => {
    upload.mockRejectedValue(new Error('Network Error'))
    const w = await mountPage()
    expect(w.find('[data-testid="gc-failure"]').text()).toContain('Could not reach the server')
  })
})
