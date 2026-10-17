import { useEffect, useRef, useState, type FormEvent } from 'react'
import { Document, Page, pdfjs } from 'react-pdf'
import { AlertCircle, ChevronLeft, ChevronRight, ExternalLink, FileText, LoaderCircle } from 'lucide-react'

pdfjs.GlobalWorkerOptions.workerSrc = new URL('pdfjs-dist/build/pdf.worker.min.mjs', import.meta.url).toString()

/**
 * Renders every page of the packet as a scrollable column of canvases (via react-pdf/pdf.js)
 * instead of embedding the browser's own PDF plugin in an iframe. That gives us real control
 * over "jump to page": scrolling and highlighting a specific page element, rather than relying
 * on an iframe's #page= hash, which Chrome's built-in viewer does not reliably re-navigate to
 * on an already-mounted iframe.
 */
export function PdfViewer({
  fileUrl,
  filename,
  activePage,
  jumpSignal,
}: {
  fileUrl: string
  filename: string
  activePage: number | null
  jumpSignal: number
}) {
  const viewerRef = useRef<HTMLDivElement>(null)
  const pageRefs = useRef<(HTMLDivElement | null)[]>([])
  const [numPages, setNumPages] = useState(0)
  const [pageWidth, setPageWidth] = useState(0)
  const [currentPage, setCurrentPage] = useState(1)
  const [pageInput, setPageInput] = useState('1')
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

  useEffect(() => {
    if (jumpSignal && activePage) goToPage(activePage)
    // jumpSignal is the trigger; activePage is only read when it fires.
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [jumpSignal])

  useEffect(() => {
    setPageInput(String(currentPage))
  }, [currentPage])

  function goToPage(page: number) {
    const viewer = viewerRef.current
    const target = pageRefs.current[page - 1]
    if (!viewer || !target) return
    viewer.scrollTo({ top: target.offsetTop - 16, behavior: 'smooth' })
    setHighlightPage(page)
    window.setTimeout(() => setHighlightPage((p) => (p === page ? null : p)), 1500)
  }

  function step(delta: number) {
    goToPage(Math.min(Math.max(currentPage + delta, 1), numPages))
  }

  function submitPageInput(e: FormEvent) {
    e.preventDefault()
    const page = Math.round(Number(pageInput))
    if (page >= 1 && page <= numPages) goToPage(page)
    else setPageInput(String(currentPage))
  }

  function trackCurrentPage() {
    const viewer = viewerRef.current
    if (!viewer) return
    const marker = viewer.scrollTop + viewer.clientHeight / 3
    let page = 1
    pageRefs.current.forEach((el, i) => { if (el && el.offsetTop <= marker) page = i + 1 })
    setCurrentPage(page)
  }

  return (
    <div className="flex min-w-0 flex-col overflow-hidden rounded-lg border bg-slate-100">
      <div className="flex items-center justify-between gap-3 border-b bg-white px-3 py-2 text-xs text-muted-foreground">
        <span className="flex min-w-0 items-center gap-1.5 truncate"><FileText className="size-3.5 shrink-0" />{filename}</span>
        <a href={fileUrl} target="_blank" rel="noreferrer" className="inline-flex shrink-0 items-center gap-1 font-medium text-primary hover:underline">
          Open in new tab<ExternalLink className="size-3" />
        </a>
      </div>
      {numPages > 0 && (
        <div className="flex items-center justify-center gap-2 border-b bg-white px-3 py-1.5 text-xs text-muted-foreground">
          <button type="button" onClick={() => step(-1)} disabled={currentPage <= 1} aria-label="Previous page" className="rounded p-1 hover:bg-muted/60 disabled:opacity-30">
            <ChevronLeft className="size-3.5" />
          </button>
          <form onSubmit={submitPageInput} className="flex items-center gap-1.5">
            <span>Page</span>
            <input
              type="text"
              inputMode="numeric"
              value={pageInput}
              onChange={(e) => setPageInput(e.target.value)}
              onFocus={(e) => e.target.select()}
              className="h-6 w-10 rounded border text-center tabular-nums focus:border-primary focus:outline-none"
            />
            <span>of {numPages}</span>
          </form>
          <button type="button" onClick={() => step(1)} disabled={currentPage >= numPages} aria-label="Next page" className="rounded p-1 hover:bg-muted/60 disabled:opacity-30">
            <ChevronRight className="size-3.5" />
          </button>
        </div>
      )}
      <div ref={viewerRef} onScroll={trackCurrentPage} className="relative h-[75vh] min-h-[520px] overflow-y-auto p-4">
        <Document
          file={fileUrl}
          onLoadSuccess={({ numPages }) => setNumPages(numPages)}
          loading={<div className="flex h-40 items-center justify-center text-sm text-muted-foreground"><LoaderCircle className="mr-2 size-4 animate-spin" />Loading packet…</div>}
          error={<div className="flex h-40 items-center justify-center text-sm text-red-700"><AlertCircle className="mr-2 size-4" />Could not load the PDF.</div>}
        >
          {pageWidth > 0 && Array.from({ length: numPages }, (_, i) => (
            <div
              key={i}
              ref={(el) => { pageRefs.current[i] = el }}
              data-highlight={highlightPage === i + 1}
              style={{ minHeight: pageWidth * (pageRatios[i + 1] ?? 11 / 8.5) }}
              className="mx-auto mb-4 w-fit bg-white shadow-sm ring-primary transition-shadow data-[highlight=true]:ring-4"
            >
              <Page
                pageNumber={i + 1}
                width={pageWidth}
                renderTextLayer={false}
                renderAnnotationLayer={false}
                onLoadSuccess={(page) => setPageRatios((r) => ({ ...r, [page.pageNumber]: page.originalHeight / page.originalWidth }))}
              />
            </div>
          ))}
        </Document>
      </div>
    </div>
  )
}
