import client from './client'
import type { ApiResponse, Department } from '../types'

export const departmentsApi = {
  list: () => client.get<ApiResponse<Department[]>>('/departments/'),
  create: (data: { departmentName: string }) => client.post<ApiResponse<Department>>('/departments/', data),
  update: (id: string, data: { departmentName: string }) => client.patch<ApiResponse<Department>>(`/departments/${encodeURIComponent(id)}`, data),
  delete: (id: string) => client.delete<ApiResponse<Record<string, never>>>(`/departments/${encodeURIComponent(id)}`),
}
