import { useEffect, useState } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { getStrategy, listSchedules, type ScheduleJob } from '../api'
import ChatPanel from '../components/ChatPanel'
import PortfolioSidebar from '../components/PortfolioSidebar'
import StrategyDocSidebar from '../components/StrategyDocSidebar'
import { useAuth } from '../AuthContext'

function Logo() {
  return (
    <span style={{
      fontWeight: 700, fontSize: 14, letterSpacing: -0.5,
      background: 'linear-gradient(135deg, #e8926a, #d97757)',
      WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
    }}>aipolymarket</span>
  )
}

export default function StrategyPage() {
  const { sid } = useParams<{ sid: string }>()
  const navigate = useNavigate()
  const { isGuest, auth, logout } = useAuth()
  const [schedules, setSchedules] = useState<ScheduleJob[]>([])
  const [strategyName, setStrategyName] = useState('')

  useEffect(() => {
    if (!sid) return
    listSchedules(sid).then(setSchedules).catch(() => {})
    getStrategy(sid).then(s => { if (s) setStrategyName(s.name) }).catch(() => {})
  }, [sid])

  if (!sid) return null

  return (
    <div style={{ height: '100vh', display: 'flex', flexDirection: 'column', overflow: 'hidden' }}>

      {/* Top bar */}
      <div style={{
        background: 'var(--surface)', borderBottom: '1px solid var(--border)',
        padding: '0 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0, height: 48,
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {/* Back */}
          <button
            onClick={() => navigate('/')}
            style={{
              background: 'none', border: 'none', color: 'var(--t2)', fontSize: 13,
              cursor: 'pointer', padding: '4px 6px', borderRadius: 6,
              fontFamily: 'var(--font)', display: 'flex', alignItems: 'center', gap: 4,
              transition: 'color 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--t1)' }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--t2)' }}
          >
            ← <Logo />
          </button>

          <span style={{ color: 'var(--border-2)' }}>/</span>

          {/* Strategy name */}
          <span style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)' }}>
            {strategyName || sid}
          </span>

          {strategyName && strategyName !== sid && (
            <span style={{ fontSize: 11, color: 'var(--t3)' }}>{sid}</span>
          )}

          {schedules.length > 0 && (
            <span className="tag" style={{ color: 'var(--purple)', borderColor: 'var(--purple-dim)' }}>
              ⏰ {schedules.length} 个定时任务
            </span>
          )}
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          {isGuest && (
            <span style={{
              fontSize: 10, fontWeight: 600, letterSpacing: 0.6,
              color: 'var(--t3)', background: 'var(--bg)',
              border: '1px solid var(--border)', borderRadius: 5,
              padding: '2px 7px', textTransform: 'uppercase',
            }}>访客</span>
          )}
          <span style={{ fontSize: 11, color: 'var(--t3)' }}>{auth?.username}</span>
          <button
            onClick={logout}
            style={{
              background: 'none', border: '1px solid var(--border)', borderRadius: 6,
              color: 'var(--t3)', fontSize: 11, padding: '3px 9px',
              cursor: 'pointer', fontFamily: 'var(--font)', transition: 'all 0.15s',
            }}
            onMouseEnter={e => { e.currentTarget.style.color = 'var(--t1)'; e.currentTarget.style.borderColor = 'var(--border-2)' }}
            onMouseLeave={e => { e.currentTarget.style.color = 'var(--t3)'; e.currentTarget.style.borderColor = 'var(--border)' }}
          >退出</button>
        </div>
      </div>

      {/* Three-panel layout */}
      <div style={{
        flex: 1, display: 'grid',
        gridTemplateColumns: '230px 1fr 252px',
        overflow: 'hidden',
      }}>
        <div style={{ overflow: 'hidden' }}>
          <PortfolioSidebar sid={sid} />
        </div>
        <div style={{ overflow: 'hidden', borderLeft: '1px solid var(--border)' }}>
          <ChatPanel sid={sid} readonly={isGuest} />
        </div>
        <div style={{ overflow: 'hidden' }}>
          <StrategyDocSidebar sid={sid} />
        </div>
      </div>
    </div>
  )
}
