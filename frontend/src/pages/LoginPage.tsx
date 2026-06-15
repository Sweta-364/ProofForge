import { useState } from "react";
import type { ReactNode } from "react";
import { useNavigate } from "react-router-dom";
import {
  Github,
  Code2,
  Award,
  TrendingUp,
  FlaskConical,
  Loader,
} from "lucide-react";
import { api } from "../lib/api";

export default function LoginPage() {
  const navigate = useNavigate();
  const [devLoading, setDevLoading] = useState(false);
  const [devError, setDevError] = useState<string | null>(null);

  // TEMPORARY dev-only bypass — remove before production.
  // Reuses the real /auth/callback route so the genuine post-login flow runs.
  const handleDevLogin = async () => {
    setDevLoading(true);
    setDevError(null);
    try {
      const { access_token } = await api.devLogin();
      navigate(`/auth/callback?token=${access_token}`);
    } catch (err: unknown) {
      setDevError(err instanceof Error ? err.message : "Dev login failed");
      setDevLoading(false);
    }
  };

  return (
    <div className="min-h-screen bg-[#0d1117] flex flex-col items-center justify-center px-4">
      {/* Logo */}
      <div className="mb-8 text-center">
        <div className="flex items-center justify-center gap-3 mb-3">
          <Code2 size={40} className="text-[#58a6ff]" />
          <h1 className="text-4xl font-bold text-[#e6edf3] tracking-tight">
            Proof<span className="text-[#58a6ff]">Forge</span>
          </h1>
        </div>
        <p className="text-[#8b949e] text-lg font-medium">
          Proof of Work. Not Proof of Course.
        </p>
      </div>

      {/* Card */}
      <div className="w-full max-w-md bg-[#161b22] border border-[#30363d] rounded-xl p-8 shadow-2xl">
        <h2 className="text-xl font-semibold text-[#e6edf3] mb-2">
          Welcome back
        </h2>
        <p className="text-[#8b949e] text-sm mb-6">
          Fix real bugs. Earn a cryptographically signed portfolio card.
        </p>

        <a
          href="/api/v1/auth/github"
          className="flex items-center justify-center gap-3 w-full py-3 px-4 bg-[#238636] hover:bg-[#2ea043] text-white font-medium rounded-lg transition-colors"
        >
          <Github size={20} />
          Sign in with GitHub
        </a>

        <p className="text-xs text-[#8b949e] text-center mt-4">
          By signing in, you agree to have your code reviewed by AI.
        </p>

        {/* TEMPORARY: dev-only login bypass — remove before production */}
        {import.meta.env.DEV && (
          <div className="mt-4 pt-4 border-t border-dashed border-[#30363d]">
            <button
              type="button"
              onClick={handleDevLogin}
              disabled={devLoading}
              className="flex items-center justify-center gap-2 w-full py-2 px-4 bg-transparent border border-[#9e6a03] text-[#d29922] hover:bg-[#2d2305] font-medium rounded-lg transition-colors text-sm disabled:opacity-50"
            >
              {devLoading ? (
                <Loader size={16} className="animate-spin" />
              ) : (
                <FlaskConical size={16} />
              )}
              Testing — skip sign in (dev only)
            </button>
            {devError && (
              <p className="text-xs text-[#f85149] text-center mt-2">
                {devError}
              </p>
            )}
          </div>
        )}
      </div>

      {/* How it works */}
      <div className="mt-12 max-w-md w-full">
        <h3 className="text-[#8b949e] text-xs font-semibold uppercase tracking-wider mb-4 text-center">
          How it works
        </h3>
        <div className="space-y-3">
          {[
            {
              step: "01",
              label: "Get a real bug to fix",
              desc: "Real-world broken codebases, not toy examples",
            },
            {
              step: "02",
              label: "Write your fix",
              desc: "Monaco editor, run tests instantly",
            },
            {
              step: "03",
              label: "AI code review",
              desc: "Senior engineer-level feedback on your PR",
            },
            {
              step: "04",
              label: "Earn your card",
              desc: "Cryptographically signed portfolio proof",
            },
          ].map(({ step, label, desc }) => (
            <div key={step} className="flex gap-3 items-start">
              <span className="text-xs font-mono text-[#1f6feb] bg-[#0d2e4d] px-2 py-0.5 rounded shrink-0">
                {step}
              </span>
              <div>
                <p className="text-sm text-[#e6edf3] font-medium">{label}</p>
                <p className="text-xs text-[#8b949e]">{desc}</p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({
  icon,
  value,
  label,
}: {
  icon: ReactNode;
  value: string;
  label: string;
}) {
  return (
    <div className="flex flex-col items-center gap-1 bg-[#161b22] border border-[#30363d] rounded-lg px-3 py-4">
      {icon}
      <span className="text-lg font-bold text-[#e6edf3]">{value}</span>
      <span className="text-xs text-[#8b949e] text-center">{label}</span>
    </div>
  );
}
