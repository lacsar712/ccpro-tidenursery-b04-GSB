import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Pond, PondSalinityStatus, WaterSample } from '../types'

function nowLocal() {
  const d = new Date()
  d.setMinutes(d.getMinutes() - d.getTimezoneOffset())
  return d.toISOString().slice(0, 16)
}

const empty = {
  pondId: 0,
  sampledAt: nowLocal(),
  tempC: 26,
  salinityPpt: 28,
  doMgL: 6.5,
  ph: 8.0,
  notes: '',
}

export default function WaterSamples() {
  const [ponds, setPonds] = useState<Pond[]>([])
  const [rows, setRows] = useState<WaterSample[]>([])
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')
  const [status, setStatus] = useState<PondSalinityStatus | null>(null)

  async function load() {
    const [ps, ws] = await Promise.all([
      api<Pond[]>('/api/ponds'),
      api<WaterSample[]>('/api/water-samples'),
    ])
    setPonds(ps)
    setRows(ws)
    if (!form.pondId && ps[0]) {
      setForm((f) => ({ ...f, pondId: ps[0].id }))
    }
  }

  async function loadStatus(pondId: number) {
    if (!pondId) {
      setStatus(null)
      return
    }
    try {
      const s = await api<PondSalinityStatus>(
        `/api/salinity-retest-tickets/pond-status?pondId=${pondId}`,
      )
      setStatus(s)
    } catch {
      setStatus(null)
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  useEffect(() => {
    loadStatus(form.pondId)
  }, [form.pondId])

  async function refresh() {
    await Promise.all([load(), loadStatus(form.pondId)])
  }

  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')
    try {
      await api('/api/water-samples', {
        method: 'POST',
        body: JSON.stringify({
          ...form,
          sampledAt: new Date(form.sampledAt).toISOString(),
        }),
      })
      setForm((f) => ({ ...empty, pondId: f.pondId, sampledAt: nowLocal() }))
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  async function createTicket() {
    setError('')
    try {
      await api(
        `/api/salinity-retest-tickets?pondId=${form.pondId}`,
        { method: 'POST' },
      )
      await loadStatus(form.pondId)
    } catch (err) {
      setError(err instanceof Error ? err.message : '生成工单失败')
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该水质样？')) return
    try {
      await api(`/api/water-samples/${id}`, { method: 'DELETE' })
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    return p ? `${p.pondCode} (${p.species})` : `#${id}`
  }

  // 仅在工单等待复测、且还没登记复测样时允许提交
  const formDisabled = status != null && !status.canCreateSample
  const awaitingRetest = status?.phase === 'awaiting_retest'

  return (
    <div>
      <header className="page-header">
        <h1>水质采样</h1>
        <p className="muted">
          校验：溶解氧 doMgL &gt; 0，pH ∈ [6, 9]；同一塘连续两份盐度 ≥ 35 ppt
          触发复测工单，工单未关闭前限制采样。
        </p>
      </header>
      {error && <div className="error">{error}</div>}

      {status && status.reason && (
        <div className={`notice ${status.blocked ? 'blocked' : 'retest'}`}>
          <strong>{status.blocked ? '⛔ 采样已拦截' : '🧪 复测进行中'}：</strong>
          {status.reason}
        </div>
      )}

      {status?.phase === 'needs_ticket' && (
        <button className="btn primary" onClick={createTicket}>
          生成复测工单
        </button>
      )}
      {status?.phase === 'awaiting_close' && (
        <Link className="btn ghost" to="/retest-tickets">
          前往关闭工单
        </Link>
      )}

      <form className="panel form-grid" onSubmit={onSubmit}>
        <label>
          塘口
          <select
            value={form.pondId}
            onChange={(e) => setForm({ ...form, pondId: Number(e.target.value) })}
            required
          >
            {ponds.map((p) => (
              <option key={p.id} value={p.id}>
                {p.pondCode} · {p.species}
                {p.retestPending ? '（待复测）' : ''}
              </option>
            ))}
          </select>
        </label>
        <label>
          采样时间
          <input
            type="datetime-local"
            value={form.sampledAt}
            onChange={(e) => setForm({ ...form, sampledAt: e.target.value })}
            required
          />
        </label>
        <label>
          水温 °C
          <input
            type="number"
            step="0.1"
            value={form.tempC}
            onChange={(e) => setForm({ ...form, tempC: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          盐度 ppt{awaitingRetest ? '（复测须 < 32）' : ''}
          <input
            type="number"
            step="0.1"
            value={form.salinityPpt}
            onChange={(e) =>
              setForm({ ...form, salinityPpt: Number(e.target.value) })
            }
            required
          />
        </label>
        <label>
          溶解氧 mg/L
          <input
            type="number"
            step="0.1"
            value={form.doMgL}
            onChange={(e) => setForm({ ...form, doMgL: Number(e.target.value) })}
            required
          />
        </label>
        <label>
          pH
          <input
            type="number"
            step="0.1"
            value={form.ph}
            onChange={(e) => setForm({ ...form, ph: Number(e.target.value) })}
            required
          />
        </label>
        <label className="span-2">
          备注
          <input
            value={form.notes}
            onChange={(e) => setForm({ ...form, notes: e.target.value })}
          />
        </label>
        <button
          type="submit"
          className="btn primary"
          disabled={formDisabled}
          title={formDisabled ? '当前塘口被复测规则拦截' : ''}
        >
          {awaitingRetest ? '登记复测水质样' : '登记水质样'}
        </button>
      </form>

      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>ID</th>
              <th>塘口</th>
              <th>采样时间</th>
              <th>水温</th>
              <th>盐度</th>
              <th>DO</th>
              <th>pH</th>
              <th>类型</th>
              <th>备注</th>
              <th />
            </tr>
          </thead>
          <tbody>
            {rows.map((r) => (
              <tr key={r.id}>
                <td>{r.id}</td>
                <td>{pondLabel(r.pondId)}</td>
                <td>{new Date(r.sampledAt).toLocaleString()}</td>
                <td>{r.tempC}</td>
                <td className={r.salinityPpt >= 35 ? 'sal-high' : ''}>
                  {r.salinityPpt}
                </td>
                <td>{r.doMgL}</td>
                <td>{r.ph}</td>
                <td>
                  {r.retestTicketId != null ? (
                    <span className="badge retest">复测样</span>
                  ) : (
                    <span className="muted">常规</span>
                  )}
                </td>
                <td>{r.notes || '—'}</td>
                <td>
                  <button
                    className="btn ghost"
                    onClick={() => remove(r.id)}
                    disabled={r.retestTicketId != null}
                    title={
                      r.retestTicketId != null
                        ? '复测样关联工单，不可删除'
                        : ''
                    }
                  >
                    删除
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  )
}
