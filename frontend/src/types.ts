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
  retestPending: boolean
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
  retestTicketId?: number | null
}

export type SalinityRetestTicket = {
  id: number
  pondId: number
  pondCode?: string | null
  triggeredAt: string
  closedAt?: string | null
  closeNote?: string | null
  retestSampleId?: number | null
  retestSalinity?: number | null
}

export type PondSalinityStatus = {
  pondId: number
  blocked: boolean
  canCreateSample: boolean
  canCreateTicket: boolean
  phase: 'normal' | 'needs_ticket' | 'awaiting_retest' | 'awaiting_close'
  openTicketId?: number | null
  reason?: string | null
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
  retestPendingPonds: number
}
