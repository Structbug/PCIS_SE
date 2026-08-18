export interface ApiResponse<T = unknown> {
  statusCode: number
  data: T
  message: string
  success: boolean
}

export interface LoginCredentials {
  username: string
  password: string
}

export interface User {
  _id: string
  username: string
  email: string
  phone_number: string
  role: 'Admin' | 'User'
  isActive: boolean
  createdAt: string
  updatedAt: string
}

export interface CurrentUser {
  user: User
  accessTokenExp: number
  refreshTokenExp: number
}

export interface TokenPair {
  access: string
  refresh: string
}

export interface AccessRequest {
  _id: string
  fullName: string
  email: string
  department: string
  rollNo?: string | null
  description?: string | null
  status: 'Pending' | 'Approved' | 'Denied'
  createdAt: string
  updatedAt: string
}

export interface AccessRequestsResponse {
  requests: AccessRequest[]
  pendingCount: number
}

export interface BlockedRequester {
  _id: string
  email: string
  createdBy: string | null
  createdAt: string
  updatedAt: string
}

export interface BlockedRequestersResponse {
  blockedRequesters: BlockedRequester[]
  totalBlocked: number
}

export interface Floor {
  _id: string
  floorName: string
  departmentId?: string | null
  departmentName?: string | null
  isActive: boolean
  createdBy: string | null
  createdAt: string
  updatedAt: string
}

export interface Department {
  _id: string
  departmentName: string
  isActive: boolean
  createdBy: string | null
  createdAt: string
  updatedAt: string
}

export interface RoomType {
  _id: string
  roomTypeName: string
  departmentId?: string | null
  departmentName?: string | null
  isActive: boolean
  createdBy: string | null
  createdAt: string
  updatedAt: string
}

export interface Category {
  _id: string
  categoryName: string
  isActive: boolean
  createdBy: string | null
  createdAt: string
  updatedAt: string
}

export interface CategoryDescription {
  _id: string
  categoryName: string
  totalItems: number
  creatorUsername: string | null
  createdAt: string
  updatedAt: string
}

export interface PaginatedCategories {
  totalCategories: number
  categories: CategoryDescription[]
}

export interface Room {
  _id: string
  roomName: string
  roomNo?: string
  roomFloorId: string
  roomTypeId: string
  isActive: boolean
  createdAt: string
  updatedAt: string
  floorName?: string
  roomFloorName?: string
  roomTypeName?: string
  departmentId?: string | null
  departmentName?: string | null
  allottedTo?: string
}

export interface Item {
  _id: string
  isActive: boolean
  itemName: string
  itemDescription: string
  itemModelNumberOrMake: string
  itemSource: 'Purchase' | 'Donation'
  itemCost: number | null
  itemAcquiredDate: string | null
  itemSerialNumber: string
  itemStatus: 'Working' | 'Repairable' | 'Not working'
  itemCategory: string | null
  itemSubCategory: string | null
  itemFloor: string
  itemRoom: string
  createdBy: string
  creatorUsername: string
  createdAt: string
  updatedAt: string
  deactivatedAt: string | null
  categoryName?: string
  subCategoryName?: string
  floorName?: string
  roomName?: string
}

export interface ItemReport {
  _id: string
  isActive: boolean
  itemName: string
  itemDescription: string
  itemModelNumberOrMake: string
  itemSource: 'Purchase' | 'Donation'
  itemCost: number | null
  itemAcquiredDate: string | null
  itemSerialNumber: string
  itemStatus: 'Working' | 'Repairable' | 'Not working'
  quantity?: number
  itemCategory: string | null
  itemSubCategory: string | null
  itemFloor: string
  itemRoom: string
  createdBy: string
  creatorUsername: string
  createdAt: string
  updatedAt: string
  deactivatedAt: string | null
  categoryName: string | null
  subCategoryName: string | null
  floorName: string
  departmentId?: string | null
  departmentName?: string | null
  roomName: string
}

export interface InventoryStats {
  no_total_items: number
  no_working: number
  no_repairable: number
  no_not_working: number
  no_total_items_till_last_month: number
  inventory_total_value: number
}

export interface ActivityLog {
  _id: string
  action: string
  entityType: string
  entityId: string | null
  entityName: string | null
  description: string | null
  performedByName: string | null
  performedByRole: string | null
  performedBy: string | null
  changes: Record<string, unknown> | null
  created_at: string
}

export interface PaginatedLogs {
  totalLogs: number
  logs: ActivityLog[]
}

export interface PaginatedItems {
  totalItems: number
  items: ItemReport[]
}

export interface CursorPaginatedItems {
  items: ItemReport[]
  nextCursor: string | null
}

export interface CommonItem {
  itemName: string
  itemModel: string
  workingCount: number
  repairableCount: number
  notWorkingCount: number
  totalCount: number
  categoryName: string
  itemCategoryId: string
}

export interface PaginatedCommonItems {
  totalItems: number
  itemData: CommonItem[]
}

export interface PaginatedUsers {
  totalUsers: number
  users: User[]
}

export interface PaginatedRooms {
  totalRooms: number
  rooms: Room[]
}
