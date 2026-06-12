import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import {
  ArrowLeft,
  ChevronDown,
  LayoutDashboard,
  LogOut,
  User as UserIcon,
  Award,
} from 'lucide-react'
import { api } from '../lib/api'
import type { User } from '../types'

interface AppHeaderProps {
  user: User | null
  /** Optional content rendered next to the logo (e.g. problem title). */
  center?: ReactNode
  /** Optional back link rendered before the logo. */
  backTo?: { to: string; label: string }
}

export default function AppHeader({ user, center, backTo }: AppHeaderProps) {
  const navigate = useNavigate()
  const [menuOpen, setMenuOpen] = useState(false)
  const [isSigningOut, setIsSigningOut] = useState(false)
  const menuRef = useRef<HTMLDivElement>(null)

  // Close dropdown on outside click
  useEffect(() => {
    if (!menuOpen) return
    const onClick = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setMenuOpen(false)
      }
    }
    document.addEventListener('mousedown', onClick)
    return () => document.removeEventListener('mousedown', onClick)
  }, [menuOpen])

  const handleSignOut = async () => {
    setIsSigningOut(true)
    try {
      await api.logout()
    } catch {
      // Token may already be invalid — sign out locally regardless
    }
    localStorage.removeItem('pf_token')
    navigate('/login', { replace: true })
  }

  return (
    <header className="h-11 flex items-center justify-between px-4 bg-[#161b22] border-b border-[#30363d] shrink-0">
      <div className="flex items-center gap-2 min-w-0">
        {backTo && (
          <Link
            to={backTo.to}
            className="flex items-center gap-1 text-xs text-[#8b949e] hover:text-[#e6edf3] transition-colors mr-1 shrink-0"
          >
            <ArrowLeft size={14} />
            {backTo.label}
          </Link>
        )}
        <Link to="/dashboard" className="font-bold text-[#58a6ff] text-sm shrink-0">
          ProofForge
        </Link>
        {center && (
          <>
            <span className="text-[#30363d]">·</span>
            {center}
          </>
        )}
      </div>

      {user && (
        <div className="relative" ref={menuRef}>
          <button
            type="button"
            onClick={() => setMenuOpen((v) => !v)}
            className="flex items-center gap-2 text-xs text-[#8b949e] hover:text-[#e6edf3] transition-colors py-1 px-1.5 rounded hover:bg-[#1c2128]"
          >
            {user.avatar_url ? (
              <img src={user.avatar_url} alt="" className="w-6 h-6 rounded-full" />
            ) : (
              <UserIcon size={16} />
            )}
            <span>{user.github_login}</span>
            <ChevronDown size={12} />
          </button>

          {menuOpen && (
            <div className="absolute right-0 top-full mt-1 w-48 bg-[#1c2128] border border-[#30363d] rounded-lg shadow-lg py-1 z-50">
              <Link
                to="/dashboard"
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs text-[#e6edf3] hover:bg-[#30363d] transition-colors"
              >
                <LayoutDashboard size={13} />
                Dashboard
              </Link>
              <Link
                to={`/p/${user.github_login}`}
                onClick={() => setMenuOpen(false)}
                className="flex items-center gap-2 px-3 py-2 text-xs text-[#e6edf3] hover:bg-[#30363d] transition-colors"
              >
                <Award size={13} />
                My Portfolio
              </Link>
              <div className="border-t border-[#30363d] my-1" />
              <button
                type="button"
                onClick={handleSignOut}
                disabled={isSigningOut}
                className="flex items-center gap-2 w-full px-3 py-2 text-xs text-[#f85149] hover:bg-[#30363d] transition-colors disabled:opacity-50"
              >
                <LogOut size={13} />
                {isSigningOut ? 'Signing out...' : 'Sign out'}
              </button>
            </div>
          )}
        </div>
      )}
    </header>
  )
}
