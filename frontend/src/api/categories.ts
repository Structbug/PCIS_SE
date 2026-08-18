import client from './client'
import type { ApiResponse, Category } from '../types'

export const categoriesApi = {
  list: () => client.get<ApiResponse<Category[]>>('/categories/'),

  create: (data: { categoryName: string }) =>
    client.post<ApiResponse<Category>>('/categories/', data),

  update: (id: string, data: { categoryName: string }) =>
    client.patch<ApiResponse<Category>>(`/categories/${encodeURIComponent(id)}`, data),

  delete: (id: string) =>
    client.delete<ApiResponse<Record<string, never>>>(`/categories/${encodeURIComponent(id)}`),
}