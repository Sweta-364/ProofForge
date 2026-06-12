import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { Loader, AlertCircle } from 'lucide-react'
import { api } from '../lib/api'

export default function AuthCallbackPage() {
  const navigate = useNavigate()
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    const params = new URLSearchParams(window.location.search)
    const token = params.get('token')

    if (!token) {
      setError('No token received from GitHub. Authentication failed.')
      return
    }

    localStorage.setItem('pf_token', token)

    api.getMe()
      .then(() => {
        navigate('/dashboard', { replace: true })
      })
      .catch((err: unknown) => {
        localStorage.removeItem('pf_token')
        const message = err instanceof Error ? err.message : 'Authentication failed'
        setError(message)
      })
  }, [navigate])

  if (error) {
    return (
      <div className="min-h-screen bg-[#0d1117] flex items-center justify-center">
        <div className="bg-[#161b22] border border-[#da3633] rounded-xl p-8 max-w-md text-center">
          <AlertCircle size={40} className="text-[#f85149] mx-auto mb-4" />
          <h2 className="text-[#e6edf3] font-semibold text-lg mb-2">Authentication Failed</h2>
          <p className="text-[#8b949e] text-sm mb-6">{error}</p>
          <a
            href="/"
            className="inline-block px-4 py-2 bg-[#238636] hover:bg-[#2ea043] text-white rounded-lg text-sm font-medium transition-colors"
          >
            Try again
          </a>
        </div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-[#0d1117] flex flex-col items-center justify-center gap-4">
      <Loader size={32} className="text-[#58a6ff] animate-spin" />
      <p className="text-[#8b949e] text-sm">Authenticating...</p>
    </div>
  )
}
