import client from './client'
import type { ApiResponse, PaginatedRooms, Room } from '../types'

export const roomsApi = {
  create: (data: { room_name: string; room_no?: string; room_floor_id: string; room_type_id: string; allotted_to?: string }) =>
    client.post<ApiResponse<Room>>('/rooms/', data),

  get: (identifier: string) => client.get<ApiResponse<Room>>(`/rooms/${encodeURIComponent(identifier)}`),

  update: (identifier: string, data: { room_name?: string; room_no?: string; room_floor_id?: string; room_type_id?: string; allotted_to?: string }) =>
    client.patch<ApiResponse<Room>>(`/rooms/${encodeURIComponent(identifier)}`, data),

  delete: (identifier: string) =>
    client.delete<ApiResponse<Room>>(`/rooms/${encodeURIComponent(identifier)}`),

  floorFilter: (floorId: string, page: string, departmentId?: string) =>
    client.get<ApiResponse<PaginatedRooms>>(
      `/rooms/floor-filter/${encodeURIComponent(floorId)}/${encodeURIComponent(page)}`,
      { params: departmentId ? { department_id: departmentId } : undefined },
    ),

  listForFloor: (floorId: string, departmentId?: string) =>
    client.get<ApiResponse<Array<Pick<Room, '_id' | 'roomName' | 'roomNo'>>>>(
      `/rooms/floor-filter/${encodeURIComponent(floorId)}`,
      { params: departmentId ? { department_id: departmentId } : undefined },
    ),

  search: (query: string, page: string, departmentId?: string) =>
    client.get<ApiResponse<PaginatedRooms>>(
      `/rooms/search/${encodeURIComponent(query)}/${encodeURIComponent(page)}`,
      { params: departmentId ? { department_id: departmentId } : undefined },
    ),
}
