import { useCallback, useEffect, useState } from 'react'
import { getStores, refreshAllStores, refreshStore, type Store } from '../api/api'

function formatSyncedAt(value: string | null) {
  // Backend stores naive UTC timestamps, so mark them as UTC before converting.
  return value ? new Date(`${value}Z`).toLocaleString() : 'Never'
}

function StoresPage() {
  const [stores, setStores] = useState<Store[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const [message, setMessage] = useState<string | null>(null)
  const [refreshing, setRefreshing] = useState<number | 'all' | null>(null)

const loadStores = useCallback(async () => {
  try {
    setStores(await getStores())
  } catch (e) {
    setError((e as Error).message)
  } finally {
    setLoading(false)
  }
}, [])

  useEffect(() => {
    loadStores()
  }, [loadStores])

  const runRefresh = async (target: number | 'all') => {
    setRefreshing(target)
    setMessage(null)
    setError(null)
    try {
      const result = target === 'all' ? await refreshAllStores() : await refreshStore(target)
      setMessage(`Updated ${result.products_synced} product price(s).`)
      await loadStores()
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setRefreshing(null)
    }
  }

  const busy = refreshing !== null

  return (
    <section>
      <div className="flex items-center justify-between mb-4">
        <h1 className="text-3xl font-semibold">Stores</h1>
        <button
          onClick={() => runRefresh('all')}
          disabled={busy}
          className="bg-blue-600 text-white rounded-lg px-4 py-2 hover:bg-blue-700 disabled:opacity-50"
        >
          {refreshing === 'all' ? 'Updating all...' : 'Bulk update prices'}
        </button>
      </div>

      {message && <p className="text-green-700 mb-4">{message}</p>}
      {error && <p className="text-red-600 mb-4">{error}</p>}

      {loading ? (
        <p className="text-gray-500">Loading...</p>
      ) : stores.length === 0 ? (
        <p className="text-gray-500">No stores registered.</p>
      ) : (
        <ul className="divide-y divide-gray-200 border border-gray-200 rounded-lg">
          {stores.map((store) => (
            <li key={store.id} className="flex items-center justify-between px-4 py-3">
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-medium">{store.name}</span>
                  <span
                    className={`text-xs rounded-full px-2 py-0.5 ${
                      store.onboarded ? 'bg-green-100 text-green-700' : 'bg-gray-100 text-gray-500'
                    }`}
                  >
                    {store.onboarded ? 'Onboarded' : 'Pending'}
                  </span>
                </div>
                <p className="text-sm text-gray-500">Last synced: {formatSyncedAt(store.last_synced_at)}</p>
              </div>
              <button
                onClick={() => runRefresh(store.id)}
                disabled={busy}
                className="border border-gray-300 rounded-lg px-3 py-1.5 text-sm hover:bg-gray-50 disabled:opacity-50"
              >
                {refreshing === store.id ? 'Updating...' : 'Force update price'}
              </button>
            </li>
          ))}
        </ul>
      )}
    </section>
  )
}

export default StoresPage