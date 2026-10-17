import { useEffect, useRef, useState } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { AlertCircle, CheckCircle2, CircleHelp, FileText, LoaderCircle, XCircle } from 'lucide-react'
import type { CriterionResult, CriterionStatus } from '@/types'
import { Badge } from '@/components/ui/badge'
import { Card, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

const statusMeta: Record<CriterionStatus, { label: string; className: string; iconClass: string; icon: typeof CheckCircle2 }> = {
  met: { iconClass: 'text-emerald-600', label: 'Met', className: 'border-emerald-200 bg-emerald-50 text-emerald-800', icon: CheckCircle2 },
  not_met: { iconClass: 'text-red-600', label: 'Not met', className: 'border-red-200 bg-red-50 text-red-700', icon: XCircle },
  missing: { iconClass: 'text-amber-600', label: 'Missing', className: 'border-amber-200 bg-amber-50 text-amber-800', icon: AlertCircle },
  unclear: { iconClass: 'text-sky-600', label: 'Unclear', className: 'border-sky-200 bg-sky-50 text-sky-700', icon: CircleHelp },
}

export function PacketReview({ fileUrl, criteria }: { fileUrl: string; criteria: CriterionResult[] }) {
  const viewerRef = useRef<HTMLDivElement>(null)
  const pageRefs = useRef<(HTMLDivElement | null)[]>([])
  const [numPages, setNumPages] = useState(0)
  const [pageWidth, setPageWidth] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [activeId, setActiveId] = useState<string | null>(null)
  const [highlightPage, setHighlightPage] = useState<number | null>(null)
  // Height/width ratio per page, so unrendered pages reserve space and jump offsets stay accurate
  const [pageRatios, setPageRatios] = useState<Record<number, number>>({})

  useEffect(() => {
    const viewer = viewerRef.current
    if (!viewer) return
    const observer = new ResizeObserver(([entry]) => setPageWidth(Math.floor(entry.contentRect.width) - 32))
    observer.observe(viewer)
    return () => observer.disconnect()
  }, [])

  function goToPage(page: number) {
    const viewer = viewerRef.current
    const target = pageRefs.current[page - 1]
    if (!viewer || !target) return
    viewer.scrollTo({ top: target.offsetTop - 16, behavior: 'smooth' })
    setHighlightPage(page)
    window.setTimeout(() => setHighlightPage((p) => (p === page ? null : p)), 1500)
  }

  function trackCurrentPage() {
    const viewer = viewerRef.current
    if (!viewer) return
    const marker = viewer.scrollTop + viewer.clientHeight / 3
    let page = 1
    pageRefs.current.forEach((el, i) => { if (el && el.offsetTop <= marker) page = i + 1 })
    setCurrentPage(page)
  }

  const counts = criteria.reduce((acc, c) => ({ ...acc, [c.status]: (acc[c.status] ?? 0) + 1 }), {} as Partial<Record<CriterionStatus, number>>)

  return <Card className="min-w-0 overflow-hidden">
    <CardHeader className="flex flex-row flex-wrap items-center justify-between gap-3 border-b pb-5">
      <div><CardTitle>Packet review</CardTitle><CardDescription className="mt-1">Select a criterion to jump to its evidence in the referral packet. Results are mocked.</CardDescription></div>
      <div className="flex flex-wrap gap-2">{(Object.keys(statusMeta) as CriterionStatus[]).map((s) => counts[s] ? <Badge key={s} variant="outline" className={statusMeta[s].className}>{counts[s]} {statusMeta[s].label.toLowerCase()}</Badge> : null)}</div>
    </CardHeader>
    <div className="grid lg:grid-cols-[minmax(300px,380px)_1fr]">
      <ul className="max-h-[78vh] divide-y overflow-y-auto border-b lg:border-b-0 lg:border-r">
        {criteria.map((c) => {
          const meta = statusMeta[c.status]
          const Icon = meta.icon
          return <li key={c.id}>
            <button
              data-active={activeId === c.id}
              onClick={() => { setActiveId(c.id); goToPage(c.page) }}
              className="flex w-full gap-3 px-5 py-3.5 text-left outline-none transition-colors hover:bg-muted/50 focus-visible:bg-muted/60 data-[active=true]:bg-primary/[0.06]"
            >
              <Icon className={`mt-0.5 size-4 shrink-0 ${meta.iconClass}`}/>
              <div className="min-w-0 flex-1">
                <div className="flex items-start justify-between gap-2"><span className="text-sm font-semibold">{c.name}</span><span className="shrink-0 text-xs text-muted-foreground tabular-nums">p. {c.page}</span></div>
                <p className="mt-1 text-xs leading-5 text-muted-foreground">{c.evidence}</p>
                <Badge variant="outline" className={`mt-2 ${meta.className}`}>{meta.label}</Badge>
              </div>
            </button>
          </li>
        })}
      </ul>

      <div className="flex min-w-0 flex-col bg-slate-100">
        <div className="flex items-center justify-between border-b bg-white px-4 py-2 text-xs text-muted-foreground">
          <span className="flex items-center gap-1.5"><FileText className="size-3.5"/>{fileUrl.split('/').pop()}</span>
          {numPages > 0 && <span className="tabular-nums">Page {currentPage} of {numPages}</span>}
        </div>
        <div ref={viewerRef} onScroll={trackCurrentPage} className="relative h-[74vh] overflow-y-auto p-4">
          <Document
            file={fileUrl}
            onLoadSuccess={({ numPages }) => setNumPages(numPages)}
            loading={<div className="flex h-40 items-center justify-center text-sm text-muted-foreground"><LoaderCircle className="mr-2 size-4 animate-spin"/>Loading packet...</div>}
            error={<div className="flex h-40 items-center justify-center text-sm text-red-700"><AlertCircle className="mr-2 size-4"/>Could not load {fileUrl}</div>}
          >
            {pageWidth > 0 && Array.from({ length: numPages }, (_, i) => <div
              key={i}
              ref={(el) => { pageRefs.current[i] = el }}
              data-highlight={highlightPage === i + 1}
              style={{ minHeight: pageWidth * (pageRatios[i + 1] ?? 11 / 8.5) }}
              className="mx-auto mb-4 w-fit bg-white shadow-sm ring-primary transition-shadow data-[highlight=true]:ring-4"
            >
              <Page pageNumber={i + 1} width={pageWidth} renderTextLayer={false} renderAnnotationLayer={false} onLoadSuccess={(page) => setPageRatios((r) => ({ ...r, [page.pageNumber]: page.originalHeight / page.originalWidth }))}/>
            </div>)}
          </Document>
        </div>
      </div>
    </div>
  </Card>
}
