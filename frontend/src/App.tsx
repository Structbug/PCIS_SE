import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom'
import type { ReactNode } from 'react'
import { AuthProvider, useAuth } from './hooks/useAuth'

import { Layout } from './components/layout/Layout'
import Login from './pages/Login'
import Dashboard from './pages/Dashboard'
import ItemList from './pages/Items/ItemList'
import ItemDetail from './pages/Items/ItemDetail'
import ItemCreate from './pages/Items/ItemCreate'
import RoomList from './pages/Rooms/RoomList'
import FloorList from './pages/Floors/FloorList'
import RoomTypeList from './pages/RoomTypes/RoomTypeList'
import DepartmentList from './pages/Departments/DepartmentList'
import CategoryList from './pages/Categories/CategoryList'
import ActivityLogs from './pages/ActivityLogs/ActivityLogs'
import UserList from './pages/Users/UserList'
function RequireAdmin({ children }: { children: ReactNode }) {
  const { isAdmin } = useAuth()
  if (!isAdmin) return <Navigate to="/" replace />
  return <>{children}</>
}

function AppRoutes() {
  const { user, loading } = useAuth()

  if (loading) return <div style={{ padding: 24, color: 'var(--text-muted)' }}>Loading...</div>

  if (!user) {
    return (
      <Routes>
        <Route path="/login" element={<Login />} />
        <Route path="*" element={<Navigate to="/login" replace />} />
      </Routes>
    )
  }

  return (
    <Routes>
      <Route element={<Layout />}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/items" element={<ItemList />} />
        <Route path="/items/new" element={<ItemCreate />} />
        <Route path="/items/:id" element={<ItemDetail />} />
        <Route path="/rooms" element={<RoomList />} />
        <Route path="/departments" element={<DepartmentList />} />
        <Route path="/categories" element={<CategoryList />} />
        <Route path="/floors" element={<FloorList />} />
        <Route path="/room-types" element={<RoomTypeList />} />
        <Route path="/activity-logs" element={<RequireAdmin><ActivityLogs /></RequireAdmin>} />
        <Route path="/users" element={<RequireAdmin><UserList /></RequireAdmin>} />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Route>
    </Routes>
  )
}

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <AppRoutes />
      </AuthProvider>
    </BrowserRouter>
  )
}
