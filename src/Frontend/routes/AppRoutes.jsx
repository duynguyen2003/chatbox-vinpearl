import { Navigate, Route, Routes } from 'react-router-dom'
import ChatWidget from '../components/ChatWidget'
import Footer from '../components/Footer'
import Header from '../components/Header'
import About from '../pages/About'
import Chatbot from '../pages/Chatbot'
import Home from '../pages/Home'
import HotelDetail from '../pages/HotelDetail'
import Login from '../pages/Login'
import Promotions from '../pages/Promotions'
import Register from '../pages/Register'
import SearchResults from '../pages/SearchResults'
import Ticket from '../pages/Ticket'
import Regulations from '../pages/Regulations'
import '../styles/routes/AppRoutes.css'

function AppLayout({ children }) {
  return (
    <div className="app-routes">
      <Header />
      <main className="app-routes__main">{children}</main>
      <Footer />
      <ChatWidget />
    </div>
  )
}

function AppRoutes() {
  return (
    <Routes>
      <Route path="/" element={<AppLayout><Home /></AppLayout>} />
      <Route path="/about" element={<AppLayout><About /></AppLayout>} />
      <Route path="/search" element={<AppLayout><SearchResults /></AppLayout>} />
      <Route path="/hotels/:hotelId" element={<AppLayout><HotelDetail /></AppLayout>} />
      <Route path="/regulations" element={<AppLayout><Regulations /></AppLayout>} />
      <Route path="/promotions" element={<AppLayout><Promotions /></AppLayout>} />
      <Route path="/chat" element={<AppLayout><Chatbot /></AppLayout>} />
      <Route path="/chatbot" element={<AppLayout><Chatbot /></AppLayout>} />
      <Route path="/support" element={<AppLayout><Ticket /></AppLayout>} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}

export default AppRoutes
