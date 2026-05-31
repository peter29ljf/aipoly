import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import { AuthProvider, useAuth } from './AuthContext'
import LoginPage from './pages/LoginPage'
import HomePage from './pages/HomePage'
import StrategyPage from './pages/StrategyPage'
import './App.css'

function ProtectedRoutes() {
  const { auth } = useAuth()
  if (!auth) return <Navigate to="/login" replace />
  return (
    <Routes>
      <Route path="/" element={<HomePage />} />
      <Route path="/s/:sid" element={<StrategyPage />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default function App() {
  return (
    <AuthProvider>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPageGuard />} />
          <Route path="/*" element={<ProtectedRoutes />} />
        </Routes>
      </BrowserRouter>
    </AuthProvider>
  )
}

/** 已登录时访问 /login → 跳首页 */
function LoginPageGuard() {
  const { auth } = useAuth()
  if (auth) return <Navigate to="/" replace />
  return <LoginPage />
}
