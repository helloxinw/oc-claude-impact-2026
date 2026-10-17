import type { AiDecision, Finding, FindingVerdict, NewReferral, Referral, ReferralDocument, ReferralStatus } from './types'

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

async function upload<T>(path: string, file: File): Promise<T> {
  const body = new FormData()
  body.append('file', file)
  // No Content-Type header here: the browser sets multipart/form-data with its own boundary.
  const res = await fetch(`/api${path}`, { method: 'POST', body })
  if (!res.ok) {
    const response = await res.text()
    throw new Error(`API error ${res.status}: ${response}`)
  }
  return res.json() as Promise<T>
}

export const api = {
  listReferrals: () => request<Referral[]>('/referrals'),
  getReferral: (id: string) => request<Referral>(`/referrals/${id}`),
  createReferral: (data: NewReferral) =>
    request<Referral>('/referrals', { method: 'POST', body: JSON.stringify(data) }),
  updateStatus: (id: string, status: ReferralStatus) =>
    request<Referral>(`/referrals/${id}`, { method: 'PATCH', body: JSON.stringify({ status }) }),
  updateCoordinatorDecision: (id: string, decision: AiDecision, note: string) =>
    request<Referral>(`/referrals/${id}/decision`, { method: 'PATCH', body: JSON.stringify({ decision, note }) }),
  health: () => request<{ status: string; database: string }>('/health'),
  uploadDocument: (referralId: string, file: File) =>
    upload<ReferralDocument>(`/referrals/${referralId}/documents`, file),
  listDocuments: (referralId: string) => request<ReferralDocument[]>(`/referrals/${referralId}/documents`),
  documentFileUrl: (referralId: string, documentId: string) => `/api/referrals/${referralId}/documents/${documentId}/file`,
  listFindings: (referralId: string) => request<Finding[]>(`/referrals/${referralId}/findings`),
  reviewFinding: (findingId: string, review: { verified: boolean; override_verdict: FindingVerdict | null; coordinator_note: string }) =>
    request<Finding>(`/findings/${findingId}`, { method: 'PATCH', body: JSON.stringify(review) }),
}
