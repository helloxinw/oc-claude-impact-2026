// Groups admission-criteria rule ids into the same categories the IHH outline itself uses
// (backend/app/data/admission_criteria.json), so the Criteria tab can show "General" rules
// (apply to every patient) separately from disease-specific ones (only shown when the backend
// actually evaluated them for this patient's diagnosis — see claude_client.py).

const RULE_ID_PREFIXES: [prefix: string, category: string][] = [
  ['GEN-', 'General'],
  ['ADL-', 'ADLs'],
  ['MOB-', 'Mobility'],
  ['MH-', 'Mental Health'],
  ['COG-', 'Cognition'],
  ['OTH-', 'Other Factors'],
  ['EOL-', 'End of life care'],
  ['INF-', 'Infection Control'],
  ['FORM-X4', 'Infection Control'],
  ['FORM-X5', 'Substance Use'],
  ['DM-', 'Diabetes'],
  ['ID-', 'Infection'],
  ['RESP-', 'Respiratory'],
  ['RSP-', 'Respiratory'],
  ['CARD-', 'Cardiac & Circulatory'],
  ['CIR-', 'Cardiac & Circulatory'],
  ['INT-', 'Integumentary'],
  ['OPH-', 'Ophthalmology'],
  ['MSK-', 'Musculoskeletal'],
  ['GI-', 'GI'],
  ['END-', 'Endocrine'],
  ['GU-', 'GU'],
  ['NEU-', 'Neurology'],
]

// Always shown first, in this order, regardless of diagnosis — every patient gets screened
// against these. Anything else is disease-specific and only appears when the backend found it
// relevant to this patient's documented conditions.
export const GENERAL_CATEGORIES = [
  'General', 'ADLs', 'Mobility', 'Mental Health', 'Cognition', 'Other Factors',
  'End of life care', 'Infection Control', 'Substance Use',
]

export function categoryForRuleId(ruleId: string): string {
  const match = RULE_ID_PREFIXES.find(([prefix]) => ruleId.startsWith(prefix))
  return match ? match[1] : 'Other'
}

export function groupByCategory<T extends { rule_id: string | null }>(items: T[]): { category: string; items: T[] }[] {
  const groups = new Map<string, T[]>()
  for (const item of items) {
    const category = categoryForRuleId(item.rule_id ?? '')
    if (!groups.has(category)) groups.set(category, [])
    groups.get(category)!.push(item)
  }
  const diseaseCategories = [...groups.keys()].filter((c) => !GENERAL_CATEGORIES.includes(c)).sort()
  const order = [...GENERAL_CATEGORIES, ...diseaseCategories]
  return order.filter((c) => groups.has(c)).map((category) => ({ category, items: groups.get(category)! }))
}
