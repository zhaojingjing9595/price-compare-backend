import { useEffect, useState, type FormEvent } from 'react'
import { getProducts, type ProductListing } from '../api/api'

function ProductsPage() {
  const [products, setProducts] = useState<ProductListing[]>([])
  const [input, setInput] = useState('')
  const [search, setSearch] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)

  useEffect(() => {
    let ignore = false

    async function loadProducts() {
      try {
        const data = await getProducts(search)
        if (ignore) return
        setProducts(data)
        setError(null)
      } catch (e) {
        if (!ignore) setError((e as Error).message)
      } finally {
        if (!ignore) setLoading(false)
      }
    }

    loadProducts()
    return () => {
      ignore = true
    }
  }, [search])

  const handleSubmit = (e: FormEvent) => {
    e.preventDefault()
    const next = input.trim()
    if (next === search) return
    setLoading(true)
    setSearch(next)
  }

  return (
    <section>
      <h1 className="text-3xl font-semibold mb-4">Products</h1>

      <form onSubmit={handleSubmit} className="flex gap-2 mb-4">
        <input
          type="search"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Search products..."
          className="flex-1 border border-gray-300 rounded-lg px-3 py-2 focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
        <button type="submit" className="bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700">
          Search
        </button>
      </form>

      {error && <p className="text-red-600 mb-4">{error}</p>}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : products.length === 0 ? (
        <p className="text-gray-500">No products found.</p>
      ) : (
        <ul className="divide-y divide-gray-200 border border-gray-200 rounded-lg">
          {products.map((p) => (
            <li key={`${p.store_name}-${p.product_name}`} className="flex items-center justify-between px-4 py-3">
              <div>
                <p className="font-medium">{p.product_name}</p>
                <p className="text-sm text-gray-500">{p.store_name}</p>
              </div>
              <span className="font-semibold">${p.price}</span>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default ProductsPage