import { useEffect, useRef, useState } from 'react'
import { getChatHistory, runStrategy, sendMessage, subscribeStream } from '../api'

interface Props { sid: string; readonly?: boolean }
interface ChatEvent {
  kind?: string; text?: string; content?: string
  trigger?: string; ts?: string; error?: string
  [key: string]: any
}

function ClaudeAvatar({ size = 28 }: { size?: number }) {
  return (
    <div style={{
      width: size, height: size, borderRadius: '50%', flexShrink: 0,
      background: 'linear-gradient(140deg, #e8926a 0%, #c05535 100%)',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: size * 0.43, fontWeight: 700, color: 'white',
      letterSpacing: -0.5, userSelect: 'none',
    }}>C</div>
  )
}

function SystemDivider({ e }: { e: ChatEvent }) {
  const ts = e.ts
    ? new Date(e.ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : ''

  if (e.kind === 'run_started') {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 10,
        margin: '16px 0', animation: 'fade-in 0.2s ease',
      }}>
        <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        <span style={{
          fontSize: 11, fontWeight: 500, color: 'var(--blue)',
          whiteSpace: 'nowrap', display: 'flex', alignItems: 'center', gap: 4,
        }}>
          <span style={{
            width: 6, height: 6, borderRadius: '50%', background: 'var(--blue)',
            display: 'inline-block', animation: 'pulse-ring 1.2s ease-out infinite',
          }} />
          运行开始{e.trigger && e.trigger !== 'chat' ? ` · ${e.trigger}` : ''}{ts ? ` ${ts}` : ''}
        </span>
        <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      </div>
    )
  }

  if (e.kind === 'run_done') {
    return (
      <div style={{ display: 'flex', alignItems: 'center', gap: 10, margin: '16px 0' }}>
        <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
        <span style={{ fontSize: 11, fontWeight: 500, color: 'var(--green)', whiteSpace: 'nowrap' }}>
          ✓ 运行完成{ts ? ` ${ts}` : ''}
        </span>
        <div style={{ flex: 1, height: 1, background: 'var(--border)' }} />
      </div>
    )
  }

  if (e.kind === 'run_error') {
    return (
      <div style={{
        margin: '10px 0', padding: '9px 13px', borderRadius: 'var(--r-sm)',
        background: 'var(--red-dim)', border: '1px solid rgba(245,90,90,0.22)',
        fontSize: 12, color: 'var(--red)', animation: 'fade-in 0.2s ease',
      }}>
        ✕ 运行错误{e.error ? `：${e.error}` : ''}
      </div>
    )
  }

  if (e.kind === 'doc_updated') {
    return (
      <div style={{
        textAlign: 'center', padding: '6px 0', fontSize: 11,
        color: 'var(--purple)', animation: 'fade-in 0.2s ease',
      }}>📄 策略文档已更新</div>
    )
  }

  return null
}

function MessageBubble({ e }: { e: ChatEvent }) {
  const kind = e.kind || 'raw'
  const ts = e.ts
    ? new Date(e.ts).toLocaleTimeString('zh-CN', { hour: '2-digit', minute: '2-digit' })
    : ''

  if (['run_started', 'run_done', 'run_error', 'doc_updated'].includes(kind)) {
    return <SystemDivider e={e} />
  }

  if (kind === 'user') {
    return (
      <div style={{
        display: 'flex', justifyContent: 'flex-end',
        marginBottom: 14, animation: 'fade-in 0.2s ease',
      }}>
        <div style={{ maxWidth: '76%' }}>
          <div style={{
            background: 'rgba(79,142,247,0.13)',
            border: '1px solid rgba(79,142,247,0.22)',
            color: '#c5d8ff',
            borderRadius: '14px 14px 3px 14px',
            padding: '9px 14px', fontSize: 13, lineHeight: 1.65,
            wordBreak: 'break-word',
          }}>
            {e.content || e.text}
          </div>
          {ts && (
            <div style={{ color: 'var(--t3)', fontSize: 10, textAlign: 'right', marginTop: 3 }}>
              {ts}
            </div>
          )}
        </div>
      </div>
    )
  }

  const text = e.content || e.text || (kind !== 'raw' ? JSON.stringify(e) : '')
  if (!text) return null

  return (
    <div style={{
      display: 'flex', gap: 10, marginBottom: 14,
      alignItems: 'flex-start', animation: 'fade-in 0.2s ease',
    }}>
      <ClaudeAvatar />
      <div style={{ flex: 1, minWidth: 0 }}>
        <div style={{
          background: 'var(--surface)',
          border: '1px solid var(--border)',
          borderLeft: '2px solid var(--accent-border)',
          borderRadius: '3px 14px 14px 14px',
          padding: '9px 14px', fontSize: 13, color: 'var(--t1)',
          lineHeight: 1.68, whiteSpace: 'pre-wrap', wordBreak: 'break-word',
        }}>
          {text.slice(0, 2000)}{text.length > 2000 ? '…' : ''}
        </div>
        {ts && (
          <div style={{ color: 'var(--t3)', fontSize: 10, marginTop: 3 }}>{ts}</div>
        )}
      </div>
    </div>
  )
}

function isStillRunning(history: ChatEvent[]): boolean {
  for (let i = history.length - 1; i >= 0; i--) {
    const k = history[i].kind
    if (k === 'run_done' || k === 'run_error') return false
    if (k === 'run_started') return true
  }
  return false
}

export default function ChatPanel({ sid, readonly = false }: Props) {
  const [events, setEvents] = useState<ChatEvent[]>([])
  const [running, setRunning] = useState(false)
  const [input, setInput] = useState('')
  const bottomRef = useRef<HTMLDivElement>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const timeoutRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  function setRunningWithTimeout(val: boolean) {
    if (timeoutRef.current) clearTimeout(timeoutRef.current)
    setRunning(val)
    if (val) timeoutRef.current = setTimeout(() => setRunning(false), 5 * 60 * 1000)
  }

  useEffect(() => {
    getChatHistory(sid).then(h => { setEvents(h); setRunning(isStillRunning(h)) })
    const es = subscribeStream(sid, (e) => {
      setEvents(prev => [...prev, e])
      if (e.kind === 'run_started') setRunningWithTimeout(true)
      if (e.kind === 'run_done' || e.kind === 'run_error') setRunningWithTimeout(false)
    })
    es.addEventListener('open', () => {
      getChatHistory(sid).then(h => {
        setEvents(h)
        if (!isStillRunning(h)) setRunningWithTimeout(false)
      })
    })
    return () => { es.close(); if (timeoutRef.current) clearTimeout(timeoutRef.current) }
  }, [sid])

  useEffect(() => { bottomRef.current?.scrollIntoView({ behavior: 'smooth' }) }, [events])

  async function handleRun() {
    setRunningWithTimeout(true)
    const r = await runStrategy(sid)
    if (!r.started) setRunningWithTimeout(false)
  }

  async function handleSend() {
    const msg = input.trim()
    if (!msg || running) return
    setInput('')
    if (inputRef.current) { inputRef.current.style.height = 'auto' }
    setRunningWithTimeout(true)
    const r = await sendMessage(sid, msg)
    if (!r.started) setRunningWithTimeout(false)
  }

  const canSend = !running && !!input.trim()

  return (
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%', background: 'var(--bg)' }}>

      {/* Toolbar */}
      <div style={{
        padding: '10px 16px', borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0, background: 'var(--surface)',
      }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <ClaudeAvatar />
          <div>
            <div style={{ fontWeight: 600, fontSize: 13, color: 'var(--t1)', lineHeight: 1.2 }}>
              与 Claude 对话
            </div>
            <div style={{ fontSize: 11, marginTop: 2 }}>
              {running ? (
                <span style={{ color: 'var(--accent)', display: 'flex', alignItems: 'center', gap: 5 }}>
                  <span style={{
                    width: 6, height: 6, borderRadius: '50%',
                    background: 'var(--accent)', display: 'inline-block',
                    animation: 'pulse-ring 1s ease-out infinite',
                  }} />
                  正在运行…
                </span>
              ) : (
                <span style={{ color: 'var(--t3)' }}>就绪</span>
              )}
            </div>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
          {readonly && (
            <span style={{
              fontSize: 10, fontWeight: 600, letterSpacing: 0.5,
              color: 'var(--t3)', background: 'var(--bg)',
              border: '1px solid var(--border)', borderRadius: 5,
              padding: '2px 7px', textTransform: 'uppercase',
            }}>只读</span>
          )}
          {!readonly && (
            <button
              className="btn-secondary"
              onClick={handleRun}
              disabled={running}
              style={{ fontSize: 12, padding: '5px 12px' }}
            >
              {running ? '运行中…' : '▶ 手动运行'}
            </button>
          )}
        </div>
      </div>

      {/* Messages */}
      <div style={{
        flex: 1, overflowY: 'auto', padding: '18px 20px',
        display: 'flex', flexDirection: 'column',
      }}>
        {events.length === 0 && !running && (
          <div style={{
            margin: 'auto', textAlign: 'center',
            display: 'flex', flexDirection: 'column', alignItems: 'center', gap: 14,
          }}>
            <ClaudeAvatar size={48} />
            <div style={{ color: 'var(--t2)', fontSize: 14, fontWeight: 500 }}>
              你好，我是 Claude
            </div>
            <div style={{ color: 'var(--t3)', fontSize: 12, maxWidth: 240, lineHeight: 1.6 }}>
              在下方输入消息与我对话，或点击"手动运行"启动策略分析。
            </div>
          </div>
        )}

        {events.map((e, i) => <MessageBubble key={i} e={e} />)}

        {running && (
          <div style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
            <ClaudeAvatar />
            <div style={{
              background: 'var(--surface)', border: '1px solid var(--border)',
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

      {/* Input area */}
      {readonly ? (
        <div style={{
          borderTop: '1px solid var(--border)', padding: '14px 16px',
          flexShrink: 0, background: 'var(--surface)',
          display: 'flex', alignItems: 'center', justifyContent: 'center', gap: 8,
        }}>
          <span style={{ fontSize: 18, opacity: 0.3 }}>🔒</span>
          <span style={{ fontSize: 12, color: 'var(--t3)' }}>访客模式 — 仅可查看，无法发送消息</span>
        </div>
      ) : (
        <div style={{
          borderTop: '1px solid var(--border)', padding: '12px 16px',
          flexShrink: 0, background: 'var(--surface)',
        }}>
          <div style={{ display: 'flex', gap: 8, alignItems: 'flex-end' }}>
            <textarea
              ref={inputRef}
              value={input}
              onChange={e => setInput(e.target.value)}
              onKeyDown={e => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); handleSend() } }}
              disabled={running}
              placeholder="输入消息… (Enter 发送，Shift+Enter 换行)"
              rows={1}
              style={{
                flex: 1, resize: 'none', maxHeight: 120, overflowY: 'auto',
                lineHeight: 1.55, background: 'var(--bg)',
                border: '1px solid var(--border-2)', borderRadius: 10,
                color: 'var(--t1)', fontSize: 13, padding: '9px 13px',
                fontFamily: 'var(--font)', outline: 'none', transition: 'border-color 0.15s',
              }}
              onFocus={e => { e.currentTarget.style.borderColor = 'var(--accent)' }}
              onBlur={e => { e.currentTarget.style.borderColor = 'var(--border-2)' }}
              onInput={e => {
                const t = e.currentTarget
                t.style.height = 'auto'
                t.style.height = Math.min(t.scrollHeight, 120) + 'px'
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
                padding: '9px 16px', fontSize: 13, fontWeight: 500,
                transition: 'all 0.15s', cursor: canSend ? 'pointer' : 'default',
                fontFamily: 'var(--font)',
              }}
            >发送</button>
          </div>
          <div style={{ fontSize: 10, color: 'var(--t3)', marginTop: 6, textAlign: 'right' }}>
            Enter 发送 · Shift+Enter 换行
          </div>
        </div>
      )}
    </div>
  )
}
