import type { AiDecision, DocumentStatus, Referral, ReferralStatus } from '@/types'
import { Badge } from '@/components/ui/badge'

export const statuses: { value: ReferralStatus; label: string }[] = [
  { value: 'new', label: 'New' },
  { value: 'needs_info', label: 'Needs information' },
  { value: 'ready_for_review', label: 'Ready for review' },
  { value: 'accepted', label: 'Accepted (staff)' },
  { value: 'closed', label: 'Closed' },
]
export const statusLabels: Record<ReferralStatus, string> = Object.fromEntries(statuses.map((s) => [s.value, s.label])) as Record<ReferralStatus, string>
export const statusStyles: Record<ReferralStatus, string> = {
  new: 'border-sky-200 bg-sky-50 text-sky-700',
  needs_info: 'border-amber-200 bg-amber-50 text-amber-800',
  ready_for_review: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  accepted: 'border-teal-200 bg-teal-50 text-teal-800',
  closed: 'border-slate-200 bg-slate-100 text-slate-600',
}

export const formatDate = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

export function StatusBadge({ status }: { status: ReferralStatus }) {
  return <Badge variant="outline" className={statusStyles[status]}><span className="size-1.5 rounded-full bg-current" />{statusLabels[status]}</Badge>
}

const packetStatusStyles: Record<string, string> = {
  uploaded: 'border-amber-200 bg-amber-50 text-amber-700',
  processing: 'border-amber-200 bg-amber-50 text-amber-700',
  processed: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  failed: 'border-red-200 bg-red-50 text-red-700',
}
const packetStatusLabels: Record<string, string> = {
  uploaded: 'Processing…',
  processing: 'Processing…',
  processed: 'Extracted',
  failed: 'Failed',
}

export function PacketStatusBadge({ referral }: { referral: Pick<Referral, 'document_status' | 'document_page_count'> }) {
  const status = referral.document_status as DocumentStatus | null
  if (!status) return <span className="text-xs text-muted-foreground">No packet</span>
  return (
    <Badge variant="outline" className={packetStatusStyles[status]}>
      <span className="size-1.5 rounded-full bg-current" />
      {packetStatusLabels[status]}
      {status === 'processed' && referral.document_page_count ? ` · ${referral.document_page_count}p` : ''}
    </Badge>
  )
}

const aiDecisionStyles: Record<AiDecision, string> = {
  yes: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  no: 'border-red-200 bg-red-50 text-red-700',
  maybe: 'border-amber-200 bg-amber-50 text-amber-700',
}
const aiDecisionLabels: Record<AiDecision, string> = { yes: 'Eligible', no: 'Ineligible', maybe: 'Needs review' }

export function AiDecisionBadge({ referral }: { referral: Pick<Referral, 'ai_decision'> }) {
  if (!referral.ai_decision) return <span className="text-xs text-muted-foreground">&mdash;</span>
  return <Badge variant="outline" className={aiDecisionStyles[referral.ai_decision]}><span className="size-1.5 rounded-full bg-current" />{aiDecisionLabels[referral.ai_decision]}</Badge>
}
