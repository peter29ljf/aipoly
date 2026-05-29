import { useEffect, useRef, useState } from 'react'
import { getStrategyDoc, writeStrategyDoc, subscribeStream } from '../api'

interface Props { sid: string }

function renderMarkdown(text: string) {
  return text.split('\n').map((line, i) => {
    if (line.startsWith('# ')) {
      return (
        <h2 key={i} style={{
          color: 'var(--t1)', fontSize: 15, fontWeight: 700,
          marginBottom: 8, marginTop: i > 0 ? 18 : 0, letterSpacing: -0.3,
        }}>
          {line.slice(2)}
        </h2>
      )
    }
    if (line.startsWith('## ')) {
      return (
        <h3 key={i} style={{
          color: 'var(--t1)', fontSize: 13, fontWeight: 600,
          marginBottom: 5, marginTop: i > 0 ? 14 : 0,
        }}>
          {line.slice(3)}
        </h3>
      )
    }
    if (line.startsWith('### ')) {
      return (
        <h4 key={i} style={{
          color: 'var(--t2)', fontSize: 12, fontWeight: 600,
          marginBottom: 4, marginTop: i > 0 ? 10 : 0,
        }}>
          {line.slice(4)}
        </h4>
      )
    }
    if (line.startsWith('- ')) {
      return (
        <div key={i} style={{
          display: 'flex', gap: 6, color: 'var(--t2)',
          fontSize: 12, marginBottom: 4, lineHeight: 1.6,
        }}>
          <span style={{ color: 'var(--accent)', flexShrink: 0, marginTop: 1 }}>•</span>
          <span>{line.slice(2)}</span>
        </div>
      )
    }
    if (line.startsWith('> ')) {
      return (
        <div key={i} style={{
          borderLeft: '2px solid var(--accent-border)',
          paddingLeft: 10, color: 'var(--t2)',
          fontSize: 12, marginBottom: 4, lineHeight: 1.6, fontStyle: 'italic',
        }}>
          {line.slice(2)}
        </div>
      )
    }
    if (line.trim() === '') return <div key={i} style={{ height: 8 }} />
    return (
      <div key={i} style={{ color: 'var(--t2)', fontSize: 12, marginBottom: 4, lineHeight: 1.6 }}>
        {line}
      </div>
    )
  })
}

export default function StrategyDocSidebar({ sid }: Props) {
  const [content, setContent] = useState('')
  const [editing, setEditing] = useState(false)
  const [draft, setDraft] = useState('')
  const [saving, setSaving] = useState(false)
  const esRef = useRef<EventSource | null>(null)

  const loadDoc = () => getStrategyDoc(sid).then(setContent)

  useEffect(() => {
    loadDoc()
    const es = subscribeStream(sid, (e) => {
      if (e.kind === 'doc_updated' && e.content) setContent(e.content)
    })
    esRef.current = es
    return () => es.close()
  }, [sid])

  function handleEdit() {
    setDraft(content)
    setEditing(true)
  }

  async function handleSave() {
    setSaving(true)
    try {
      await writeStrategyDoc(sid, draft)
      setContent(draft)
      setEditing(false)
    } finally {
      setSaving(false)
    }
  }

  return (
    <div style={{
      height: '100%', display: 'flex', flexDirection: 'column',
      background: 'var(--surface)', borderLeft: '1px solid var(--border)',
    }}>
      {/* Header */}
      <div style={{
        padding: '12px 14px', borderBottom: '1px solid var(--border)',
        display: 'flex', justifyContent: 'space-between', alignItems: 'center',
        flexShrink: 0,
      }}>
        <div style={{ fontWeight: 600, fontSize: 12, color: 'var(--t2)', letterSpacing: 0.5 }}>
          策略文档
        </div>
        {!editing ? (
          <button
            className="btn-secondary"
            style={{ fontSize: 11, padding: '4px 10px' }}
            onClick={handleEdit}
          >
            编辑
          </button>
        ) : (
          <div style={{ display: 'flex', gap: 6 }}>
            <button
              className="btn-primary"
              style={{ fontSize: 11, padding: '4px 10px' }}
              onClick={handleSave}
              disabled={saving}
            >
              {saving ? '保存中…' : '保存'}
            </button>
            <button
              className="btn-secondary"
              style={{ fontSize: 11, padding: '4px 10px' }}
              onClick={() => setEditing(false)}
            >
              取消
            </button>
          </div>
        )}
      </div>

      {/* Content */}
      <div style={{ flex: 1, overflowY: 'auto', padding: editing ? 0 : '14px 14px' }}>
        {editing ? (
          <textarea
            value={draft}
            onChange={e => setDraft(e.target.value)}
            style={{
              width: '100%', height: '100%', minHeight: 300,
              background: 'var(--bg)', border: 'none', borderRadius: 0,
              color: 'var(--t1)', fontSize: 12, fontFamily: 'var(--mono)',
              padding: '14px', resize: 'none', lineHeight: 1.65, outline: 'none',
            }}
            placeholder="在此编写策略说明…"
          />
        ) : (
          content
            ? <div>{renderMarkdown(content)}</div>
            : (
              <div style={{
                display: 'flex', flexDirection: 'column', alignItems: 'center',
                gap: 10, marginTop: 40, color: 'var(--t3)', textAlign: 'center',
              }}>
                <div style={{ fontSize: 28, opacity: 0.4 }}>📋</div>
                <div style={{ fontSize: 12 }}>策略文档为空</div>
                <div style={{ fontSize: 11 }}>
                  点击"编辑"手动填写，或让 Claude 运行后自动生成。
                </div>
              </div>
            )
        )}
      </div>
    </div>
  )
}
