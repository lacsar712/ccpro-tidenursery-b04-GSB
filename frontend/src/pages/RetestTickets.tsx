import { useEffect, useState } from 'react'
import { api } from '../api/client'
import type { SalinityRetestTicket } from '../types'

export default function RetestTickets() {
  const [rows, setRows] = useState<SalinityRetestTicket[]>([])
  const [error, setError] = useState('')
  const [note, setNote] = useState<Record<number, string>>({})

  async function load() {
    const ts = await api<SalinityRetestTicket[]>(
      '/api/salinity-retest-tickets',
    )
    setRows(ts)
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  async function closeTicket(t: SalinityRetestTicket) {
    const closeNote = (note[t.id] || '').trim()
    if (closeNote.length < 4) {
      setError('关闭说明至少 4 个字')
      return
    }
    setError('')
    try {
      await api(`/api/salinity-retest-tickets/${t.id}/close`, {
        method: 'POST',
        body: JSON.stringify({ closeNote }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '关闭失败')
    }
  }

  return (
    <div>
      <header className="page-header">
        <h1>高盐复测工单</h1>
        <p className="muted">
          同塘同时仅一张未关闭工单；最近两份盐度均 ≥ 35 ppt 触发，
          补一份盐度 &lt; 32 ppt 的复测样后方可关闭。
        </p>
      </header>
      {error && <div className="error">{error}</div>}

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>所属塘口</th>
              <th>触发时刻</th>
              <th>状态</th>
              <th>复测样 / 盐度</th>
              <th>关闭说明</th>
              <th>关闭时刻</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((t) => {
              const open = !t.closedAt
              return (
                <tr key={t.id}>
                  <td>{t.id}</td>
                  <td>{t.pondCode ? `塘 ${t.pondCode}` : `#${t.pondId}`}</td>
                  <td>{new Date(t.triggeredAt).toLocaleString()}</td>
                  <td>
                    {open ? (
                      <span className="badge retest">待复测</span>
                    ) : (
                      <span className="badge stocked">已关闭</span>
                    )}
                  </td>
                  <td>
                    {t.retestSampleId != null ? (
                      <>
                        #{t.retestSampleId} · {t.retestSalinity} ppt
                      </>
                    ) : open ? (
                      <span className="muted">尚未复测</span>
                    ) : (
                      '—'
                    )}
                  </td>
                  <td>{t.closeNote || '—'}</td>
                  <td>
                    {t.closedAt ? new Date(t.closedAt).toLocaleString() : '—'}
                  </td>
                  <td>
                    {open && (
                      <div className="inline-close">
                        <input
                          placeholder="关闭说明（≥4字）"
                          value={note[t.id] || ''}
                          onChange={(e) =>
                            setNote((n) => ({ ...n, [t.id]: e.target.value }))
                          }
                        />
                        <button
                          className="btn primary"
                          onClick={() => closeTicket(t)}
                        >
                          关闭工单
                        </button>
                      </div>
                    )}
                  </td>
                </tr>
              )
            })}
            {rows.length === 0 && (
              <tr>
                <td colSpan={8} className="muted" style={{ textAlign: 'center' }}>
                  暂无复测工单
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  )
}
