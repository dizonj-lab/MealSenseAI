import { useEffect, useRef, useState } from 'react'
import { X } from 'lucide-react'

/** The narrated demo video. It lives on the portfolio site (folio), not in the app or its image:
 *  folio serves /media/ with CORS. Made with demo/run.sh; see demo/README.md. */
export const DEMO = {
  src: 'https://folio.xtangent.ai/media/mealsenseai-demo.mp4',
  captions: 'https://folio.xtangent.ai/media/mealsenseai-demo.vtt',
  page: 'https://folio.xtangent.ai/demo/mealsenseai/',
  title: 'MealSenseAI demo',
  length: '4 min',
}

const EVENT = 'mealsense-open-demo'
/** Open the demo player from anywhere on the page (one <DemoDialog /> is mounted per shell). */
export const openDemo = () => window.dispatchEvent(new Event(EVENT))

export function PlayIcon({ className = 'size-4' }: { className?: string }) {
  return <svg aria-hidden="true" viewBox="0 0 16 16" className={`${className} fill-current`}><path d="M4 2.8v10.4a.6.6 0 0 0 .9.5l8.3-5.2a.6.6 0 0 0 0-1L4.9 2.3a.6.6 0 0 0-.9.5z" /></svg>
}

/** The player, in a dialog over the page. The video loads only when opened, starts playing, and stops when
 *  closed (the element is removed). Escape, the close button or a click outside closes it. The video carries no
 *  crossOrigin, so it plays as plain media whatever the CDN does with CORS headers; the subtitles are fetched
 *  separately and handed to the track as a blob, and the video plays without them if that fails. If the video
 *  cannot load at all, folio's own player is offered instead. */
export function DemoDialog() {
  const [open, setOpen] = useState(false)
  const [captions, setCaptions] = useState<string | null>(null)
  const [failed, setFailed] = useState(false)
  const close = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    const show = () => setOpen(true)
    window.addEventListener(EVENT, show)
    return () => window.removeEventListener(EVENT, show)
  }, [])

  useEffect(() => {
    if (!open) return
    close.current?.focus()
    const onKey = (e: KeyboardEvent) => { if (e.key === 'Escape') setOpen(false) }
    window.addEventListener('keydown', onKey)
    let url: string | null = null, cancelled = false
    fetch(DEMO.captions)
      .then(r => (r.ok ? r.text() : Promise.reject(new Error(String(r.status)))))
      .then(text => { if (!cancelled) { url = URL.createObjectURL(new Blob([text], { type: 'text/vtt' })); setCaptions(url) } })
      .catch(() => {})
    return () => {
      window.removeEventListener('keydown', onKey)
      cancelled = true
      if (url) URL.revokeObjectURL(url)
      setCaptions(null); setFailed(false)
    }
  }, [open])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-3 sm:p-8">
      <div aria-hidden="true" className="absolute inset-0 bg-slate-950/70" onClick={() => setOpen(false)} />
      <div role="dialog" aria-modal="true" aria-label={DEMO.title} className="card relative w-full max-w-5xl overflow-hidden bg-white p-0">
        <div className="flex items-center justify-between px-4 py-2.5">
          <span className="text-sm font-semibold text-slate-800">{DEMO.title}</span>
          <button ref={close} type="button" aria-label="Close the demo" onClick={() => setOpen(false)}
            className="size-9 grid place-items-center rounded-full text-slate-500 hover:bg-slate-100"><X className="size-5" /></button>
        </div>
        {failed ? (
          <div className="aspect-video w-full flex flex-col items-center justify-center gap-3 bg-slate-50 p-6 text-center">
            <p className="text-sm text-slate-500">The video could not load here.</p>
            <a href={DEMO.page} target="_blank" rel="noopener" className="text-sm font-medium text-brand-700 underline underline-offset-4">Watch it on folio.xtangent.ai</a>
          </div>
        ) : (
          <video data-testid="demo-video" src={DEMO.src} controls autoPlay playsInline preload="metadata"
            onError={() => setFailed(true)} className="block aspect-video w-full bg-black">
            {captions && <track kind="captions" src={captions} srcLang="en" label="English" default />}
          </video>
        )}
        <p className="px-4 py-2 text-xs text-slate-500">Wei Ming and his meals are fictional. Educational estimates only, not medical advice.</p>
      </div>
    </div>
  )
}
