import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import { DemoDialog, openDemo } from './DemoVideo'

/** Header + footer shared by the public pages (landing, privacy, terms, contact). */
export default function PublicShell({ children }: { children: ReactNode }) {
  return (
    <div className="public min-h-full flex flex-col">
      <header className="w-full max-w-5xl mx-auto flex items-center gap-2 px-5 sm:px-8 h-16">
        <Link to="/" className="flex items-center gap-2 font-semibold tracking-tight mr-auto"><img src="/favicon.svg" className="size-7" alt="" />MealSenseAI</Link>
        <a href="/#how" className="hidden sm:inline px-3 py-2 text-sm" style={{ color: 'var(--p-muted)' }}>How It Works</a>
        <button type="button" onClick={openDemo} className="hidden sm:inline px-3 py-2 text-sm" style={{ color: 'var(--p-muted)' }}>Watch Demo</button>
        <Link to="/login" className="px-3 py-2 text-sm font-medium">Sign In</Link>
        <Link to="/register" className="rounded-lg px-4 py-2 text-sm font-medium text-white" style={{ background: 'var(--p-primary)' }}>Get Started</Link>
      </header>
      <main className="flex-1">{children}</main>
      <DemoDialog />
      <footer className="w-full max-w-5xl mx-auto px-5 sm:px-8 py-8 flex flex-wrap items-center gap-x-6 gap-y-2 text-sm border-t" style={{ borderColor: 'var(--p-border)', color: 'var(--p-muted)' }}>
        <span className="mr-auto">© MealSenseAI · Created by <Link to="/creator" className="underline">Joselito Villanueva Dizon</Link></span>
        <Link to="/privacy">Privacy Policy</Link><Link to="/terms">Terms of Service</Link><Link to="/contact">Contact</Link>
      </footer>
    </div>
  )
}
