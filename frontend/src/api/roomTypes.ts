import client from './client'
import type { ApiResponse, RoomType } from '../types'

export const roomTypesApi = {
  list: (departmentId?: string) => client.get<ApiResponse<RoomType[]>>('/room-types/', { params: departmentId ? { department_id: departmentId } : undefined }),

  create: (data: { roomTypeName: string; departmentId?: string }) =>
    client.post<ApiResponse<RoomType>>('/room-types/', data),

  get: (id: string) => client.get<ApiResponse<RoomType>>(`/room-types/${encodeURIComponent(id)}`),

  update: (id: string, data: { roomTypeName: string; departmentId?: string }) =>
    client.patch<ApiResponse<RoomType>>(`/room-types/${encodeURIComponent(id)}`, data),

  delete: (id: string) =>
    client.delete<ApiResponse<RoomType>>(`/room-types/${encodeURIComponent(id)}`),
}
