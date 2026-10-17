import { useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { AlertCircle, ArrowLeft, LoaderCircle } from 'lucide-react'
import { api } from '@/api'
import type { Referral, ReferralStatus } from '@/types'
import { formatDate, statuses, StatusBadge } from '@/lib/referralUi'
import { DocumentReview } from '@/components/DocumentReview'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'

export function ReferralWorkspace() {
  const { id } = useParams<{ id: string }>()
  const [referral, setReferral] = useState<Referral | null>(null)
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!id) return
    setLoading(true)
    api.getReferral(id)
      .then(setReferral)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Referral not found'))
      .finally(() => setLoading(false))
  }, [id])

  async function updateStatus(status: ReferralStatus) {
    if (!referral) return
    setBusy(true)
    setError('')
    try {
      setReferral(await api.updateStatus(referral.id, status))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update referral')
    } finally {
      setBusy(false)
    }
  }

  if (loading) {
    return <div className="flex min-h-screen items-center justify-center text-sm text-muted-foreground"><LoaderCircle className="mr-2 size-4 animate-spin"/>Loading referral...</div>
  }
  if (error || !referral) {
    return <div className="flex min-h-screen flex-col items-center justify-center gap-3 text-center">
      <AlertCircle className="size-8 text-red-500"/>
      <p className="text-sm text-muted-foreground">{error || 'Referral not found.'}</p>
      <Link to="/"><Button variant="outline" size="sm"><ArrowLeft/> Back to queue</Button></Link>
    </div>
  }

  return <div className="min-h-screen bg-background">
    <header className="border-b bg-white px-5 py-4 sm:px-8">
      <Link to="/" className="inline-flex items-center gap-1 text-xs font-medium text-muted-foreground hover:text-primary"><ArrowLeft className="size-3.5"/> Referral queue</Link>
      <div className="mt-3 flex flex-wrap items-start justify-between gap-4">
        <div>
          <div className="flex flex-wrap items-center gap-2"><h1 className="text-2xl font-semibold tracking-tight">{referral.patient_alias}</h1><StatusBadge status={referral.status}/></div>
          <p className="mt-1 text-sm text-muted-foreground">{referral.hospital_name} &middot; received {formatDate(referral.created_at)}</p>
          <p className="mt-2 max-w-2xl text-sm leading-6">{referral.reason}</p>
        </div>
        <div className="w-full max-w-[220px] space-y-1.5 sm:w-[220px]">
          <Label className="text-xs">Workflow status</Label>
          <Select value={referral.status} onValueChange={(value) => void updateStatus(value as ReferralStatus)} disabled={busy}>
            <SelectTrigger aria-label="Update workflow status"><SelectValue/></SelectTrigger>
            <SelectContent>{statuses.map((status) => <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>)}</SelectContent>
          </Select>
          <p className="text-[11px] leading-4 text-muted-foreground">All acceptance decisions require authorized human review.</p>
        </div>
      </div>
      {error && <div role="alert" className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"><AlertCircle className="mt-0.5 size-4 shrink-0"/>{error}</div>}
    </header>

    <main className="mx-auto max-w-[1400px] p-5 sm:p-8">
      <DocumentReview referral={referral} onReferralUpdated={setReferral}/>
    </main>
  </div>
}
