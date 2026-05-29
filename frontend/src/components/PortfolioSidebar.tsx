import { useEffect, useState } from 'react'
import {
  listPositions, listAlerts, cancelAlert, listSchedules,
  type Position, type Alert, type ScheduleJob,
} from '../api'

interface Props { sid: string }

type Tab = 'positions' | 'alerts' | 'schedules'

function TabBtn({
  active, onClick, children,
}: { active: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      onClick={onClick}
      style={{
        flex: 1, padding: '8px 4px', fontSize: 11, fontWeight: active ? 600 : 400,
        color: active ? 'var(--t1)' : 'var(--t3)',
        background: 'none', border: 'none',
        borderBottom: active ? '2px solid var(--accent)' : '2px solid transparent',
        cursor: 'pointer', transition: 'all 0.15s', fontFamily: 'var(--font)',
        whiteSpace: 'nowrap',
      }}
    >{children}</button>
  )
}

function Card({ children, accent }: { children: React.ReactNode; accent?: string }) {
  return (
    <div style={{
      background: 'var(--surface-2)', border: '1px solid var(--border)',
      borderLeft: accent ? `3px solid ${accent}` : '1px solid var(--border)',
      borderRadius: 'var(--r-sm)', padding: '10px 12px', marginBottom: 8,
      animation: 'fade-in 0.2s ease',
    }}>
      {children}
    </div>
  )
}

function Empty({ icon, text }: { icon: string; text: string }) {
  return (
    <div style={{
      display: 'flex', flexDirection: 'column', alignItems: 'center',
      gap: 8, marginTop: 40, color: 'var(--t3)',
    }}>
      <div style={{ fontSize: 28, opacity: 0.5 }}>{icon}</div>
      <div style={{ fontSize: 12 }}>{text}</div>
    </div>
  )
}

export default function PortfolioSidebar({ sid }: Props) {
  const [positions, setPositions] = useState<Position[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [schedules, setSchedules] = useState<ScheduleJob[]>([])
  const [tab, setTab] = useState<Tab>('positions')

  const loadPositions = () => listPositions(sid).then(setPositions).catch(() => {})
  const loadAlerts = () => listAlerts(sid).then(setAlerts).catch(() => {})
  const loadSchedules = () => listSchedules(sid).then(setSchedules).catch(() => setSchedules([]))

  useEffect(() => {
    loadPositions(); loadAlerts(); loadSchedules()
    const t = setInterval(() => { loadPositions(); loadAlerts(); loadSchedules() }, 15000)
    return () => clearInterval(t)
  }, [sid])

  async function handleCancelAlert(id: number) {
    await cancelAlert(sid, id)
    loadAlerts()
  }

  const activeAlerts = alerts.filter(a => a.status === 'active')

  return (
    <div style={{
      height: '100%', display: 'flex', flexDirection: 'column',
      background: 'var(--surface)', borderRight: '1px solid var(--border)',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 14px 0', borderBottom: '1px solid var(--border)', flexShrink: 0,
      }}>
        <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--t2)', letterSpacing: 0.5, marginBottom: 8 }}>
          仓位面板
        </div>
        <div style={{ display: 'flex' }}>
          <TabBtn active={tab === 'positions'} onClick={() => setTab('positions')}>
            持仓{positions.length > 0 ? ` (${positions.length})` : ''}
          </TabBtn>
          <TabBtn active={tab === 'alerts'} onClick={() => setTab('alerts')}>
            警报{activeAlerts.length > 0 ? ` (${activeAlerts.length})` : ''}
          </TabBtn>
          <TabBtn active={tab === 'schedules'} onClick={() => setTab('schedules')}>
            定时{schedules.length > 0 ? ` (${schedules.length})` : ''}
          </TabBtn>
        </div>
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '10px 12px' }}>

        {/* ── 持仓 ── */}
        {tab === 'positions' && (
          positions.length === 0
            ? <Empty icon="📭" text="暂无持仓记录" />
            : positions.map((p, i) => (
              <Card key={i} accent="var(--blue)">
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                  <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--t1)', lineHeight: 1.2 }}>
                    {p.outcome}
                  </div>
                  <div style={{ fontSize: 12, fontWeight: 600, color: 'var(--green)' }}>
                    {p.shares.toFixed(2)} <span style={{ fontWeight: 400, color: 'var(--t3)', fontSize: 10 }}>股</span>
                  </div>
                </div>
                <div style={{ marginTop: 6, display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <div style={{ fontSize: 11, color: 'var(--t3)' }}>
                    成本 <span style={{ color: 'var(--t2)' }}>${p.cost_usdc.toFixed(2)}</span>
                  </div>
                  {p.note && (
                    <div style={{ fontSize: 10, color: 'var(--t3)', maxWidth: 90, textAlign: 'right', overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                      {p.note}
                    </div>
                  )}
                </div>
                <div style={{ marginTop: 5, fontSize: 10, color: 'var(--t3)', fontFamily: 'var(--mono)' }}>
                  {p.token_id.slice(0, 22)}…
                </div>
              </Card>
            ))
        )}

        {/* ── 警报 ── */}
        {tab === 'alerts' && (
          alerts.length === 0
            ? <Empty icon="🔔" text="暂无价格警报" />
            : alerts.map(a => {
              const statusColor = a.status === 'active' ? 'var(--yellow)' : a.status === 'fired' ? 'var(--green)' : 'var(--t3)'
              const statusLabel = a.status === 'active' ? '活跃' : a.status === 'fired' ? '已触发' : '已取消'
              return (
                <Card key={a.id} accent={statusColor}>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <div>
                      <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)' }}>
                        {a.direction === 'above' ? '↑' : '↓'} {(a.target * 100).toFixed(1)}%
                      </div>
                      {a.note && (
                        <div style={{ fontSize: 11, color: 'var(--t2)', marginTop: 3 }}>{a.note}</div>
                      )}
                      <div style={{ fontSize: 10, color: 'var(--t3)', marginTop: 4, fontFamily: 'var(--mono)' }}>
                        {a.token_id.slice(0, 22)}…
                      </div>
                    </div>
                    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: 5 }}>
                      <span style={{
                        fontSize: 10, padding: '2px 7px', borderRadius: 20,
                        background: 'var(--surface-3)', color: statusColor, fontWeight: 500,
                      }}>
                        {statusLabel}
                      </span>
                      {a.status === 'active' && (
                        <button
                          onClick={() => handleCancelAlert(a.id)}
                          style={{
                            fontSize: 10, padding: '2px 7px',
                            background: 'transparent', color: 'var(--red)',
                            border: '1px solid rgba(245,90,90,0.28)', borderRadius: 6,
                            cursor: 'pointer', fontFamily: 'var(--font)',
                          }}
                        >取消</button>
                      )}
                    </div>
                  </div>
                  {a.fired_price != null && (
                    <div style={{ marginTop: 6, fontSize: 11, color: 'var(--green)' }}>
                      触发价 {(a.fired_price * 100).toFixed(2)}%
                    </div>
                  )}
                </Card>
              )
            })
        )}

        {/* ── 定时任务 ── */}
        {tab === 'schedules' && (
          schedules.length === 0
            ? <Empty icon="⏰" text="暂无定时任务" />
            : schedules.map(j => {
              const isCron = j.trigger === 'cron'
              return (
                <Card key={j.id} accent="var(--purple)">
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)' }}>
                      {isCron ? '⏰ cron' : '📅 单次'}
                    </div>
                    <span style={{
                      fontSize: 10, padding: '2px 7px', borderRadius: 20,
                      background: 'var(--purple-dim)', color: 'var(--purple)', fontWeight: 500,
                    }}>活跃</span>
                  </div>
                  <div style={{ fontSize: 10, color: 'var(--t3)', marginTop: 5, fontFamily: 'var(--mono)' }}>
                    {j.id}
                  </div>
                  {j.next_run && (
                    <div style={{ marginTop: 6, fontSize: 11, color: 'var(--t2)' }}>
                      下次：{new Date(j.next_run).toLocaleString('zh-CN', {
                        timeZone: 'UTC', hour12: false,
                        month: '2-digit', day: '2-digit',
                        hour: '2-digit', minute: '2-digit',
                      })} UTC
                    </div>
                  )}
                </Card>
              )
            })
        )}
      </div>
    </div>
  )
}
