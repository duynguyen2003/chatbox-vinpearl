import { BrowserRouter } from 'react-router-dom'
import { AuthProvider } from './Frontend/context/AuthContext'
import { LanguageProvider } from './Frontend/context/LanguageContext'
import AppRoutes from './Frontend/routes/AppRoutes'

export default function App() {
  return (
    <div translate="no" className="notranslate">
      <BrowserRouter>
        <LanguageProvider>
          <AuthProvider>
            <AppRoutes />
          </AuthProvider>
        </LanguageProvider>
      </BrowserRouter>
    </div>
  )
}