export type ReferralStatus = 'new' | 'needs_info' | 'ready_for_review' | 'accepted' | 'closed'

export interface Referral {
  id: string
  patient_alias: string
  hospital_name: string
  reason: string
  status: ReferralStatus
  notes: string
  created_at: string
  updated_at: string
}

export type NewReferral = Pick<Referral, 'patient_alias' | 'hospital_name' | 'reason'>

export type CriterionStatus = 'met' | 'not_met' | 'missing' | 'unclear'

export interface CriterionResult {
  id: string
  name: string
  status: CriterionStatus
  evidence: string
  page: number
}
