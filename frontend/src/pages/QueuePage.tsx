import { useEffect, useMemo, useRef, useState, type ChangeEvent, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { AlertCircle, CheckCircle2, ChevronRight, ChevronsUpDown, ClipboardList, Clock3, FileText, Filter, LayoutDashboard, LoaderCircle, LogOut, Paperclip, Plus, Search, Settings, X } from 'lucide-react'
import { api } from '@/api'
import logo from '@/assets/logo.png'
import type { NewReferral, Referral, ReferralStatus } from '@/types'
import { AiDecisionBadge, formatDate, PacketStatusBadge, statuses, StatusBadge } from '@/lib/referralUi'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { Textarea } from '@/components/ui/textarea'

const emptyForm: NewReferral = { patient_alias: '', hospital_name: '', reason: '' }

export function QueuePage() {
  const [referrals, setReferrals] = useState<Referral[]>([])
  const [filter, setFilter] = useState<ReferralStatus | 'all'>('all')
  const [query, setQuery] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const [busyStep, setBusyStep] = useState('')
  const [error, setError] = useState('')
  const [formOpen, setFormOpen] = useState(false)
  const [newReferral, setNewReferral] = useState<NewReferral>(emptyForm)
  const [packetFile, setPacketFile] = useState<File | null>(null)

  useEffect(() => {
    api.listReferrals()
      .then(setReferrals)
      .catch((e: unknown) => setError(e instanceof Error ? e.message : 'Cannot connect to API'))
      .finally(() => setLoading(false))
  }, [])

  const visible = useMemo(() => referrals.filter((r) => (filter === 'all' || r.status === filter) &&
    [r.patient_alias, r.hospital_name, r.reason].some((text) => text.toLowerCase().includes(query.toLowerCase()))), [referrals, filter, query])
  const needsInfo = referrals.filter((r) => r.status === 'needs_info').length
  const ready = referrals.filter((r) => r.status === 'ready_for_review').length

  function handlePacketFile(event: ChangeEvent<HTMLInputElement>) {
    setPacketFile(event.target.files?.[0] ?? null)
  }

  async function createReferral(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setBusy(true)
    setError('')
    try {
      setBusyStep('Creating referral…')
      let referral = await api.createReferral(newReferral)
      if (packetFile) {
        setBusyStep('Reading packet and extracting facts… this can take a minute.')
        await api.uploadDocument(referral.id, packetFile)
        referral = await api.getReferral(referral.id)
      }
      setReferrals((prev) => [referral, ...prev])
      setFilter('all')
      setQuery('')
      setFormOpen(false)
      setNewReferral(emptyForm)
      setPacketFile(null)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Failed to create referral')
    } finally {
      setBusy(false)
      setBusyStep('')
    }
  }

  return <div className="min-h-screen bg-background lg:flex">
    <aside className="hidden w-[234px] shrink-0 flex-col border-r bg-white px-4 py-6 lg:sticky lg:top-0 lg:flex lg:h-screen lg:overflow-y-auto">
      <div className="flex items-center gap-2.5 px-2">
        <img src={logo} alt="" className="h-7 w-auto"/>
        <div className="text-[17px] font-semibold tracking-tight">Referral<span className="text-primary">Flow</span></div>
      </div>
      <p className="mb-3 mt-12 px-3 text-[10px] font-bold uppercase tracking-[0.14em] text-muted-foreground">Workspace</p>
      <div className="flex items-center gap-2 rounded-lg bg-primary/10 px-3 py-2.5 text-sm font-semibold text-primary"><LayoutDashboard className="size-4"/>Referral intake</div>
      <div className="mt-auto">
        <ProfileMenu/>
      </div>
    </aside>

    <main className="min-w-0 flex-1">
      <header className="flex h-[66px] items-center justify-between border-b bg-white px-5 sm:px-8">
        <div className="flex items-center gap-2 text-sm font-medium"><span className="lg:hidden text-primary">ReferralFlow</span><span className="hidden text-muted-foreground lg:inline">Workspace</span><ChevronRight className="hidden size-3.5 text-muted-foreground lg:inline"/>Referral intake</div>
        <div className="flex items-center gap-2 text-xs text-muted-foreground"><span className="size-2 rounded-full bg-emerald-500"/>OC Impact Lab · Prototype</div>
      </header>
      <div className="mx-auto max-w-[1200px] space-y-6 p-5 sm:p-8">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div><div className="mb-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-primary">Intake operations</div><h1 className="text-3xl font-semibold tracking-tight">Your referral queue</h1><p className="mt-2 text-sm text-muted-foreground">Every packet you're working, with its extraction status. Click a case to open its workspace.</p></div>
          <Button onClick={() => setFormOpen(true)}><Plus/> New referral</Button>
        </div>

        {error && <div role="alert" className="flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-800"><AlertCircle className="mt-0.5 size-4 shrink-0"/><div><b>Something went wrong.</b> {error}</div><Button size="sm" variant="outline" onClick={() => window.location.reload()} className="ml-auto">Retry</Button></div>}
        <div className="grid gap-4 sm:grid-cols-3">
          <Card><CardContent className="flex items-center justify-between p-5"><div><p className="text-xs font-medium text-muted-foreground">Total referrals</p><p className="mt-2 text-3xl font-semibold tabular-nums">{referrals.length}</p><p className="mt-1 text-xs text-muted-foreground">All received cases</p></div><div className="rounded-xl bg-slate-100 p-3 text-slate-600"><ClipboardList className="size-5"/></div></CardContent></Card>
          <Card><CardContent className="flex items-center justify-between p-5"><div><p className="text-xs font-medium text-muted-foreground">Needs information</p><p className="mt-2 text-3xl font-semibold tabular-nums">{needsInfo}</p><p className="mt-1 text-xs text-amber-700">Waiting for clarification</p></div><div className="rounded-xl bg-amber-50 p-3 text-amber-700"><Clock3 className="size-5"/></div></CardContent></Card>
          <Card><CardContent className="flex items-center justify-between p-5"><div><p className="text-xs font-medium text-muted-foreground">Ready for review</p><p className="mt-2 text-3xl font-semibold tabular-nums">{ready}</p><p className="mt-1 text-xs text-emerald-700">Awaiting a staff member</p></div><div className="rounded-xl bg-emerald-50 p-3 text-emerald-700"><CheckCircle2 className="size-5"/></div></CardContent></Card>
        </div>

        <Card className="min-w-0 overflow-hidden">
          <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b pb-5"><div><CardTitle>Incoming referrals</CardTitle><CardDescription className="mt-1">Click a referral to open its packet in a new tab.</CardDescription></div><Badge variant="outline">{visible.length} cases</Badge></CardHeader>
          <div className="flex flex-wrap items-center gap-2 border-b px-5 py-4">
            <div className="relative min-w-[185px] flex-1"><Search className="absolute left-3 top-3 size-4 text-muted-foreground"/><Input aria-label="Search referrals" placeholder="Search referrals..." value={query} onChange={(e) => setQuery(e.target.value)} className="pl-9"/></div>
            <div className="flex items-center gap-2"><Filter className="size-4 text-muted-foreground"/><Select value={filter} onValueChange={(value) => setFilter(value as ReferralStatus | 'all')}><SelectTrigger className="w-[166px]" aria-label="Filter referrals"><SelectValue placeholder="All statuses"/></SelectTrigger><SelectContent><SelectItem value="all">All statuses</SelectItem>{statuses.map((status) => <SelectItem key={status.value} value={status.value}>{status.label}</SelectItem>)}</SelectContent></Select></div>
          </div>
          <Table>
            <TableHeader><TableRow><TableHead>Referral</TableHead><TableHead>Hospital</TableHead><TableHead>Status</TableHead><TableHead>Packet</TableHead><TableHead>AI read</TableHead><TableHead>Received</TableHead></TableRow></TableHeader>
            <TableBody>
              {visible.map((r) => <TableRow key={r.id} className="focus-within:bg-muted/50 hover:bg-muted/30">
                <TableCell>
                  <Link to={`/referrals/${r.id}`} target="_blank" rel="noreferrer" className="group block text-left outline-none focus-visible:underline">
                    <span className="font-semibold group-hover:text-primary">{r.patient_alias}</span>
                    <span className="mt-1 block text-xs text-muted-foreground">#{r.id.slice(0, 8)}</span>
                  </Link>
                </TableCell>
                <TableCell className="max-w-[165px] text-muted-foreground"><span className="line-clamp-2">{r.hospital_name}</span></TableCell>
                <TableCell><StatusBadge status={r.status}/></TableCell>
                <TableCell><PacketStatusBadge referral={r}/></TableCell>
                <TableCell><AiDecisionBadge referral={r}/></TableCell>
                <TableCell className="whitespace-nowrap text-xs text-muted-foreground">{formatDate(r.created_at)}</TableCell>
              </TableRow>)}
              {loading && <TableRow><TableCell colSpan={6} className="h-28 text-center text-sm text-muted-foreground"><LoaderCircle className="mr-2 inline size-4 animate-spin"/>Loading referrals...</TableCell></TableRow>}
              {!loading && visible.length === 0 && <TableRow><TableCell colSpan={6} className="h-28 text-center text-sm text-muted-foreground">No matching referrals.</TableCell></TableRow>}
            </TableBody>
          </Table>
          <div className="flex items-center justify-between border-t px-5 py-3 text-xs text-muted-foreground"><span>Showing {visible.length} of {referrals.length} referrals</span></div>
        </Card>

        <footer className="flex flex-wrap justify-between gap-2 border-t pt-5 text-xs text-muted-foreground"><span>ReferralFlow · Hackathon prototype</span><span>No PHI, authentication, or production security controls</span></footer>
      </div>
    </main>

    <Dialog open={formOpen} onOpenChange={(open) => { if (!busy) { setFormOpen(open); if (!open) setPacketFile(null) } }}>
      <DialogContent>
        <DialogHeader><DialogTitle>New referral</DialogTitle><DialogDescription>Create a referral and, optionally, attach its packet now so extraction starts right away. Do not enter real patient information.</DialogDescription></DialogHeader>
        <form className="mt-5 space-y-4" onSubmit={createReferral}>
          <div className="space-y-2"><Label htmlFor="patient-alias">Patient Name</Label><Input id="patient-alias" required minLength={2} maxLength={80} value={newReferral.patient_alias} onChange={(e) => setNewReferral((p) => ({ ...p, patient_alias: e.target.value }))} placeholder="Patient A"/></div>
          <div className="space-y-2"><Label htmlFor="hospital">Hospital</Label><Input id="hospital" required minLength={2} maxLength={120} value={newReferral.hospital_name} onChange={(e) => setNewReferral((p) => ({ ...p, hospital_name: e.target.value }))} placeholder="Example Hospital"/></div>
          <div className="space-y-2"><Label htmlFor="reason">Reason for referral</Label><Textarea id="reason" required minLength={2} maxLength={3000} rows={3} value={newReferral.reason} onChange={(e) => setNewReferral((p) => ({ ...p, reason: e.target.value }))} placeholder="Recovery needs and outstanding documentation..."/></div>
          <div className="space-y-2">
            <Label>Referral packet (PDF)</Label>
            {packetFile ? (
              <div className="flex items-center gap-2 rounded-md border px-3 py-2 text-sm">
                <FileText className="size-4 shrink-0 text-muted-foreground"/>
                <span className="min-w-0 flex-1 truncate">{packetFile.name}</span>
                <button type="button" onClick={() => setPacketFile(null)} className="shrink-0 text-muted-foreground hover:text-foreground" aria-label="Remove file"><X className="size-4"/></button>
              </div>
            ) : (
              <label className="flex cursor-pointer items-center gap-2 rounded-md border border-dashed px-3 py-2 text-sm text-muted-foreground hover:border-primary hover:text-primary">
                <input type="file" accept="application/pdf" className="hidden" onChange={handlePacketFile}/>
                <Paperclip className="size-4"/> Attach a PDF (optional)
              </label>
            )}
          </div>
          <DialogFooter className="flex-col items-stretch gap-2 sm:flex-row sm:items-center">
            {busy && busyStep && <p className="text-xs text-muted-foreground sm:mr-auto">{busyStep}</p>}
            <Button type="button" variant="outline" onClick={() => setFormOpen(false)} disabled={busy}>Cancel</Button>
            <Button type="submit" disabled={busy}>{busy ? <LoaderCircle className="animate-spin"/> : <Plus/>}{packetFile ? 'Create & extract' : 'Create referral'}</Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  </div>
}

// Placeholder only — this prototype has no real authentication.
function ProfileMenu() {
  const [open, setOpen] = useState(false)
  const ref = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!open) return
    function handleClick(e: MouseEvent) {
      if (ref.current && !ref.current.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', handleClick)
    return () => document.removeEventListener('mousedown', handleClick)
  }, [open])

  return (
    <div ref={ref} className="relative mt-3">
      <button
        type="button"
        onClick={() => setOpen((v) => !v)}
        className="flex w-full items-center gap-2.5 rounded-lg px-2 py-2 text-left hover:bg-muted/60"
      >
        <span className="flex size-8 shrink-0 items-center justify-center rounded-full bg-primary/10 text-sm font-semibold text-primary">A</span>
        <span className="min-w-0 flex-1">
          <span className="block truncate text-sm font-semibold">Hi, Alice</span>
          <span className="block truncate text-xs text-muted-foreground">Care Coordinator</span>
        </span>
        <ChevronsUpDown className="size-3.5 shrink-0 text-muted-foreground"/>
      </button>
      {open && (
        <div className="absolute inset-x-0 bottom-full z-20 mb-1.5 overflow-hidden rounded-lg border bg-white py-1 shadow-lg">
          <div className="border-b px-3 py-2 text-xs text-muted-foreground">Signed in as <span className="font-medium text-foreground">alice@illuminationhh.org</span></div>
          <button type="button" onClick={() => setOpen(false)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm hover:bg-muted/60"><Settings className="size-4 text-muted-foreground"/>Settings</button>
          <button type="button" onClick={() => setOpen(false)} className="flex w-full items-center gap-2 px-3 py-2 text-left text-sm text-red-700 hover:bg-red-50"><LogOut className="size-4"/>Sign out</button>
        </div>
      )}
    </div>
  )
}
