import { networkAnalysisConfig } from '../../config/networkAnalysis'
import type { HPOClassificationsResult } from '../../api/genes'

type Classification = HPOClassificationsResult['data'][number]

const percent = (count: number, denominator: number): string | null =>
  denominator > 0 ? ((count / denominator) * 100).toFixed(1) : null

const breakdown = (
  counts: Record<string, number>,
  group: 'clinical_group' | 'onset_group',
  denominator: number
) =>
  Object.entries(counts)
    .map(([key, count]) => ({
      key,
      label: networkAnalysisConfig.nodeColoring.labels[group][key] || key,
      color: networkAnalysisConfig.nodeColoring.colorSchemes[group][key],
      count,
      percentage: percent(count, denominator)
    }))
    .sort((a, b) => b.count - a.count)

/**
 * HPO statistics for a set of genes. A gene counts as having HPO data only when
 * at least one classification is known; syndromic percentages use only genes
 * assessed true/false, and unassessed (null) genes are reported separately (#253).
 */
export function computeHpoClusterStats(geneIds: number[], hpoLookup: Map<number, Classification>) {
  const clinicalCounts: Record<string, number> = {}
  const onsetCounts: Record<string, number> = {}
  let syndromicCount = 0
  let isolatedCount = 0
  let hpoDataCount = 0
  const total = geneIds.length

  geneIds.forEach(geneId => {
    const c = hpoLookup.get(geneId)
    if (!c || (c.clinical_group == null && c.onset_group == null && c.is_syndromic == null)) {
      return
    }
    hpoDataCount++
    const clinicalGroup = c.clinical_group || 'null'
    clinicalCounts[clinicalGroup] = (clinicalCounts[clinicalGroup] || 0) + 1
    const onsetGroup = c.onset_group || 'null'
    onsetCounts[onsetGroup] = (onsetCounts[onsetGroup] || 0) + 1
    if (c.is_syndromic === true) syndromicCount++
    else if (c.is_syndromic === false) isolatedCount++
  })

  const assessedCount = syndromicCount + isolatedCount
  return {
    total,
    hpoDataCount,
    hpoDataPercentage: percent(hpoDataCount, total),
    clinical: breakdown(clinicalCounts, 'clinical_group', hpoDataCount),
    onset: breakdown(onsetCounts, 'onset_group', hpoDataCount),
    syndromic: {
      assessedCount,
      unknownCount: total - assessedCount,
      syndromicCount,
      syndromicPercentage: percent(syndromicCount, assessedCount),
      isolatedCount,
      isolatedPercentage: percent(isolatedCount, assessedCount)
    }
  }
}
