import { Navigate, Route, Routes, useLocation } from 'react-router-dom'
import Layout from './components/Layout'
import { useAuth } from './lib/auth'
import AuthPage from './pages/Auth'
import Landing from './pages/Landing'
import { Contact, Creator, Privacy, Terms } from './pages/Legal'
import Onboarding from './pages/Onboarding'
import Dashboard from './pages/Dashboard'
import Capture from './pages/Capture'
import History from './pages/History'
import MealDetail from './pages/MealDetail'
import NutritionInsights from './pages/NutritionInsights'
import HealthProfile from './pages/HealthProfile'
import ModelInsights from './pages/ModelInsights'
import Settings from './pages/Settings'
import Advisor from './pages/Advisor'
import About from './pages/About'
import { Spinner } from './components/ui'

function Protected({ children }: { children: JSX.Element }) {
  const { user, loading } = useAuth()
  const loc = useLocation()
  if (loading) return <div className="h-full grid place-items-center"><Spinner /></div>
  if (!user) return loc.pathname === '/' ? <Landing /> : <Navigate to="/login" replace state={{ from: loc.pathname }} />
  if (!user.onboarded && loc.pathname !== '/onboarding') return <Navigate to="/onboarding" replace />
  return children
}

export default function App() {
  return (
    <Routes>
      <Route path="/login" element={<AuthPage mode="login" />} />
      <Route path="/privacy" element={<Privacy />} />
      <Route path="/terms" element={<Terms />} />
      <Route path="/contact" element={<Contact />} />
      <Route path="/creator" element={<Creator />} />
      <Route path="/register" element={<AuthPage mode="register" />} />
      <Route path="/onboarding" element={<Protected><Onboarding /></Protected>} />
      <Route element={<Protected><Layout /></Protected>}>
        <Route path="/" element={<Dashboard />} />
        <Route path="/capture" element={<Capture />} />
        <Route path="/history" element={<History />} />
        <Route path="/meals/:id" element={<MealDetail />} />
        <Route path="/insights" element={<NutritionInsights />} />
        <Route path="/profile" element={<HealthProfile />} />
        <Route path="/ai" element={<ModelInsights />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/advisor" element={<Advisor />} />
        <Route path="/about" element={<About />} />
      </Route>
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
