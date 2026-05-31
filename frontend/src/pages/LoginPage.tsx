import { useState, type FormEvent } from 'react'
import { useAuth } from '../AuthContext'

export default function LoginPage() {
  const { login } = useAuth()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [shaking, setShaking] = useState(false)

  function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    const ok = login(username, password)
    if (!ok) {
      setError('用户名或密码错误')
      setShaking(true)
      setTimeout(() => setShaking(false), 500)
    }
  }

  return (
    <div style={{
      minHeight: '100vh',
      background: 'var(--bg)',
      display: 'flex',
      alignItems: 'center',
      justifyContent: 'center',
      fontFamily: 'var(--font)',
    }}>

      {/* Background glow */}
      <div style={{
        position: 'fixed', inset: 0, pointerEvents: 'none', zIndex: 0,
        background: 'radial-gradient(ellipse 700px 500px at 50% 40%, rgba(217,119,87,0.07) 0%, transparent 70%)',
      }} />

      <div style={{
        position: 'relative', zIndex: 1,
        width: '100%', maxWidth: 380,
        padding: '0 20px',
      }}>

        {/* Logo area */}
        <div style={{ textAlign: 'center', marginBottom: 40 }}>
          <div style={{
            width: 52, height: 52, borderRadius: '50%', margin: '0 auto 16px',
            background: 'linear-gradient(140deg, #e8926a 0%, #c05535 100%)',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: 22, fontWeight: 700, color: 'white', letterSpacing: -1,
            boxShadow: '0 8px 24px rgba(217,119,87,0.35)',
          }}>P</div>
          <div style={{
            fontSize: 22, fontWeight: 700, letterSpacing: -0.8,
            background: 'linear-gradient(135deg, #e8926a, #d97757)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
            marginBottom: 6,
          }}>aipolymarket</div>
          <div style={{ fontSize: 13, color: 'var(--t3)' }}>
            Polymarket 自动交易系统
          </div>
        </div>

        {/* Card */}
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderRadius: 14,
          padding: '28px 28px',
          boxShadow: '0 4px 32px rgba(0,0,0,0.25)',
          animation: shaking ? 'shake 0.5s ease' : undefined,
        }}>

          <div style={{ fontSize: 16, fontWeight: 600, color: 'var(--t1)', marginBottom: 20 }}>
            登录
          </div>

          <form onSubmit={handleSubmit} style={{ display: 'flex', flexDirection: 'column', gap: 14 }}>
            <div>
              <label style={{ fontSize: 12, color: 'var(--t2)', display: 'block', marginBottom: 6, fontWeight: 500 }}>
                用户名
              </label>
              <input
                type="text"
                value={username}
                onChange={e => { setUsername(e.target.value); setError('') }}
                autoComplete="username"
                autoFocus
                placeholder="admin 或 guest"
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: 'var(--bg)',
                  border: `1px solid ${error ? 'rgba(245,90,90,0.5)' : 'var(--border-2)'}`,
                  borderRadius: 8, padding: '9px 12px',
                  color: 'var(--t1)', fontSize: 13, fontFamily: 'var(--font)',
                  outline: 'none', transition: 'border-color 0.15s',
                }}
                onFocus={e => { if (!error) e.currentTarget.style.borderColor = 'var(--accent)' }}
                onBlur={e => { e.currentTarget.style.borderColor = error ? 'rgba(245,90,90,0.5)' : 'var(--border-2)' }}
              />
            </div>

            <div>
              <label style={{ fontSize: 12, color: 'var(--t2)', display: 'block', marginBottom: 6, fontWeight: 500 }}>
                密码
              </label>
              <input
                type="password"
                value={password}
                onChange={e => { setPassword(e.target.value); setError('') }}
                autoComplete="current-password"
                placeholder="••••••••"
                style={{
                  width: '100%', boxSizing: 'border-box',
                  background: 'var(--bg)',
                  border: `1px solid ${error ? 'rgba(245,90,90,0.5)' : 'var(--border-2)'}`,
                  borderRadius: 8, padding: '9px 12px',
                  color: 'var(--t1)', fontSize: 13, fontFamily: 'var(--font)',
                  outline: 'none', transition: 'border-color 0.15s',
                }}
                onFocus={e => { if (!error) e.currentTarget.style.borderColor = 'var(--accent)' }}
                onBlur={e => { e.currentTarget.style.borderColor = error ? 'rgba(245,90,90,0.5)' : 'var(--border-2)' }}
              />
            </div>

            {/* Error */}
            {error && (
              <div style={{
                fontSize: 12, color: 'var(--red)',
                background: 'var(--red-dim)',
                border: '1px solid rgba(245,90,90,0.22)',
                borderRadius: 7, padding: '7px 11px',
                display: 'flex', alignItems: 'center', gap: 6,
              }}>
                <span>✕</span> {error}
              </div>
            )}

            <button
              type="submit"
              className="btn-primary"
              style={{
                marginTop: 4, padding: '10px 0', fontSize: 14, fontWeight: 600,
                borderRadius: 9, cursor: 'pointer', letterSpacing: 0.2,
              }}
            >
              登录
            </button>
          </form>
        </div>

        {/* Hint */}
        <div style={{
          marginTop: 20, textAlign: 'center', fontSize: 12, color: 'var(--t3)',
          lineHeight: 1.7,
        }}>
          <span style={{ opacity: 0.6 }}>
            访客账号（guest）仅可查看，无法操作
          </span>
        </div>
      </div>

      <style>{`
        @keyframes shake {
          0%, 100% { transform: translateX(0); }
          20%       { transform: translateX(-6px); }
          40%       { transform: translateX(6px); }
          60%       { transform: translateX(-4px); }
          80%       { transform: translateX(4px); }
        }
      `}</style>
    </div>
  )
}
