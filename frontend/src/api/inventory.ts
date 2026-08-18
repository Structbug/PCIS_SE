import client from './client'
import type { ApiResponse, InventoryStats, PaginatedLogs, ActivityLog } from '../types'

export const inventoryApi = {
  stats: () => client.get<ApiResponse<InventoryStats>>('/inventory/stats'),

  logs: (page: string) =>
    client.get<ApiResponse<PaginatedLogs>>(`/inventory/logs/${encodeURIComponent(page)}`),

  logsFilter: (page: string, startingDate: string, endDate: string) =>
    client.get<ApiResponse<PaginatedLogs>>(
      `/inventory/logs/${[page, startingDate, endDate].map(encodeURIComponent).join('/')}`
    ),

  recentLogs: () =>
    client.get<ApiResponse<ActivityLog[]>>('/inventory/recent-logs'),

  deleteLog: (id: string) =>
    client.delete<ApiResponse<{ _id: string }>>(`/inventory/logs/${encodeURIComponent(id)}`),

  clearLogs: () =>
    client.delete<ApiResponse<{ deleted: number }>>('/inventory/logs/clear'),

  purgeLogs: (days: number) =>
    client.delete<ApiResponse<{ deleted: number }>>(`/inventory/logs/purge/${encodeURIComponent(String(days))}`),
}
