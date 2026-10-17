import type { NewReferral, Referral, ReferralStatus } from './types'

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`/api${path}`, {
    ...options,
    headers: { 'Content-Type': 'application/json', ...options?.headers },
  })
  if (!res.ok) {
    const response = await res.text()
    throw new Error(`API error ${res.status}: ${response}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  listReferrals: () => request<Referral[]>('/referrals'),
  createReferral: (data: NewReferral) =>
    request<Referral>('/referrals', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id: string, status: ReferralStatus) =>
    request<Referral>(`/referrals/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  health: () => request<{ status: string; database: string }>('/health'),
}
