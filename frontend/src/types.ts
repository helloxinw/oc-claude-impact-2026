export type ReferralStatus = 'new' | 'needs_info' | 'ready_for_review' | 'accepted' | 'closed'
export type AiDecision = 'yes' | 'no' | 'maybe'
export type DocumentStatus = 'uploaded' | 'processing' | 'processed' | 'failed'
export type FindingCategory = 'extraction' | 'eligibility_rule' | 'missing_document' | 'decision'
// Eligibility rules: met / not_met / unclear / not_applicable / pending_arrangement (a conditional
// rule whose arrangement isn't confirmed yet). `ask` questions: answered / unanswered, never pass/fail.
// Checklist documents: present / present_unclear / missing.
export type FindingVerdict =
  | 'met' | 'not_met' | 'unclear' | 'not_applicable' | 'pending_arrangement'
  | 'answered' | 'unanswered'
  | 'present' | 'present_unclear' | 'missing'

export interface Referral {
  id: string
  patient_alias: string
  hospital_name: string
  reason: string
  status: ReferralStatus
  notes: string
  ai_decision: AiDecision | null
  ai_decision_summary: string | null
  ai_processed_at: string | null
  coordinator_decision: AiDecision | null
  coordinator_decision_note: string | null
  coordinator_decision_at: string | null
  document_status: DocumentStatus | null
  document_filename: string | null
  document_page_count: number | null
  created_at: string
  updated_at: string
}

export type NewReferral = Pick<Referral, 'patient_alias' | 'hospital_name' | 'reason'>

export interface ReferralDocument {
  id: string
  referral_id: string
  filename: string
  content_type: string
  size_bytes: number
  page_count: number | null
  status: DocumentStatus
  error_message: string | null
  uploaded_at: string
}

export interface Finding {
  id: string
  document_id: string
  referral_id: string
  category: FindingCategory
  key: string
  value: string
  evidence: string | null
  rule_id: string | null
  source_page: number | null
  verdict: FindingVerdict | null
  needs_verification: boolean
  verified: boolean
  override_verdict: FindingVerdict | null
  coordinator_note: string | null
  bbox_x0: number | null
  bbox_y0: number | null
  bbox_x1: number | null
  bbox_y1: number | null
  created_at: string
}
