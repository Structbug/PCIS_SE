import client from './client'
import type { AccessRequest, AccessRequestsResponse, ApiResponse, BlockedRequestersResponse, BlockedRequester } from '../types'

export interface AccessRequestInput {
  fullName: string
  email: string
  department: string
  rollNo?: string
  description?: string
}

export const accessRequestsApi = {
  create: (data: AccessRequestInput) =>
    client.post<ApiResponse<AccessRequest>>('/access-requests/', data),

  list: () => client.get<ApiResponse<AccessRequestsResponse>>('/access-requests/all/'),

  setStatus: (id: string, status: AccessRequest['status']) =>
    client.patch<ApiResponse<AccessRequest>>(`/access-requests/${encodeURIComponent(id)}`, { status }),

  remove: (id: string) =>
    client.delete<ApiResponse<{ _id: string }>>(`/access-requests/${encodeURIComponent(id)}`),

  listBlocked: () => client.get<ApiResponse<BlockedRequestersResponse>>('/blocked-requesters/'),

  block: (email: string) =>
    client.post<ApiResponse<BlockedRequester>>('/blocked-requesters/', { email }),

  unblock: (id: string) =>
    client.delete<ApiResponse<{ _id: string }>>(`/blocked-requesters/${encodeURIComponent(id)}`),
}
