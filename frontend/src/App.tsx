import { useEffect, useMemo, useState, type FormEvent } from 'react'
import { AlertCircle, ArrowRight, CheckCircle2, ChevronRight, ClipboardList, Clock3, FilePlus2, FileSearch, Filter, HeartHandshake, LayoutDashboard, LoaderCircle, Plus, Search, ShieldCheck, Sparkles } from 'lucide-react'
import { api } from './api'
import { mockCriteria, samplePacketUrl } from './mockCriteria'
import { PacketReview } from '@/components/PacketReview'
import type { NewReferral, Referral, ReferralStatus } from './types'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

const statuses: { value: ReferralStatus; label: string }[] = [
  { value: 'new', label: 'New' },
  { value: 'needs_info', label: 'Needs information' },
  { value: 'ready_for_review', label: 'Ready for review' },
  { value: 'accepted', label: 'Accepted (staff)' },
  { value: 'closed', label: 'Closed' },
]
const labels: Record<ReferralStatus, string> = Object.fromEntries(statuses.map((status) => [status.value, status.label])) as Record<ReferralStatus, string>
const statusStyles: Record<ReferralStatus, string> = {
  new: 'border-sky-200 bg-sky-50 text-sky-700',
  needs_info: 'border-amber-200 bg-amber-50 text-amber-800',
  ready_for_review: 'border-emerald-200 bg-emerald-50 text-emerald-800',
  accepted: 'border-teal-200 bg-teal-50 text-teal-800',
  closed: 'border-slate-200 bg-slate-100 text-slate-600',
}
const emptyForm: NewReferral = { patient_alias: '', hospital_name: '', reason: '' }
const formatDate = (iso: string) => new Date(iso).toLocaleDateString(undefined, { month: 'short', day: 'numeric', year: 'numeric' })

function StatusBadge({ status }: { status: ReferralStatus }) {
  return <Badge variant="outline" className={statusStyles[status]}><span className="size-1.5 rounded-full bg-current"/>{labels[status]}</Badge>
}

function App() {
  const [referrals, setReferrals] = useState<Referral[]>([])
  const [selectedId, setSelectedId] = useState<string | null>(null)
  const [filter, setFilter] = useState<ReferralStatus | 'all'>('all')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [newReferral, setNewReferral] = useState<NewReferral>(emptyForm)

  useEffect(() => {
    api.listReferrals()
      .then(setReferrals)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Cannot connect to API'))
      .finally(() => setLoading(false))
  }, [])

  const visible = useMemo(() => referrals.filter((r) => (filter === 'all' || r.status === filter) &&
    [r.patient_alias, r.hospital_name, r.reason].some((text) => text.toLowerCase().includes(query.toLowerCase()))), [referrals, filter, query])
  const selected = referrals.find((r) => r.id === selectedId) ?? visible[0] ?? null
  const needsInfo = referrals.filter((r) => r.status === 'needs_info').length
  const ready = referrals.filter((r) => r.status === 'ready_for_review').length

  async function createReferral(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      const added = await api.createReferral(newReferral)
      setReferrals((prev) => [added, ...prev])
      setSelectedId(added.id)
      setFilter('all')
      setQuery('')
      setFormOpen(false)
      setNewReferral(emptyForm)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create referral')
    } finally { setBusy(false) }
  }

  async function updateStatus(status: ReferralStatus) {
    if (!selected) return
    setBusy(true)
    setError('')
    try {
      const updated = await api.updateStatus(selected.id, status)
      setReferrals((prev) => prev.map((r) => r.id === updated.id ? updated : r))
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to update referral')
    } finally { setBusy(false) }
  }

  return <div className="min-h-screen bg-background lg:flex">
    <aside className="hidden w-[234px] shrink-0 flex-col border-r bg-white px-4 py-6 lg:flex">
      <div className="flex items-center gap-2.5 px-2">
        <div className="flex size-9 items-center justify-center rounded-xl bg-primary text-white"><HeartHandshake className="size-5"/></div>
        <div className="text-[17px] font-semibold tracking-tight">Referral<span className="text-primary">Flow</span></div>
      </div>
      <p className="mb-3 mt-12 px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">Workspace</p>
      <div className="flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-2.5 text-sm font-semibold text-primary"><LayoutDashboard className="size-4"/>Referral intake</div>
      <div className="mt-2 flex items-center gap-2 rounded-lg px-3 py-2.5 text-sm text-muted-foreground"><ClipboardList className="size-4"/>Coordinator overview</div>
      <div className="mt-auto rounded-lg border bg-muted/50 p-3">
        <div className="mb-1 flex items-center gap-2 text-xs font-semibold"><ShieldCheck className="size-4 text-primary"/>Demo environment</div>
        <p className="text-[11px] leading-5 text-muted-foreground">Synthetic referrals only. Not approved for patient information.</p>
      </div>
    </aside>

    <main className="min-w-0 flex-1">
      <header className="flex h-[66px] items-center justify-between border-b bg-white px-5 sm:px-8">
        <div className="flex items-center gap-2 text-sm font-medium"><span className="lg:hidden text-primary">ReferralFlow</span><span className="hidden text-muted-foreground lg:inline">Workspace</span><ChevronRight className="hidden size-3.5 text-muted-foreground lg:inline"/>Referral intake</div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="size-2 rounded-full bg-emerald-500"/>OC Impact Lab · Prototype</div>
      </header>
      <div className="mx-auto max-w-[1440px] space-y-6 p-5 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">Intake operations</div><h1 className="text-3xl font-semibold tracking-tight">Referral queue</h1><p className="mt-2 text-sm text-muted-foreground">Keep every hospital referral moving toward coordinator review.</p></div>
          <Button onClick={() => setFormOpen(true)}><Plus/> New referral</Button>
        </div>

        {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"><AlertCircle className="mt-0.5 size-4 shrink-0"/><div><b>Something went wrong.</b> {error}</div><Button size="sm" variant="outline" onClick={() => window.location.reload()} className="ml-auto">Retry</Button></div>}
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><CardContent className="flex items-center justify-between p-5"><div><p className="text-xs font-medium text-muted-foreground">Total referrals</p><p className="mt-2 text-3xl font-semibold tabular-nums">{referrals.length}</p><p className="mt-1 text-xs text-muted-foreground">All received cases</p></div><div className="rounded-xl bg-slate-100 p-3 text-slate-600"><ClipboardList className="size-5"/></div></CardContent></Card>
          <Card><CardContent className="flex items-center justify-between p-5"><div><p className="text-xs font-medium text-muted-foreground">Needs information</p><p className="mt-2 text-3xl font-semibold tabular-nums">{needsInfo}</p><p className="mt-1 text-xs text-amber-700">Waiting for clarification</p></div><div className="rounded-xl bg-amber-50 p-3 text-amber-700"><Clock3 className="size-5"/></div></CardContent></Card>
          <Card><CardContent className="flex items-center justify-between p-5"><div><p className="text-xs font-medium text-muted-foreground">Ready for review</p><p className="mt-2 text-3xl font-semibold tabular-nums">{ready}</p><p className="mt-1 text-xs text-emerald-700">Awaiting a staff member</p></div><div className="rounded-xl bg-emerald-50 p-3 text-emerald-700"><CheckCircle2 className="size-5"/></div></CardContent></Card>
        </div>

        <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.45fr)_minmax(340px,1fr)]">
          <Card className="min-w-0 overflow-hidden">
            <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b pb-5"><div><CardTitle>Incoming referrals</CardTitle><CardDescription className="mt-1">Select a case to inspect or update it.</CardDescription></div><Badge variant="outline">{visible.length} cases</Badge></CardHeader>
            <div className="flex flex-wrap items-center gap-2 border-b px-5 py-4">
              <div className="relative min-w-[185px] flex-1"><Search className="absolute left-3 top-3 size-4 text-muted-foreground"/><Input aria-label="Search referrals" placeholder="Search referrals..." value={query} onChange={(e) => setQuery(e.target.value)} className="pl-9"/></div>
              <div className="flex items-center gap-2"><Filter className="size-4 text-muted-foreground"/><Select value={filter} onValueChange={(value) => { setFilter(value as ReferralStatus | 'all'); setSelectedId(null) }}><SelectTrigger className="w-[166px]" aria-label="Filter referrals"><SelectValue placeholder="All statuses"/></SelectTrigger><SelectContent><SelectItem value="all">All statuses</SelectItem>{statuses.map((status) => <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>)}</SelectContent></Select></div>
            </div>
            <Table>
              <TableHeader><TableRow><TableHead>Referral</TableHead><TableHead>Hospital</TableHead><TableHead>Status</TableHead><TableHead>Received</TableHead></TableRow></TableHeader>
              <TableBody>
                {visible.map((r) => <TableRow key={r.id} data-selected={selected?.id === r.id} className={`cursor-pointer data-[selected=true]:bg-primary/[0.045] focus-within:bg-muted/50`}><TableCell><button className="block text-left outline-none focus-visible:underline" onClick={() => setSelectedId(r.id)}><span className="font-semibold">{r.patient_alias}</span><span className="mt-1 block text-xs text-muted-foreground">#{r.id.slice(0, 8)}</span></button></TableCell><TableCell className="max-w-[165px] text-muted-foreground"><span className="line-clamp-2">{r.hospital_name}</span></TableCell><TableCell><StatusBadge status={r.status}/></TableCell><TableCell className="whitespace-nowrap text-xs text-muted-foreground">{formatDate(r.created_at)}</TableCell></TableRow>)}
                {loading && <TableRow><TableCell colSpan={4} className="h-28 text-center text-sm text-muted-foreground"><LoaderCircle className="mr-2 inline size-4 animate-spin"/>Loading referrals...</TableCell></TableRow>}
                {!loading && visible.length === 0 && <TableRow><TableCell colSpan={4} className="h-28 text-center text-sm text-muted-foreground">No matching referrals.</TableCell></TableRow>}
              </TableBody>
            </Table>
            <div className="flex items-center justify-between border-t px-5 py-3 text-xs text-muted-foreground"><span>Showing {visible.length} of {referrals.length} referrals</span><span>Fictional demo data</span></div>
          </Card>

          <Card className="min-w-0 overflow-hidden">
            <CardHeader className="border-b pb-5"><div className="flex items-center justify-between"><CardTitle>Referral details</CardTitle><FileSearch className="size-4 text-muted-foreground"/></div><CardDescription>Coordinator review workspace</CardDescription></CardHeader>
            {selected ? <div>
              <CardContent className="space-y-5">
                <div><div className="mb-1 flex flex-wrap items-center justify-between gap-2"><h2 className="text-xl font-semibold tracking-tight">{selected.patient_alias}</h2><StatusBadge status={selected.status}/></div><p className="text-sm text-muted-foreground">{selected.hospital_name}</p></div>
                <div className="space-y-2"><Label>Workflow status</Label><Select value={selected.status} onValueChange={(value) => void updateStatus(value as ReferralStatus)} disabled={busy}><SelectTrigger aria-label="Update workflow status"><SelectValue/></SelectTrigger><SelectContent>{statuses.map((status) => <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>)}</SelectContent></Select><p className="text-xs leading-5 text-muted-foreground">All acceptance decisions require authorized human review.</p></div>
                <div className="border-t pt-4"><p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Referral reason</p><p className="text-sm leading-6">{selected.reason}</p></div>
                <div className="border-t pt-4"><p className="mb-2 text-[11px] font-semibold uppercase tracking-widest text-muted-foreground">Coordinator notes</p><p className="text-sm leading-6 text-muted-foreground">{selected.notes || 'No notes yet.'}</p></div>
              </CardContent>
              <div className="border-t bg-gradient-to-br from-teal-50/80 to-white p-5"><div className="flex gap-3"><div className="h-fit rounded-lg bg-primary/10 p-2 text-primary"><Sparkles className="size-4"/></div><div><h3 className="text-sm font-semibold">Coming next: Claude document review</h3><p className="mt-1 text-xs leading-5 text-muted-foreground">Upload a synthetic PDF, identify missing packet details, and show page-level evidence for staff to verify.</p><div className="mt-3 inline-flex items-center gap-1 text-xs font-medium text-primary">Planned feature <ArrowRight className="size-3"/></div></div></div></div>
            </div> : <CardContent className="flex min-h-72 flex-col items-center justify-center gap-3 text-center text-muted-foreground"><FilePlus2 className="size-8"/><p className="text-sm">Choose or create a referral to inspect it.</p></CardContent>}
          </Card>
        </div>
        <PacketReview fileUrl={samplePacketUrl} criteria={mockCriteria}/>
        <footer className="flex flex-wrap justify-between gap-2 border-t pt-5 text-xs text-muted-foreground"><span>ReferralFlow · Hackathon prototype</span><span>No PHI, authentication, or production security controls</span></footer>
      </div>
    </main>

    <Dialog open={formOpen} onOpenChange={setFormOpen}>
      <DialogContent>
        <DialogHeader><DialogTitle>New referral</DialogTitle><DialogDescription>Create a fictional referral for your intake queue. Do not enter real patient information.</DialogDescription></DialogHeader>
        <form className="mt-5 space-y-4" onSubmit={createReferral}>
          <div className="space-y-2"><Label htmlFor="patient-alias">Fictional patient alias</Label><Input id="patient-alias" required minLength={2} maxLength={80} value={newReferral.patient_alias} onChange={(e) => setNewReferral((p) => ({ ...p, patient_alias: e.target.value }))} placeholder="Demo patient D"/></div>
          <div className="space-y-2"><Label htmlFor="hospital">Hospital</Label><Input id="hospital" required minLength={2} maxLength={120} value={newReferral.hospital_name} onChange={(e) => setNewReferral((p) => ({ ...p, hospital_name: e.target.value }))} placeholder="Example Hospital"/></div>
          <div className="space-y-2"><Label htmlFor="reason">Reason for referral</Label><Textarea id="reason" required minLength={2} maxLength={3000} rows={3} value={newReferral.reason} onChange={(e) => setNewReferral((p) => ({ ...p, reason: e.target.value }))} placeholder="Recovery needs and outstanding documentation..."/></div>
          <DialogFooter><Button type="button" variant="outline" onClick={() => setFormOpen(false)}>Cancel</Button><Button type="submit" disabled={busy}>{busy ? <LoaderCircle className="animate-spin"/> : <Plus/>}Create referral</Button></DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </div>
}
export default App
