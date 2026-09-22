export type User = {
  id: number
  username: string
  role: string
  display_name: string
}

export type Hatchery = {
  id: number
  name: string
  seawaterSource: string
  notes?: string | null
}

export type Pond = {
  id: number
  hatcheryId: number
  pondCode: string
  species: string
  volumeM3: number
  status: 'stocked' | 'dry' | 'quarantine'
  retestPending?: boolean
  retestAlert?: boolean
}

export type WaterSample = {
  id: number
  pondId: number
  sampledAt: string
  tempC: number
  salinityPpt: number
  doMgL: number
  ph: number
  notes?: string | null
  workOrderId?: number | null
}

export type WorkOrder = {
  id: number
  pondId: number
  pondCode: string
  triggeredAt: string
  closedAt: string | null
  closeNote: string | null
  status: 'open' | 'closed'
  retestSampleId: number | null
  retestSalinity: number | null
  retestSampledAt: string | null
}

export type FeedEvent = {
  id: number
  pondId: number
  fedAt: string
  feedType: string
  amountKg: number
  operatorName: string
}

export type DashboardStats = {
  pondTotal: number
  quarantineCount: number
  samplesLast24h: number
  feedKgLast7d: number
  retestPendingCount: number
}
