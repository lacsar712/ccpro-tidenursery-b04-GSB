import { FormEvent, useEffect, useState } from 'react'
import { api } from '../api/client'
import type { Pond, WorkOrder } from '../types'

type Filter = 'all' | 'open' | 'closed'

function fmt(ts: string | null) {
  return ts ? new Date(ts).toLocaleString() : '—'
}

function StatusBadge({ wo }: { wo: WorkOrder }) {
  if (wo.status === 'closed') return <span className="badge closed">已关闭</span>
  if (wo.retestSampleId != null)
    return <span className="badge waiting">待关闭</span>
  return <span className="badge pending">待复测</span>
}

export default function WorkOrders() {
  const [ponds, setPonds] = useState<Pond[]>([])
  const [rows, setRows] = useState<WorkOrder[]>([])
  const [filter, setFilter] = useState<Filter>('all')
  const [pondId, setPondId] = useState(0)
  const [notes, setNotes] = useState<Record<number, string>>({})
  const [error, setError] = useState('')

  async function load() {
    const query = filter === 'all' ? '' : `?status=${filter}`
    const [ps, wos] = await Promise.all([
      api<Pond[]>('/api/ponds'),
      api<WorkOrder[]>(`/api/work-orders${query}`),
    ])
    setPonds(ps)
    setRows(wos)
    if (!pondId && ps[0]) setPondId(ps[0].id)
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filter])

  async function createOrder(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api('/api/work-orders', {
        method: 'POST',
        body: JSON.stringify({ pondId }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建工单失败')
    }
  }

  async function closeOrder(id: number) {
    const note = (notes[id] || '').trim()
    if (note.length < 4) {
      setError('关闭说明至少需要 4 个字符')
      return
    }
    setError('')
    try {
      await api(`/api/work-orders/${id}/close`, {
        method: 'POST',
        body: JSON.stringify({ closeNote: note }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '关闭工单失败')
    }
  }

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    return p ? `${p.pondCode} · ${p.species}` : `#${id}`
  }

  return (
    <div>
      <header className="page-header">
        <h1>高盐复测工单</h1>
        <p className="muted">
          触发阈值：同一塘口最近两份水样盐度均 ≥ 35 ppt；复测样盐度须 &lt; 32 ppt；关闭说明至少 4 个字符
        </p>
      </header>
      {error && <div className="error">{error}</div>}

      <form className="panel form-grid" onSubmit={createOrder}>
        <label>
          塘口
          <select
            value={pondId}
            onChange={(e) => setPondId(Number(e.target.value))}
            required
          >
            {ponds.map((p) => (
              <option key={p.id} value={p.id}>
                {p.pondCode} · {p.species}
              </option>
            ))}
          </select>
        </label>
        <label>
          状态筛选
          <select
            value={filter}
            onChange={(e) => setFilter(e.target.value as Filter)}
          >
            <option value="all">全部</option>
            <option value="open">未关闭</option>
            <option value="closed">已关闭</option>
          </select>
        </label>
        <button type="submit" className="btn primary">
          手动生成复测工单
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>塘口</th>
              <th>触发时刻</th>
              <th>状态</th>
              <th>复测样盐度</th>
              <th>复测时刻</th>
              <th>关闭时刻</th>
              <th>关闭说明</th>
              <th>操作</th>
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{pondLabel(r.pondId)}</td>
                <td>{fmt(r.triggeredAt)}</td>
                <td>
                  <StatusBadge wo={r} />
                </td>
                <td>{r.retestSalinity != null ? `${r.retestSalinity} ppt` : '—'}</td>
                <td>{fmt(r.retestSampledAt)}</td>
                <td>{fmt(r.closedAt)}</td>
                <td>{r.closeNote || '—'}</td>
                <td>
                  {r.status === 'open' ? (
                    <div className="row-actions">
                      <input
                        placeholder="关闭说明（至少 4 字）"
                        value={notes[r.id] || ''}
                        onChange={(e) =>
                          setNotes((n) => ({ ...n, [r.id]: e.target.value }))
                        }
                      />
                      <button
                        type="button"
                        className="btn ghost"
                        onClick={() => closeOrder(r.id)}
                      >
                        关闭工单
                      </button>
                    </div>
                  ) : (
                    '—'
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
