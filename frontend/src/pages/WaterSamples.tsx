import { FormEvent, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api } from '../api/client'
import type { Pond, WaterSample, WorkOrder } from '../types'

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
  const [openOrders, setOpenOrders] = useState<WorkOrder[]>([])
  const [form, setForm] = useState(empty)
  const [error, setError] = useState('')

  async function load() {
    const [ps, ws, os] = await Promise.all([
      api<Pond[]>('/api/ponds'),
      api<WaterSample[]>('/api/water-samples'),
      api<WorkOrder[]>('/api/work-orders?status=open'),
    ])
    setPonds(ps)
    setRows(ws)
    setOpenOrders(os)
    if (!form.pondId && ps[0]) {
      setForm((f) => ({ ...f, pondId: ps[0].id }))
    }
  }

  useEffect(() => {
    load().catch((e) => setError(e.message))
  }, [])

  // 当前选中塘口的高盐复测状态
  const latest = rows
    .filter((r) => r.pondId === form.pondId)
    .sort(
      (a, b) =>
        Date.parse(b.sampledAt) - Date.parse(a.sampledAt) || b.id - a.id
    )
    .slice(0, 2)
  const bothHigh =
    latest.length === 2 && latest.every((s) => s.salinityPpt >= 35)
  const openWo =
    openOrders.find((o) => o.pondId === form.pondId) ?? null
  const needsOrder = !openWo && bothHigh
  const retestTaken = !!openWo?.retestSampleId

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
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '保存失败')
    }
  }

  async function createOrder() {
    setError('')
    try {
      await api('/api/work-orders', {
        method: 'POST',
        body: JSON.stringify({ pondId: form.pondId }),
      })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '创建工单失败')
    }
  }

  async function remove(id: number) {
    if (!confirm('确认删除该水质样？')) return
    try {
      await api(`/api/water-samples/${id}`, { method: 'DELETE' })
      await load()
    } catch (err) {
      setError(err instanceof Error ? err.message : '删除失败')
    }
  }

  const pondLabel = (id: number) => {
    const p = ponds.find((x) => x.id === id)
    return p ? `${p.pondCode} (${p.species})` : `#${id}`
  }

  return (
    <div>
      <header className="page-header">
        <h1>水质采样</h1>
        <p className="muted">
          校验：溶解氧 doMgL &gt; 0，pH ∈ [6, 9]；同塘最近两份盐度均 ≥ 35 ppt
          触发复测工单，工单中仅允许 1 份盐度 &lt; 32 ppt 的复测样
        </p>
      </header>
      {error && <div className="error">{error}</div>}

      {needsOrder && (
        <div className="notice warn">
          <span>
            该塘口最近两份水样盐度均 ≥ 35 ppt，已触发高盐复测规则；生成复测工单前无法继续采样。
          </span>
          <button type="button" className="btn primary" onClick={createOrder}>
            生成复测工单
          </button>
        </div>
      )}
      {openWo && !retestTaken && (
        <div className="notice info">
          <span>
            复测工单 #{openWo.id} 进行中：仅允许登记 1 条复测水样，且复测盐度必须
            &lt; 32 ppt。
          </span>
        </div>
      )}
      {openWo && retestTaken && (
        <div className="notice warn">
          <span>
            复测样已登记（{openWo.retestSalinity} ppt），工单 #{openWo.id}{' '}
            关闭前禁止再次采样；请前往
            <Link to="/work-orders">「复测工单」</Link>页关闭。
          </span>
        </div>
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
          盐度 ppt
          <input
            type="number"
            step="0.1"
            value={form.salinityPpt}
            onChange={(e) => setForm({ ...form, salinityPpt: Number(e.target.value) })}
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
        <button type="submit" className="btn primary" disabled={retestTaken}>
          登记水质样
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
                <td>
                  {r.salinityPpt}
                  {r.workOrderId != null && (
                    <span className="badge waiting cell-badge">复测</span>
                  )}
                </td>
                <td>{r.doMgL}</td>
                <td>{r.ph}</td>
                <td>{r.notes || '—'}</td>
                <td>
                  <button className="btn ghost" onClick={() => remove(r.id)}>
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
