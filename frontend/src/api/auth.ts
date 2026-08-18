import client from './client'
import type { ApiResponse, CurrentUser, LoginCredentials, PaginatedUsers, TokenPair, User } from '../types'

export const authApi = {
  login: (data: LoginCredentials) =>
    client.post<ApiResponse<CurrentUser>>('/users/login', data),

  logout: () => client.post<ApiResponse<User>>('/users/logout'),

  currentUser: () => client.get<ApiResponse<CurrentUser>>('/users/current-user'),

  refresh: () => client.post<TokenPair>('/users/refresh'),

  getActiveUsers: (page: string) =>
    client.get<ApiResponse<PaginatedUsers>>(`/users/active/${encodeURIComponent(page)}`),

  searchUsers: (username: string, page: string) =>
    client.get<ApiResponse<PaginatedUsers>>(
      `/users/${encodeURIComponent(username)}/${encodeURIComponent(page)}`
    ),

  register: (data: Partial<User> & { password: string }) =>
    client.post<ApiResponse<User>>('/users/register', data),

  changePassword: (data: { currentPassword: string; newPassword: string }) =>
    client.patch<ApiResponse<null>>('/users/change-password', data),

  editProfile: (data: Partial<User>) =>
    client.patch<ApiResponse<User>>('/users/edit-profile', data),

  deleteUser: (userId: string) =>
    client.delete<ApiResponse<User>>(`/users/${encodeURIComponent(userId)}`),
}
