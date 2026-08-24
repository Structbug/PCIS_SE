import client from './client'
import type {
  ApiResponse, CursorPaginatedItems, Item, ItemReport, PaginatedItems,
  PaginatedCommonItems,
} from '../types'

export interface ItemCreateData {
  itemName: string
  itemDescription?: string
  itemModelNumberOrMake?: string
  itemSource: string
  itemCost?: number
  itemAcquiredDate?: string
  itemSerialNumber?: string
  itemStatus?: string
  itemCategory?: string
  itemSubCategory?: string
  itemFloor: string
  itemRoom: string
  item_create_count?: number
}

export interface ItemUpdateData {
  item_name?: string
  item_description?: string
  item_category_id?: string
  item_subCategory_id?: string
  item_make_or_model_no?: string
  item_source?: string
  item_cost?: number
  item_acquired_date?: string
  item_room_id?: string
  item_status?: string
}

export interface ItemQueryParams {
  search?: string
  category_id?: string
  sub_category_id?: string
  room_id?: string
  floor_id?: string
  department_id?: string
  status?: string
  source?: string
  starting_date?: string
  end_date?: string
  cursor?: string
  group?: string
}

export interface CSVImportPreview {
  fileName: string
  totalRows: number
  validRows: number
  totalItems: number
  errors: Array<{ row: number; message: string }>
}

export interface CSVImportResult {
  fileName: string
  importedRows: number
  importedItems: number
}

export const itemsApi = {
  create: (data: ItemCreateData) =>
    client.post<ApiResponse<Item[]>>('/items/', data),

  get: (id: string) =>
    client.get<ApiResponse<ItemReport>>(`/items/item/${encodeURIComponent(id)}`),

  all: (page: string) =>
    client.get<ApiResponse<PaginatedItems>>(`/items/all/${encodeURIComponent(page)}`),

  search: (query: string, page: string) =>
    client.get<ApiResponse<PaginatedItems>>(
      `/items/search/${encodeURIComponent(query)}/${encodeURIComponent(page)}`
    ),

  query: (params: ItemQueryParams, signal?: AbortSignal) =>
    client.get<ApiResponse<CursorPaginatedItems>>('/items/search', { params, signal }),

  filter: (params: {
    category_id: string; subCategory_id: string; room_id: string; floor_id: string
    status: string; source: string; starting_date: string; end_date: string; page: string
  }) => client.get<ApiResponse<PaginatedItems>>(
    `/items/filter/${[
      params.category_id, params.subCategory_id, params.room_id, params.floor_id,
      params.status, params.source, params.starting_date, params.end_date, params.page,
    ].map(encodeURIComponent).join('/')}`
  ),

  updateStatus: (id: string, statusId: string) =>
    client.patch<ApiResponse<Item>>(`/items/${encodeURIComponent(id)}/status`, { statusId }),

  updateDetails: (id: string, data: ItemUpdateData) =>
    client.patch<ApiResponse<Item>>(`/items/${encodeURIComponent(id)}/details`, data),

  moveRoom: (id: string, newRoomId: string) =>
    client.patch<ApiResponse<Item>>(`/items/${encodeURIComponent(id)}/room`, { new_room_id: newRoomId }),

  moveDepartment: (id: string, newDepartmentId: string, newRoomId: string) =>
    client.patch<ApiResponse<Item>>(`/items/${encodeURIComponent(id)}/department`, {
      new_department_id: newDepartmentId,
      new_room_id: newRoomId,
    }),

  previewCsvImport: (file: File) => {
    const data = new FormData()
    data.append('file', file)
    // Do not set Content-Type here: the browser adds the multipart boundary
    // required for Django to populate request.FILES.
    return client.post<ApiResponse<CSVImportPreview>>('/items/import/preview', data)
  },

  commitCsvImport: (file: File) => {
    const data = new FormData()
    data.append('file', file)
    // See previewCsvImport: Axios/browser must construct the multipart header.
    return client.post<ApiResponse<CSVImportResult>>('/items/import/commit', data)
  },

  delete: (id: string) =>
    client.delete<ApiResponse<Item>>(`/items/${encodeURIComponent(id)}`),

  history: (id: string) =>
    client.get<ApiResponse<unknown[]>>(`/items/${encodeURIComponent(id)}/history`),

  similarStats: (id: string) =>
    client.get<ApiResponse<Array<{ modelOrMake: string; count: number }>>>(
      `/items/${encodeURIComponent(id)}/similar_items`
    ),

  similarInstances: (itemName: string, itemModel: string, roomId: string) =>
    client.get<ApiResponse<ItemReport[]>>(
      `/items/similar/${[itemName, itemModel, roomId].map(encodeURIComponent).join('/')}`
    ),

  common: (page: string, categoryId?: string) => {
    const url = categoryId
      ? `/items/common_items/${encodeURIComponent(categoryId)}/${encodeURIComponent(page)}`
      : `/items/common_items/${encodeURIComponent(page)}`
    return client.get<ApiResponse<PaginatedCommonItems>>(url)
  },

  bulkDelete: (itemIds: string[]) =>
    client.delete<ApiResponse<Record<string, unknown>>>('/items/similar/bulk', { data: { item_ids: itemIds } }),

  bulkStatus: (itemIds: string[], statusId: string) =>
    client.patch<ApiResponse<Record<string, unknown>>>('/items/similar/bulk', { item_ids: itemIds, statusId }, { params: { action: 'status' } }),

  bulkMoveRoom: (itemIds: string[], newRoomId: string) =>
    client.patch<ApiResponse<Record<string, unknown>>>('/items/similar/bulk', { item_ids: itemIds, new_room_id: newRoomId }, { params: { action: 'room' } }),

  sources: () =>
    client.get<ApiResponse<Array<{ sourceId: string; sourceName: string }>>>('/items/item_source'),

  statuses: () =>
    client.get<ApiResponse<Array<{ statusId: string; statusName: string }>>>('/items/item_status'),
}
