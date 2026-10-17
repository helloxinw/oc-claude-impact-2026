import { useEffect, useState, type ChangeEvent } from 'react'
import { AlertTriangle, Check, CheckCircle2, CircleHelp, ExternalLink, FileWarning, Loader2, ShieldAlert, Upload, XCircle } from 'lucide-react'
import { api } from '@/api'
import type { AiDecision, Finding, FindingVerdict, Referral, ReferralDocument } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Progress } from '@/components/ui/progress'
import { Skeleton } from '@/components/ui/skeleton'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Textarea } from '@/components/ui/textarea'

const decisionStyles: Record<AiDecision, string> = {
  yes: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  no: 'border-red-200 bg-red-50 text-red-800',
  maybe: 'border-amber-200 bg-amber-50 text-amber-800',
}
const decisionLabels: Record<AiDecision, string> = { yes: 'Looks eligible', no: 'Looks ineligible', maybe: 'Needs coordinator review' }
const decisionIcons: Record<AiDecision, typeof CheckCircle2> = { yes: CheckCircle2, no: XCircle, maybe: CircleHelp }
const verdictStyles: Record<string, string> = {
  met: 'border-emerald-200 bg-emerald-50 text-emerald-700',
  not_met: 'border-red-200 bg-red-50 text-red-700',
  unclear: 'border-amber-200 bg-amber-50 text-amber-700',
}
const verdictLabels: Record<string, string> = { met: 'Met', not_met: 'Not met', unclear: 'Unclear' }
const verdictOrder: Record<string, number> = { not_met: 0, unclear: 1, met: 2 }

export function DocumentReview({ referral, onReferralUpdated }: { referral: Referral; onReferralUpdated?: (r: Referral) => void }) {
  const [documents, setDocuments] = useState<ReferralDocument[]>([])
  const [findings, setFindings] = useState<Finding[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [error, setError] = useState('')
  const [activePage, setActivePage] = useState<number | null>(null)
  const [activeFindingId, setActiveFindingId] = useState<string | null>(null)
  const [flash, setFlash] = useState(false)

  useEffect(() => {
    let active = true
    setLoading(true)
    setActivePage(null)
    setActiveFindingId(null)
    Promise.all([api.listDocuments(referral.id), api.listFindings(referral.id)])
      .then(([docs, fnds]) => { if (active) { setDocuments(docs); setFindings(fnds) } })
      .catch((e: unknown) => { if (active) setError(e instanceof Error ? e.message : 'Failed to load documents') })
      .finally(() => { if (active) setLoading(false) })
    return () => { active = false }
  }, [referral.id])

  async function handleFile(event: ChangeEvent<HTMLInputElement>) {
    const file = event.target.files?.[0]
    event.target.value = ''
    if (!file) return
    setUploading(true)
    setError('')
    try {
      await api.uploadDocument(referral.id, file)
      const [docs, fnds, updated] = await Promise.all([
        api.listDocuments(referral.id),
        api.listFindings(referral.id),
        api.getReferral(referral.id),
      ])
      setDocuments(docs)
      setFindings(fnds)
      setActivePage(null)
      setActiveFindingId(null)
      onReferralUpdated?.(updated)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to process the packet')
    } finally {
      setUploading(false)
    }
  }

  function updateFinding(updated: Finding) {
    setFindings((prev) => prev.map((f) => (f.id === updated.id ? updated : f)))
  }

  const latestDocument = documents[0]
  const patientSummary = findings.find((f) => f.key === 'patient_summary')
  const fields = findings.filter((f) => f.category === 'extraction' && f.key !== 'patient_summary' && !f.key.startsWith('document:'))
  const checklist = findings.filter((f) => f.key.startsWith('document:'))
  const ruleFindings = [...findings.filter((f) => f.category === 'eligibility_rule')]
    .sort((a, b) => (verdictOrder[a.verdict ?? 'met'] ?? 2) - (verdictOrder[b.verdict ?? 'met'] ?? 2))
  const flagFindings = findings.filter((f) => f.category === 'decision' && f.key.startsWith('flag:'))
  const reviewedCount = ruleFindings.filter((f) => f.verified).length

  function jumpToFinding(finding: Finding) {
    if (!finding.source_page) return
    setActiveFindingId(finding.id)
    setActivePage(finding.source_page)
    setFlash(true)
    window.setTimeout(() => setFlash(false), 900)
  }

  return (
    <div>
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h3 className="text-sm font-semibold">Packet extraction &amp; eligibility</h3>
          <p className="mt-0.5 text-xs text-muted-foreground">Upload the referral packet (PDF) to view it, pull out the clinical facts, and check it against IHH's admission criteria.</p>
        </div>
        <label>
          <input type="file" accept="application/pdf" className="hidden" onChange={handleFile} disabled={uploading} />
          <Button asChild size="sm" disabled={uploading} className={uploading ? 'pointer-events-none opacity-50' : 'cursor-pointer'}>
            <span>{uploading ? <Loader2 className="animate-spin" /> : <Upload />}{uploading ? 'Processing…' : documents.length ? 'Upload new packet' : 'Upload packet'}</span>
          </Button>
        </label>
      </div>

      {error && (
        <div role="alert" className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
          <AlertTriangle className="mt-0.5 size-3.5 shrink-0" />{error}
        </div>
      )}

      {uploading && (
        <div className="mt-4 space-y-2 rounded-lg border bg-muted/30 p-4 text-xs text-muted-foreground">
          <div className="flex items-center gap-2"><Loader2 className="size-3.5 animate-spin" />Running OCR, extracting facts, and checking admission criteria. Longer packets can take a couple of minutes.</div>
          <Progress value={65} className="h-1.5 [&>div]:animate-pulse" />
        </div>
      )}

      {loading && !uploading && <div className="mt-4 space-y-2"><Skeleton className="h-14 w-full" /><Skeleton className="h-14 w-full" /></div>}

      {!loading && !uploading && documents.length === 0 && (
        <div className="mt-4 rounded-lg border border-dashed p-6 text-center text-xs text-muted-foreground">No packet uploaded yet for this referral.</div>
      )}

      {!uploading && latestDocument?.status === 'failed' && (
        <div className="mt-4 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-800">
          <FileWarning className="mt-0.5 size-3.5 shrink-0" />
          <div><b>Could not process {latestDocument.filename}.</b> {latestDocument.error_message}</div>
        </div>
      )}

      {!uploading && latestDocument?.status === 'processed' && (
        <div className="mt-4 grid gap-4 lg:grid-cols-2">
          <div className="min-w-0 lg:sticky lg:top-4 lg:self-start">
            <div className="mb-2 flex items-center justify-between">
              <p className="text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">
                {latestDocument.filename} &middot; {activePage ? `viewing p.${activePage} of ` : ''}{latestDocument.page_count} pages
              </p>
              <a href={api.documentFileUrl(referral.id, latestDocument.id)} target="_blank" rel="noreferrer" className="inline-flex items-center gap-1 text-xs font-medium text-primary hover:underline">
                Open in new tab<ExternalLink className="size-3" />
              </a>
            </div>
            <iframe
              key={`${latestDocument.id}-${activePage ?? 0}`}
              title={`${latestDocument.filename} preview`}
              src={`${api.documentFileUrl(referral.id, latestDocument.id)}${activePage ? `#page=${activePage}` : ''}`}
              className={`h-[75vh] min-h-[520px] w-full rounded-lg border bg-muted/20 transition-shadow duration-300 ${flash ? 'ring-4 ring-primary/50' : ''}`}
            />
            <p className="mt-1.5 text-[11px] text-muted-foreground">Tip: the PDF's own outline panel (sidebar icon in the viewer toolbar) jumps straight to any page a fact or criterion came from.</p>
          </div>

          <div className="min-w-0">
            {referral.ai_decision && (
              <div className={`mb-4 flex items-start gap-3 rounded-lg border p-3 ${decisionStyles[referral.ai_decision]}`}>
                <DecisionIcon decision={referral.ai_decision} />
                <div>
                  <div className="flex flex-wrap items-center gap-2 text-sm font-semibold">
                    {decisionLabels[referral.ai_decision]}
                    <Badge variant="outline" className="border-current/30 bg-white/60 text-[10px] font-medium uppercase tracking-wide">AI draft &middot; needs sign-off</Badge>
                  </div>
                  <p className="mt-1 text-xs leading-5">{referral.ai_decision_summary}</p>
                </div>
              </div>
            )}

            {flagFindings.length > 0 && (
              <div className="mb-4 space-y-2">
                {flagFindings.map((f) => (
                  <div key={f.id} className="flex items-start gap-2 rounded-lg border border-violet-200 bg-violet-50 p-3 text-xs text-violet-900">
                    <ShieldAlert className="mt-0.5 size-3.5 shrink-0" />
                    <div><b>{f.key.replace('flag:', '')} — case-by-case, never automatic.</b> {f.value}</div>
                  </div>
                ))}
              </div>
            )}

            <CoordinatorDecisionPanel referral={referral} onUpdated={(r) => onReferralUpdated?.(r)} />

            <Tabs defaultValue="eligibility">
              <TabsList>
                <TabsTrigger value="eligibility">Criteria ({reviewedCount}/{ruleFindings.length} reviewed)</TabsTrigger>
                <TabsTrigger value="facts">Extracted facts ({fields.length})</TabsTrigger>
                <TabsTrigger value="checklist">Checklist ({checklist.length})</TabsTrigger>
              </TabsList>

              <TabsContent value="eligibility" className="mt-3 space-y-2 max-h-[62vh] overflow-y-auto pr-1">
                {patientSummary && (
                  <div className="mb-3 rounded-lg border bg-muted/30 p-3">
                    <p className="mb-1 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Summary</p>
                    <p className="text-xs leading-5">{patientSummary.value}</p>
                  </div>
                )}
                {ruleFindings.map((f) => (
                  <RuleRow key={f.id} finding={f} active={f.id === activeFindingId} onClick={() => jumpToFinding(f)} onReviewed={updateFinding} />
                ))}
                {ruleFindings.length === 0 && <p className="text-xs text-muted-foreground">No criteria evaluated.</p>}
              </TabsContent>

              <TabsContent value="facts" className="mt-3 space-y-2 max-h-[62vh] overflow-y-auto pr-1">
                {fields.map((f) => <FactRow key={f.id} finding={f} active={f.id === activeFindingId} onClick={() => jumpToFinding(f)} />)}
                {fields.length === 0 && <p className="text-xs text-muted-foreground">No facts extracted.</p>}
              </TabsContent>

              <TabsContent value="checklist" className="mt-3 space-y-1.5 max-h-[62vh] overflow-y-auto pr-1">
                {checklist.map((f) => {
                  const clickable = Boolean(f.source_page)
                  return (
                    <div
                      key={f.id}
                      onClick={clickable ? () => jumpToFinding(f) : undefined}
                      className={`flex items-start gap-2 rounded-md p-1 text-xs transition-colors ${clickable ? 'cursor-pointer hover:bg-muted/60' : ''} ${f.id === activeFindingId ? 'bg-primary/10 ring-1 ring-primary/30' : ''}`}
                    >
                      <Badge variant="outline" className={f.verdict === 'present' ? 'shrink-0 border-emerald-200 bg-emerald-50 text-emerald-700' : 'shrink-0 border-amber-200 bg-amber-50 text-amber-700'}>
                        {f.verdict === 'present' ? 'Found' : 'Missing'}
                      </Badge>
                      <div className="leading-5"><span className="font-medium">{f.key.replace('document:', '')}</span> &mdash; <span className="text-muted-foreground">{f.value}</span></div>
                    </div>
                  )
                })}
                {checklist.length === 0 && <p className="text-xs text-muted-foreground">No checklist items evaluated.</p>}
              </TabsContent>
            </Tabs>
          </div>
        </div>
      )}
    </div>
  )
}

function DecisionIcon({ decision }: { decision: AiDecision }) {
  const Icon = decisionIcons[decision]
  return <Icon className="mt-0.5 size-5 shrink-0" />
}

function CoordinatorDecisionPanel({ referral, onUpdated }: { referral: Referral; onUpdated: (r: Referral) => void }) {
  const [decision, setDecision] = useState<AiDecision | null>(referral.coordinator_decision)
  const [note, setNote] = useState(referral.coordinator_decision_note ?? '')
  const [editing, setEditing] = useState(!referral.coordinator_decision)
  const [saving, setSaving] = useState(false)
  const [error, setError] = useState('')

  async function save() {
    if (!decision) return
    setSaving(true)
    setError('')
    try {
      const updated = await api.updateCoordinatorDecision(referral.id, decision, note)
      onUpdated(updated)
      setEditing(false)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to save your decision')
    } finally {
      setSaving(false)
    }
  }

  if (!editing && referral.coordinator_decision) {
    return (
      <div className={`mb-4 rounded-lg border p-3 ${decisionStyles[referral.coordinator_decision]}`}>
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-2 text-sm font-semibold">
            <DecisionIcon decision={referral.coordinator_decision} />
            Coordinator decision: {decisionLabels[referral.coordinator_decision]}
          </div>
          <Button size="sm" variant="outline" className="h-7 shrink-0 px-2 text-[11px]" onClick={() => setEditing(true)}>Edit</Button>
        </div>
        {referral.coordinator_decision_note && <p className="mt-1 text-xs leading-5">{referral.coordinator_decision_note}</p>}
        {referral.coordinator_decision_at && (
          <p className="mt-1 text-[10px] text-muted-foreground">Recorded {new Date(referral.coordinator_decision_at).toLocaleString()}</p>
        )}
      </div>
    )
  }

  return (
    <div className="mb-4 rounded-lg border border-dashed p-3">
      <p className="mb-2 text-xs font-semibold">Your decision</p>
      <div className="flex flex-wrap gap-1.5">
        <Button size="sm" variant={decision === 'yes' ? 'default' : 'outline'} className="h-7 px-2.5 text-xs" onClick={() => setDecision('yes')}>Approve</Button>
        <Button size="sm" variant={decision === 'no' ? 'default' : 'outline'} className="h-7 px-2.5 text-xs" onClick={() => setDecision('no')}>Deny</Button>
        <Button size="sm" variant={decision === 'maybe' ? 'default' : 'outline'} className="h-7 px-2.5 text-xs" onClick={() => setDecision('maybe')}>Needs more info</Button>
      </div>
      <Textarea className="mt-2 text-xs" rows={2} placeholder="Notes for the record (optional)" value={note} onChange={(e) => setNote(e.target.value)} />
      {error && <p className="mt-1 text-[11px] text-red-700">{error}</p>}
      <div className="mt-2 flex justify-end gap-2">
        {referral.coordinator_decision && <Button size="sm" variant="ghost" className="h-7 px-2 text-[11px]" onClick={() => setEditing(false)}>Cancel</Button>}
        <Button size="sm" className="h-7 px-2.5 text-xs" disabled={!decision || saving} onClick={() => void save()}>
          {saving ? <Loader2 className="size-3 animate-spin" /> : <Check className="size-3" />}Save decision
        </Button>
      </div>
    </div>
  )
}

function RuleRow({ finding, active, onClick, onReviewed }: { finding: Finding; active: boolean; onClick: () => void; onReviewed: (f: Finding) => void }) {
  const [expanded, setExpanded] = useState(false)
  const [overrideDraft, setOverrideDraft] = useState<FindingVerdict | null>(finding.override_verdict)
  const [noteDraft, setNoteDraft] = useState(finding.coordinator_note ?? '')
  const [saving, setSaving] = useState(false)
  const [saveError, setSaveError] = useState('')

  const clickable = Boolean(finding.source_page)
  const effectiveVerdict = finding.override_verdict ?? finding.verdict
  const style = effectiveVerdict ? verdictStyles[effectiveVerdict] : ''
  const overridden = Boolean(finding.override_verdict && finding.override_verdict !== finding.verdict)

  async function handleSave() {
    setSaving(true)
    setSaveError('')
    try {
      const updated = await api.reviewFinding(finding.id, { verified: true, override_verdict: overrideDraft, coordinator_note: noteDraft })
      onReviewed(updated)
      setExpanded(false)
    } catch (e) {
      setSaveError(e instanceof Error ? e.message : 'Failed to save')
    } finally {
      setSaving(false)
    }
  }

  return (
    <div className={`rounded-lg border transition-colors ${active ? 'border-primary/40 bg-primary/5 ring-1 ring-primary/30' : ''}`}>
      <div onClick={clickable ? onClick : undefined} className={clickable ? 'cursor-pointer p-2.5' : 'p-2.5'}>
        <div className="flex items-center gap-2">
          <Badge variant="outline" className={`shrink-0 text-[10px] ${style}`}>{effectiveVerdict ? verdictLabels[effectiveVerdict] : 'N/A'}</Badge>
          {overridden && <Badge variant="outline" className="shrink-0 border-violet-200 bg-violet-50 text-[10px] text-violet-700">overridden</Badge>}
          <span className="text-xs font-semibold">{finding.rule_id}</span>
          {finding.source_page && <span className="text-xs font-normal text-muted-foreground">p.{finding.source_page}</span>}
          {finding.verified && <CheckCircle2 className="ml-auto size-3.5 shrink-0 text-emerald-600" />}
        </div>
        <p className="mt-1 text-xs leading-5">
          {finding.evidence ? <span className="font-medium">{finding.evidence}</span> : <span className="italic text-muted-foreground">Not found in packet</span>}
        </p>
        <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{finding.value}</p>
        {finding.coordinator_note && (
          <p className="mt-1.5 rounded bg-violet-50 px-2 py-1 text-xs leading-5 text-violet-900"><b>Coordinator:</b> {finding.coordinator_note}</p>
        )}
      </div>
      <div className="border-t px-2.5 py-1.5" onClick={(e) => e.stopPropagation()}>
        <button type="button" onClick={() => setExpanded((v) => !v)} className="text-[11px] font-medium text-primary hover:underline">
          {expanded ? 'Close' : finding.verified ? 'Edit review' : 'Review this'}
        </button>
        {expanded && (
          <div className="mt-2 space-y-2">
            <div className="flex flex-wrap items-center gap-1.5">
              <span className="text-[11px] text-muted-foreground">Your verdict:</span>
              {(['met', 'not_met', 'unclear'] as const).map((v) => {
                const isActive = (overrideDraft ?? finding.verdict) === v
                return (
                  <button
                    key={v}
                    type="button"
                    onClick={() => setOverrideDraft(v === finding.verdict ? null : v)}
                    className={`rounded-full border px-2 py-0.5 text-[11px] ${isActive ? verdictStyles[v] : 'text-muted-foreground hover:bg-muted/60'}`}
                  >
                    {verdictLabels[v]}
                  </button>
                )
              })}
            </div>
            <Textarea rows={2} className="text-xs" placeholder="Add a note (optional)" value={noteDraft} onChange={(e) => setNoteDraft(e.target.value)} />
            {saveError && <p className="text-[11px] text-red-700">{saveError}</p>}
            <div className="flex justify-end gap-2">
              <Button size="sm" variant="outline" className="h-6 px-2 text-[11px]" onClick={() => setExpanded(false)} disabled={saving}>Cancel</Button>
              <Button size="sm" className="h-6 px-2 text-[11px]" disabled={saving} onClick={() => void handleSave()}>
                {saving ? <Loader2 className="size-3 animate-spin" /> : <Check className="size-3" />}Save
              </Button>
            </div>
          </div>
        )}
      </div>
    </div>
  )
}

function FactRow({ finding, active, onClick }: { finding: Finding; active: boolean; onClick: () => void }) {
  const clickable = Boolean(finding.source_page)
  return (
    <div
      onClick={clickable ? onClick : undefined}
      className={`rounded-lg border p-2.5 transition-colors ${clickable ? 'cursor-pointer hover:bg-muted/60' : ''} ${active ? 'border-primary/40 bg-primary/5 ring-1 ring-primary/30' : ''}`}
    >
      <div className="flex items-center gap-2 text-xs font-semibold capitalize">
        {finding.key.replace(/_/g, ' ')}
        {finding.source_page && <span className="font-normal text-muted-foreground">p.{finding.source_page}</span>}
        {finding.needs_verification && <Badge variant="outline" className="border-amber-200 bg-amber-50 text-[10px] text-amber-700">low confidence</Badge>}
      </div>
      <p className="mt-0.5 text-xs leading-5 text-muted-foreground">{finding.value}</p>
    </div>
  )
}
