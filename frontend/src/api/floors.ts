import client from './client'
import type { ApiResponse, Floor } from '../types'

export const floorsApi = {
  list: (departmentId?: string) => client.get<ApiResponse<Floor[]>>('/floors/', { params: departmentId ? { department_id: departmentId } : undefined }),

  create: (data: { floorName: string; departmentId?: string }) =>
    client.post<ApiResponse<Floor>>('/floors/', data),

  get: (id: string) => client.get<ApiResponse<Floor>>(`/floors/${encodeURIComponent(id)}`),

  update: (id: string, data: { floorName: string; departmentId?: string }) =>
    client.patch<ApiResponse<Floor>>(`/floors/${encodeURIComponent(id)}`, data),

  delete: (id: string) =>
    client.delete<ApiResponse<Floor>>(`/floors/${encodeURIComponent(id)}`),
}
