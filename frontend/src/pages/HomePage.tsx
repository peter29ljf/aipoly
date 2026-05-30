import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  listStrategies, createStrategy, deleteStrategy,
  sendMessage, subscribeStream, getChatHistory, getMcpHealth,
  type Strategy, type McpServerStatus,
} from '../api'

const AGENT_SID = '_agent'

// ─── MCP status bar ──────────────────────────────────────────────────────────

const MCP_LABELS: Record<string, string> = {
  'poly-trade':   'poly-trade',
  'portfolio':    'portfolio',
  'scheduler':    'scheduler',
  'sweep':        'sweep',
  'strategy-doc': 'strategy-doc',
}

function McpStatusBar() {
  const [data, setData] = useState<Record<string, McpServerStatus> | null>(null)
  const [loading, setLoading] = useState(true)

  const load = async () => {
    setLoading(true)
    try { setData(await getMcpHealth()) }
    catch { setData(null) }
    finally { setLoading(false) }
  }

  useEffect(() => { load() }, [])

  const entries = data ? Object.entries(data) : []
  const hasError = entries.some(([, v]) => v.status === 'error')

  const chipStyle = (status: string): React.CSSProperties => ({
    display: 'inline-flex', alignItems: 'center', gap: 5,
    padding: '3px 10px', borderRadius: 20, fontSize: 11, fontWeight: 500,
    background: status === 'ok' ? 'rgba(74,197,116,0.12)' : status === 'loading' ? 'rgba(148,163,184,0.12)' : 'rgba(255,99,99,0.12)',
    border: `1px solid ${status === 'ok' ? 'rgba(74,197,116,0.3)' : status === 'loading' ? 'rgba(148,163,184,0.2)' : 'rgba(255,99,99,0.3)'}`,
    color: status === 'ok' ? '#4ac574' : status === 'loading' ? '#94a3b8' : '#ff6363',
    whiteSpace: 'nowrap' as const,
    cursor: 'default',
  })

  const dotStyle = (status: string): React.CSSProperties => ({
    width: 6, height: 6, borderRadius: '50%', flexShrink: 0,
    background: status === 'ok' ? '#4ac574' : status === 'loading' ? '#94a3b8' : '#ff6363',
  })

  return (
    <div style={{
      display: 'flex', alignItems: 'center', gap: 6, flexWrap: 'wrap',
      padding: '8px 0', marginBottom: 20,
      borderBottom: '1px solid var(--border)',
    }}>
      <span style={{ fontSize: 10, fontWeight: 600, color: 'var(--t3)', letterSpacing: 1, textTransform: 'uppercase', marginRight: 4 }}>
        MCP
      </span>
      {loading && !data && (
        <span style={chipStyle('loading')}><span style={dotStyle('loading')} />检查中…</span>
      )}
      {entries.map(([key, val]) => {
        const label = MCP_LABELS[key] ?? key
        const title = val.detail || ''
        const statusStr = loading ? 'loading' : val.status
        return (
          <span key={key} style={chipStyle(statusStr)} title={title}>
            <span style={dotStyle(statusStr)} />
            {label}
            {key === 'scheduler' && val.jobs != null && (
              <span style={{ opacity: 0.7 }}>({val.jobs})</span>
            )}
            {val.status === 'error' && val.detail && (
              <span style={{ opacity: 0.8 }}>— {val.detail}</span>
            )}
          </span>
        )
      })}
      {!loading && (
        <button
          onClick={load}
          title="刷新 MCP 状态"
          style={{
            marginLeft: 'auto', background: 'none', border: 'none',
            color: 'var(--t3)', fontSize: 14, cursor: 'pointer', padding: '2px 6px',
            borderRadius: 6, transition: 'color 0.15s',
          }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--t1)' }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--t3)' }}
        >↺</button>
      )}
      {!loading && hasError && (
        <span style={{ fontSize: 11, color: '#ff6363', marginLeft: 4 }}>部分 MCP 未运行</span>
      )}
    </div>
  )
}

function isStillRunning(history: any[]): boolean {
  for (let i = history.length - 1; i >= 0; i--) {
    const k = history[i].kind
    if (k === 'run_done' || k === 'run_error') return false
    if (k === 'run_started') return true
  }
  return false
}

function ClaudeAvatar({ size = 28 }: { size?: number }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: 'linear-gradient(140deg, #e8926a 0%, #c05535 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.43, fontWeight: 700, color: 'white', userSelect: 'none',
    }}>C</div>
  )
}

function AgentChat() {
  const [events, setEvents] = useState<any[]>([])
  const [input, setInput] = useState('')
  const [running, setRunning] = useState(false)
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function setRunningWithTimeout(val: boolean) {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    setRunning(val)
    if (val) timeoutRef.current = setTimeout(() => setRunning(false), 5 * 60 * 1000)
  }

  useEffect(() => {
    getChatHistory(AGENT_SID).then(h => {
      setEvents(h); setRunning(isStillRunning(h))
    }).catch(() => {})
    const es = subscribeStream(AGENT_SID, (e) => {
      setEvents(prev => [...prev, e])
      if (e.kind === 'run_started') setRunningWithTimeout(true)
      if (e.kind === 'run_done' || e.kind === 'run_error') setRunningWithTimeout(false)
    })
    es.addEventListener('open', () => {
      getChatHistory(AGENT_SID).then(h => {
        setEvents(h)
        if (!isStillRunning(h)) setRunningWithTimeout(false)
      }).catch(() => {})
    })
    return () => { es.close(); if (timeoutRef.current) clearTimeout(timeoutRef.current) }
  }, [])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [events])

  async function handleSend() {
    const msg = input.trim()
    if (!msg || running) return
    setInput('')
    if (inputRef.current) inputRef.current.style.height = 'auto'
    setRunningWithTimeout(true)
    const r = await sendMessage(AGENT_SID, msg).catch(() => ({ started: false }))
    if (!r.started) setRunningWithTimeout(false)
  }

  function renderEvent(e: any, i: number) {
    const kind = e.kind || 'raw'

    if (kind === 'user') {
      return (
        <div key={i} style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: 12 }}>
          <div style={{
            background: 'rgba(79,142,247,0.13)',
            border: '1px solid rgba(79,142,247,0.22)',
            color: '#c5d8ff',
            borderRadius: '14px 14px 3px 14px',
            padding: '9px 14px', fontSize: 13, lineHeight: 1.65,
            wordBreak: 'break-word', maxWidth: '76%',
          }}>
            {e.content || e.text}
          </div>
        </div>
      )
    }

    if (kind === 'run_started' || kind === 'run_done') {
      return (
        <div key={i} style={{
          display: 'flex', alignItems: 'center', gap: 8, margin: '10px 0',
        }}>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
          <span style={{ fontSize: 10, color: kind === 'run_done' ? 'var(--green)' : 'var(--blue)', whiteSpace: 'nowrap' }}>
            {kind === 'run_done' ? '✓ 完成' : '▶ 运行中'}
          </span>
          <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        </div>
      )
    }

    if (kind === 'run_error') {
      return (
        <div key={i} style={{ color: 'var(--red)', fontSize: 12, marginBottom: 8 }}>
          ✕ {e.error || '运行错误'}
        </div>
      )
    }

    const text = e.content || e.text
    if (!text) return null

    return (
      <div key={i} style={{ display: 'flex', gap: 10, marginBottom: 12, alignItems: 'flex-start' }}>
        <ClaudeAvatar />
        <div style={{
          background: 'var(--surface-2)', border: '1px solid var(--border)',
          borderLeft: '2px solid var(--accent-border)',
          borderRadius: '3px 14px 14px 14px',
          padding: '9px 14px', fontSize: 13, color: 'var(--t1)',
          lineHeight: 1.65, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
          maxWidth: '82%',
        }}>
          {String(text).slice(0, 1500)}{text.length > 1500 ? '…' : ''}
        </div>
      </div>
    )
  }

  const canSend = !running && !!input.trim()

  return (
    <div style={{
      background: 'var(--surface)', border: '1px solid var(--border)',
      borderRadius: 'var(--r)', display: 'flex', flexDirection: 'column',
      height: 500, marginBottom: 32,
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0,
      }}>
        <ClaudeAvatar size={32} />
        <div>
          <div style={{ fontWeight: 600, fontSize: 14, color: 'var(--t1)' }}>全局助手</div>
          <div style={{ fontSize: 11, color: 'var(--t3)' }}>扫市场 · 查价格 · 问策略</div>
        </div>
        {running && (
          <span style={{
            marginLeft: 'auto', fontSize: 11, color: 'var(--accent)',
            display: 'flex', alignItems: 'center', gap: 5,
          }}>
            <span style={{
              width: 6, height: 6, borderRadius: '50%', background: 'var(--accent)',
              display: 'inline-block', animation: 'pulse-ring 1s ease-out infinite',
            }} />
            正在运行…
          </span>
        )}
      </div>

      {/* Messages */}
      <div style={{ flex: 1, overflowY: 'auto', padding: '16px' }}>
        {events.length === 0 && (
          <div style={{
            display: 'flex', flexDirection: 'column', alignItems: 'center',
            gap: 12, marginTop: 50, color: 'var(--t3)',
          }}>
            <ClaudeAvatar size={44} />
            <div style={{ fontSize: 14, color: 'var(--t2)', fontWeight: 500 }}>
              有什么需要帮忙的？
            </div>
            <div style={{ fontSize: 12, color: 'var(--t3)', textAlign: 'center', lineHeight: 1.6 }}>
              可扫描市场机会、查询 token 价格、分析交易策略
            </div>
          </div>
        )}
        {events.map(renderEvent)}
        {running && (
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <ClaudeAvatar />
            <div style={{
              background: 'var(--surface-2)', border: '1px solid var(--border)',
              borderLeft: '2px solid var(--accent-border)',
              borderRadius: '3px 14px 14px 14px',
              padding: '11px 16px', display: 'flex', gap: 5, alignItems: 'center',
            }}>
              <span className="typing-dot" />
              <span className="typing-dot" />
              <span className="typing-dot" />
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>

      {/* Input */}
      <div style={{
        borderTop: '1px solid var(--border)', padding: '10px 14px',
        flexShrink: 0, background: 'var(--surface)',
        borderRadius: '0 0 var(--r) var(--r)',
      }}>
        <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
          <textarea
            ref={inputRef}
            value={input}
            onChange={e => setInput(e.target.value)}
            onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
            disabled={running}
            placeholder="询问市场分析、价格查询、策略建议…"
            rows={1}
            style={{
              flex: 1, resize: 'none', maxHeight: 100, overflowY: 'auto',
              lineHeight: 1.55, background: 'var(--bg)',
              border: '1px solid var(--border-2)', borderRadius: 10,
              color: 'var(--t1)', fontSize: 13, padding: '8px 12px',
              fontFamily: 'var(--font)', outline: 'none', transition: 'border-color 0.15s',
            }}
            onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)' }}
            onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-2)' }}
            onInput={e => {
              const t = e.currentTarget; t.style.height = 'auto'
              t.style.height = Math.min(t.scrollHeight, 100) + 'px'
            }}
          />
          <button
            onClick={handleSend}
            disabled={!canSend}
            style={{
              flexShrink: 0,
              background: canSend ? 'var(--accent)' : 'var(--surface-2)',
              border: 'none', borderRadius: 10,
              color: canSend ? 'white' : 'var(--t3)',
              padding: '8px 14px', fontSize: 13, fontWeight: 500,
              transition: 'all 0.15s', cursor: canSend ? 'pointer' : 'default',
              fontFamily: 'var(--font)',
            }}
          >发送</button>
        </div>
      </div>
    </div>
  )
}

export default function HomePage() {
  const [strategies, setStrategies] = useState<Strategy[]>([])
  const [showCreate, setShowCreate] = useState(false)
  const [name, setName] = useState('')
  const [desc, setDesc] = useState('')
  const [loading, setLoading] = useState(false)
  const [tab, setTab] = useState<'agent' | 'strategies'>('agent')
  const navigate = useNavigate()

  const load = () => listStrategies().then(s => setStrategies(s.filter(x => x.id !== AGENT_SID)))
  useEffect(() => { load() }, [])

  async function handleCreate() {
    if (!name.trim()) return
    setLoading(true)
    try {
      const s = await createStrategy(name.trim(), desc.trim())
      setName(''); setDesc(''); setShowCreate(false)
      navigate(`/s/${s.id}`)
    } finally {
      setLoading(false)
    }
  }

  async function handleDelete(sid: string, name: string, e: React.MouseEvent) {
    e.stopPropagation()
    if (!confirm(`删除策略「${name}」？\n\n将同时清除所有相关定时任务和价格警报，防止孤儿任务继续触发。\n\n此操作不可恢复。`)) return
    await deleteStrategy(sid)
    load()
  }

  const tabStyle = (active: boolean): React.CSSProperties => ({
    padding: '8px 16px', fontSize: 13, fontWeight: active ? 600 : 400,
    color: active ? 'var(--t1)' : 'var(--t3)',
    background: 'none', border: 'none',
    borderBottom: `2px solid ${active ? 'var(--accent)' : 'transparent'}`,
    cursor: 'pointer', transition: 'all 0.15s', fontFamily: 'var(--font)',
  })

  return (
    <div style={{ maxWidth: 880, margin: '0 auto', padding: '32px 20px' }}>

      {/* Header */}
      <div style={{
        display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start',
        marginBottom: 28,
      }}>
        <div>
          <h1 style={{
            fontSize: 26, fontWeight: 700, margin: 0, letterSpacing: -0.8,
            background: 'linear-gradient(135deg, #e8926a 0%, #d97757 50%, #c05535 100%)',
            WebkitBackgroundClip: 'text', WebkitTextFillColor: 'transparent',
          }}>
            aipolymarket
          </h1>
          <p style={{ color: 'var(--t3)', marginTop: 5, fontSize: 13 }}>
            Polymarket · Claude AI 自动交易系统
          </p>
        </div>
        {tab === 'strategies' && (
          <button className="btn-primary" onClick={() => setShowCreate(true)}>
            + 新建策略
          </button>
        )}
      </div>

      {/* Tabs */}
      <div style={{ display: 'flex', borderBottom: '1px solid var(--border)', marginBottom: 16 }}>
        <button style={tabStyle(tab === 'agent')} onClick={() => setTab('agent')}>
          🤖 全局助手
        </button>
        <button style={tabStyle(tab === 'strategies')} onClick={() => setTab('strategies')}>
          📋 我的策略{strategies.length > 0 ? ` (${strategies.length})` : ''}
        </button>
      </div>

      {/* MCP health bar */}
      <McpStatusBar />

      {/* ── Agent tab ── */}
      {tab === 'agent' && <AgentChat />}

      {/* ── Strategies tab ── */}
      {tab === 'strategies' && (
        <>
          {/* Create form */}
          {showCreate && (
            <div style={{
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--r)', padding: '20px', marginBottom: 20,
              animation: 'fade-in 0.2s ease',
            }}>
              <div style={{ fontWeight: 600, fontSize: 15, color: 'var(--t1)', marginBottom: 16 }}>
                新建交易策略
              </div>
              <div style={{ marginBottom: 12 }}>
                <label style={{ display: 'block', marginBottom: 5, color: 'var(--t2)', fontSize: 12, fontWeight: 500 }}>
                  策略名称
                </label>
                <input
                  value={name}
                  onChange={e => setName(e.target.value)}
                  placeholder="如：扫尾策略、政治市场策略"
                  autoFocus
                  onKeyDown={e => e.key === 'Enter' && handleCreate()}
                />
              </div>
              <div style={{ marginBottom: 18 }}>
                <label style={{ display: 'block', marginBottom: 5, color: 'var(--t2)', fontSize: 12, fontWeight: 500 }}>
                  描述（可选）
                </label>
                <input
                  value={desc}
                  onChange={e => setDesc(e.target.value)}
                  placeholder="策略简介"
                />
              </div>
              <div style={{ display: 'flex', gap: 8 }}>
                <button className="btn-primary" onClick={handleCreate} disabled={loading || !name.trim()}>
                  {loading ? '创建中…' : '创建'}
                </button>
                <button className="btn-secondary" onClick={() => { setShowCreate(false); setName(''); setDesc('') }}>
                  取消
                </button>
              </div>
            </div>
          )}

          {/* Strategy list */}
          {strategies.length === 0 ? (
            <div style={{
              textAlign: 'center', padding: '60px 20px',
              background: 'var(--surface)', border: '1px solid var(--border)',
              borderRadius: 'var(--r)',
            }}>
              <div style={{ fontSize: 36, marginBottom: 14, opacity: 0.4 }}>📋</div>
              <div style={{ color: 'var(--t2)', fontSize: 15, fontWeight: 500, marginBottom: 6 }}>
                暂无策略
              </div>
              <div style={{ color: 'var(--t3)', fontSize: 13 }}>
                点击"新建策略"开始自动交易
              </div>
            </div>
          ) : (
            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {strategies.map(s => (
                <div
                  key={s.id}
                  onClick={() => navigate(`/s/${s.id}`)}
                  style={{
                    background: 'var(--surface)', border: '1px solid var(--border)',
                    borderRadius: 'var(--r)', padding: '16px 20px',
                    cursor: 'pointer', transition: 'border-color 0.15s, background 0.15s',
                    display: 'flex', justifyContent: 'space-between', alignItems: 'center',
                  }}
                  onMouseEnter={e => {
                    e.currentTarget.style.borderColor = 'var(--accent-border)'
                    e.currentTarget.style.background = 'var(--surface-2)'
                  }}
                  onMouseLeave={e => {
                    e.currentTarget.style.borderColor = 'var(--border)'
                    e.currentTarget.style.background = 'var(--surface)'
                  }}
                >
                  <div style={{ minWidth: 0 }}>
                    <div style={{ fontWeight: 600, color: 'var(--t1)', fontSize: 15 }}>
                      {s.name}
                    </div>
                    {s.description && (
                      <div style={{ color: 'var(--t2)', fontSize: 12, marginTop: 4, lineHeight: 1.5 }}>
                        {s.description}
                      </div>
                    )}
                    <div style={{ color: 'var(--t3)', fontSize: 11, marginTop: 6, fontFamily: 'var(--mono)' }}>
                      {s.id}
                      <span style={{ fontFamily: 'var(--font)' }}>
                        {' '}· {new Date(s.created_at).toLocaleDateString('zh-CN')}
                      </span>
                    </div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexShrink: 0 }}>
                    <button
                      className="btn-danger"
                      style={{ fontSize: 11 }}
                      onClick={e => handleDelete(s.id, s.name, e)}
                    >删除</button>
                    <span style={{ color: 'var(--t3)', fontSize: 16 }}>›</span>
                  </div>
                </div>
              ))}
            </div>
          )}
        </>
      )}
    </div>
  )
}
