import { BrowserRouter, Routes, Route } from 'react-router-dom'
import HomePage from './pages/HomePage'
import StrategyPage from './pages/StrategyPage'
import './App.css'

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/s/:sid" element={<StrategyPage />} />
      </Routes>
    </BrowserRouter>
  )
}
