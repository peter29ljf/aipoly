import { useEffect, useState } from 'react'
import {
  listPositions, listAlerts, cancelAlert,
  getScheduleConfig, setScheduleConfig,
  getActivity,
  type Position, type Alert, type ScheduleConfig, type ActivityRun,
} from '../api'

interface Props { sid: string }

type Tab = 'positions' | 'alerts' | 'schedules' | 'activity'

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

const PRESET_LABELS: Record<string, string> = {
  '15min': '每 15 分钟',
  '30min': '每 30 分钟',
  '1h':    '每小时',
  '2h':    '每 2 小时',
  '4h':    '每 4 小时',
  '8h':    '每 8 小时',
  '12h':   '每 12 小时',
  'daily': '每天 09:00 UTC',
}

export default function PortfolioSidebar({ sid }: Props) {
  const [positions, setPositions] = useState<Position[]>([])
  const [alerts, setAlerts] = useState<Alert[]>([])
  const [schedCfg, setSchedCfg] = useState<ScheduleConfig | null>(null)
  const [schedSaving, setSchedSaving] = useState(false)
  const [activity, setActivity] = useState<ActivityRun[]>([])
  const [tab, setTab] = useState<Tab>('positions')

  const loadPositions = () => listPositions(sid).then(setPositions).catch(() => {})
  const loadAlerts = () => listAlerts(sid).then(setAlerts).catch(() => {})
  const loadSched = () => getScheduleConfig(sid).then(setSchedCfg).catch(() => {})
  const loadActivity = () => getActivity(sid).then(setActivity).catch(() => {})

  useEffect(() => {
    loadPositions(); loadAlerts(); loadSched(); loadActivity()
    const t = setInterval(() => { loadPositions(); loadAlerts(); loadSched(); loadActivity() }, 10000)
    return () => clearInterval(t)
  }, [sid])

  async function handleCancelAlert(id: number) {
    await cancelAlert(sid, id)
    loadAlerts()
  }

  async function handleToggle(enabled: boolean) {
    if (!schedCfg) return
    const preset = schedCfg.preset || (schedCfg.presets[4] ?? 'daily')
    setSchedSaving(true)
    await setScheduleConfig(sid, enabled, preset)
    await loadSched()
    setSchedSaving(false)
  }

  async function handlePresetChange(preset: string) {
    if (!schedCfg) return
    setSchedSaving(true)
    await setScheduleConfig(sid, schedCfg.enabled, preset)
    await loadSched()
    setSchedSaving(false)
  }

  const activeAlerts = alerts.filter(a => a.status === 'active')
  const schedEnabled = schedCfg?.enabled ?? false
  const schedCount = schedEnabled ? 1 : 0

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
            定时{schedCount > 0 ? ' ●' : ''}
          </TabBtn>
          <TabBtn active={tab === 'activity'} onClick={() => setTab('activity')}>
            活动
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
          <div>
            {/* 开关 */}
            <div style={{
              display: 'flex', alignItems: 'center', justifyContent: 'space-between',
              padding: '12px 4px 10px',
            }}>
              <div>
                <div style={{ fontSize: 13, fontWeight: 600, color: 'var(--t1)' }}>自动运行策略</div>
                <div style={{ fontSize: 11, color: 'var(--t3)', marginTop: 2 }}>
                  定时调用 Claude CLI 执行一次策略
                </div>
              </div>
              <button
                onClick={() => handleToggle(!schedEnabled)}
                disabled={schedSaving}
                style={{
                  width: 42, height: 24, borderRadius: 12, border: 'none',
                  background: schedEnabled ? 'var(--accent)' : 'var(--surface-3)',
                  cursor: schedSaving ? 'default' : 'pointer',
                  position: 'relative', transition: 'background 0.2s', flexShrink: 0,
                  opacity: schedSaving ? 0.6 : 1,
                }}
              >
                <span style={{
                  position: 'absolute', top: 3,
                  left: schedEnabled ? 21 : 3,
                  width: 18, height: 18, borderRadius: '50%',
                  background: 'white',
                  transition: 'left 0.2s',
                  boxShadow: '0 1px 3px rgba(0,0,0,0.3)',
                }} />
              </button>
            </div>

            {/* 频率选择 */}
            <div style={{ marginBottom: 14 }}>
              <div style={{ fontSize: 11, color: 'var(--t3)', marginBottom: 6 }}>执行频率</div>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 4 }}>
                {(schedCfg?.presets ?? Object.keys(PRESET_LABELS)).map(p => (
                  <button
                    key={p}
                    onClick={() => handlePresetChange(p)}
                    disabled={schedSaving}
                    style={{
                      padding: '7px 10px', borderRadius: 'var(--r-sm)',
                      border: '1px solid',
                      borderColor: schedCfg?.preset === p ? 'var(--accent)' : 'var(--border)',
                      background: schedCfg?.preset === p ? 'rgba(99,102,241,0.1)' : 'var(--surface-2)',
                      color: schedCfg?.preset === p ? 'var(--accent)' : 'var(--t2)',
                      fontSize: 12, fontWeight: schedCfg?.preset === p ? 600 : 400,
                      cursor: schedSaving ? 'default' : 'pointer',
                      textAlign: 'left', fontFamily: 'var(--font)',
                      transition: 'all 0.15s',
                    }}
                  >
                    {PRESET_LABELS[p] ?? p}
                  </button>
                ))}
              </div>
            </div>

            {/* 下次执行时间 */}
            {schedEnabled && schedCfg?.job?.next_run && (
              <div style={{
                padding: '8px 10px', borderRadius: 'var(--r-sm)',
                background: 'var(--surface-2)', border: '1px solid var(--border)',
                fontSize: 11, color: 'var(--t2)',
              }}>
                <span style={{ color: 'var(--t3)' }}>下次执行：</span>
                {new Date(schedCfg.job.next_run).toLocaleString('zh-CN', {
                  timeZone: 'Asia/Shanghai', hour12: false,
                  month: '2-digit', day: '2-digit',
                  hour: '2-digit', minute: '2-digit',
                })}
                <span style={{ color: 'var(--t3)', marginLeft: 4 }}>北京时间</span>
              </div>
            )}

            {!schedEnabled && (
              <div style={{ marginTop: 8, fontSize: 11, color: 'var(--t3)', textAlign: 'center' }}>
                开启后将按所选频率自动运行
              </div>
            )}
          </div>
        )}

        {/* ── 活动时间线 ── */}
        {tab === 'activity' && (
          activity.length === 0
            ? <Empty icon="📋" text="暂无运行记录" />
            : <div style={{ position: 'relative' }}>
                {/* 竖线 */}
                <div style={{
                  position: 'absolute', left: 7, top: 6, bottom: 6,
                  width: 1, background: 'var(--border)',
                }} />
                {activity.map((run, i) => {
                  const isOk = run.status === 'ok'
                  const isErr = run.status === 'error'
                  const dotColor = isErr ? 'var(--red)' : isOk ? 'var(--green)' : 'var(--yellow)'
                  const dt = new Date(run.ts)
                  const dateStr = dt.toLocaleDateString('zh-CN', { timeZone: 'Asia/Shanghai', month: '2-digit', day: '2-digit' })
                  const timeStr = dt.toLocaleTimeString('zh-CN', { timeZone: 'Asia/Shanghai', hour: '2-digit', minute: '2-digit', hour12: false })
                  const triggerIcon = run.trigger === 'schedule' || run.trigger === 'cron' ? '⏰'
                    : run.trigger === 'alert' ? '🔔'
                    : run.trigger === 'chat' ? '💬'
                    : '▶'
                  return (
                    <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 14, position: 'relative' }}>
                      {/* 圆点 */}
                      <div style={{
                        width: 14, height: 14, borderRadius: '50%',
                        background: dotColor, flexShrink: 0, marginTop: 1,
                        boxShadow: `0 0 0 2px var(--surface), 0 0 0 3px ${dotColor}44`,
                        zIndex: 1,
                      }} />
                      <div style={{ flex: 1, minWidth: 0 }}>
                        {/* 时间 + 触发类型 */}
                        <div style={{ display: 'flex', alignItems: 'center', gap: 5, marginBottom: 3 }}>
                          <span style={{ fontSize: 10, color: 'var(--t3)', fontFamily: 'var(--mono)' }}>
                            {dateStr} {timeStr}
                          </span>
                          <span style={{ fontSize: 10, color: 'var(--t3)' }}>·</span>
                          <span style={{ fontSize: 10, color: 'var(--t2)' }}>
                            {triggerIcon} {run.trigger_label}
                          </span>
                          {run.duration_s != null && (
                            <>
                              <span style={{ fontSize: 10, color: 'var(--t3)' }}>·</span>
                              <span style={{ fontSize: 10, color: 'var(--t3)' }}>{run.duration_s}s</span>
                            </>
                          )}
                        </div>
                        {/* 用户消息（chat 触发时） */}
                        {run.user_message && (
                          <div style={{
                            fontSize: 11, color: 'var(--t3)', marginBottom: 3,
                            fontStyle: 'italic', overflow: 'hidden',
                            textOverflow: 'ellipsis', whiteSpace: 'nowrap',
                          }}>
                            "{run.user_message}"
                          </div>
                        )}
                        {/* 摘要 */}
                        {run.summary ? (
                          <div style={{
                            fontSize: 12, color: isErr ? 'var(--red)' : 'var(--t1)',
                            lineHeight: 1.4,
                          }}>
                            {run.summary}
                          </div>
                        ) : (
                          <div style={{ fontSize: 11, color: 'var(--t3)' }}>
                            {isErr ? '运行出错' : '无输出'}
                          </div>
                        )}
                      </div>
                    </div>
                  )
                })}
              </div>
        )}
      </div>
    </div>
  )
}
