import type { CriterionResult } from './types'

// Mocked analysis results for the local sample packet (samples/R01.pdf).
// Will be replaced by Claude's per-criterion output from the backend.
export const samplePacketUrl = '/samples/R01.pdf'

export const mockCriteria: CriterionResult[] = [
  { id: 'homeless', name: 'Currently experiencing homelessness', status: 'met', evidence: '"Currently homeless" is checked on the referral form.', page: 2 },
  { id: 'diagnosis', name: 'Qualifying admitting diagnosis', status: 'met', evidence: 'Chief complaint: Major Depressive Disorder.', page: 2 },
  { id: 'substance_use', name: 'No active substance withdrawal', status: 'met', evidence: 'Substance abuse: "None" checked.', page: 2 },
  { id: 'adls', name: 'Independent with ADLs', status: 'met', evidence: '"Independent w/all ADLs" marked Yes.', page: 2 },
  { id: 'ambulatory', name: 'Ambulatory', status: 'met', evidence: 'Ambulatory: Yes. Assistive device: No.', page: 2 },
  { id: 'continence', name: 'Continent of bowel & bladder', status: 'not_met', evidence: '"Continent of Bowel & Bladder" appears marked No. Confirm with hospital.', page: 2 },
  { id: 'meds', name: 'Self-administers medications', status: 'met', evidence: '"Self Administer All Meds" marked Yes.', page: 2 },
  { id: 'tb', name: 'TB test or chest X-ray results', status: 'missing', evidence: 'PPD/TB test and chest X-ray fields are blank.', page: 2 },
  { id: 'cognition', name: 'No significant cognitive impairment', status: 'unclear', evidence: 'Form leaves cognitive impairment unchecked, but diagnosis list includes F03.90 unspecified dementia.', page: 10 },
  { id: 'follow_up', name: 'Specialist follow-up plan', status: 'met', evidence: 'Specialist follow-up care: No.', page: 5 },
  { id: 'mar', name: 'Medication administration record', status: 'met', evidence: 'Medication administration record attached.', page: 20 },
]
