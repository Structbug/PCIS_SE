import client from './client'
import type { ApiResponse, CategoryStat, InventoryStats, PaginatedLogs, ActivityLog } from '../types'

export const inventoryApi = {
  stats: () => client.get<ApiResponse<InventoryStats>>('/inventory/stats'),

  categoryStats: () =>
    client.get<ApiResponse<CategoryStat[]>>('/inventory/category-stats'),

  logs: (page: string) =>
    client.get<ApiResponse<PaginatedLogs>>(`/inventory/logs/${encodeURIComponent(page)}`),

  logsFilter: (page: string, startingDate: string, endDate: string) =>
    client.get<ApiResponse<PaginatedLogs>>(
      `/inventory/logs/${[page, startingDate, endDate].map(encodeURIComponent).join('/')}`
    ),

  recentLogs: () =>
    client.get<ApiResponse<ActivityLog[]>>('/inventory/recent-logs'),
}
