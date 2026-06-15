import type { ReactNode } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import LoginPage from './pages/LoginPage'
import AuthCallbackPage from './pages/AuthCallbackPage'
import DashboardPage from './pages/DashboardPage'
import WorkspacePage from './pages/WorkspacePage'
import ReviewPage from './pages/ReviewPage'
import PortfolioPage from './pages/PortfolioPage'
import ProfilePage from './pages/ProfilePage'
import CommunityPage from './pages/CommunityPage'
import CommunityPostPage from './pages/CommunityPostPage'

function PrivateRoute({ children }: { children: ReactNode }) {
  const token = localStorage.getItem('pf_token')
  if (!token) {
    return <Navigate to="/login" replace />
  }
  return <>{children}</>
}

function RootRedirect() {
  const token = localStorage.getItem('pf_token')
  return <Navigate to={token ? '/dashboard' : '/login'} replace />
}

export default function AppRouter() {
  return (
    <Routes>
      <Route path="/" element={<RootRedirect />} />
      <Route path="/login" element={<LoginPage />} />
      <Route path="/auth/callback" element={<AuthCallbackPage />} />
      <Route
        path="/dashboard"
        element={
          <PrivateRoute>
            <DashboardPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/workspace"
        element={
          <PrivateRoute>
            <WorkspacePage />
          </PrivateRoute>
        }
      />
      <Route
        path="/workspace/:slug"
        element={
          <PrivateRoute>
            <WorkspacePage />
          </PrivateRoute>
        }
      />
      <Route
        path="/profile"
        element={
          <PrivateRoute>
            <ProfilePage />
          </PrivateRoute>
        }
      />
      <Route
        path="/review/:submissionId"
        element={
          <PrivateRoute>
            <ReviewPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/community"
        element={
          <PrivateRoute>
            <CommunityPage />
          </PrivateRoute>
        }
      />
      <Route
        path="/community/posts/:postId"
        element={
          <PrivateRoute>
            <CommunityPostPage />
          </PrivateRoute>
        }
      />
      <Route path="/p/:githubLogin" element={<PortfolioPage />} />
      <Route path="*" element={<RootRedirect />} />
    </Routes>
  )
}
