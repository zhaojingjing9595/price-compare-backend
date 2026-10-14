import { Routes, Route } from 'react-router-dom'
import Navbar from './components/Navbar'
import WelcomePage from './pages/WelcomePage'
import ProductsPage from './pages/ProductsPage'
import StoresPage from './pages/StoresPage'

function App() {
  return (
    <>
      <Navbar />
      <main className="max-w-3xl mx-auto p-8">
        <Routes>
          <Route path="/" element={<WelcomePage />} />
          <Route path="/products" element={<ProductsPage />} />
          <Route path="/stores" element={<StoresPage />} />
        </Routes>
      </main>
    </>
  )
}

export default App