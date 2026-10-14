const API_BASE = '/api'

export type Store = {
  id: number
  name: string
  api_endpoint: string
  onboarded: boolean
  last_synced_at: string | null
  created_at: string
}

export type ProductListing = {
  product_name: string
  store_name: string
  price: string
  last_updated: string
}

export type RefreshResult = {
  products_synced: number
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, init)
  if (!res.ok) {
    const body = await res.json().catch(() => null)
    const detail = typeof body?.detail === 'string' ? body.detail : `Request failed (${res.status})`
    throw new Error(detail)
  }
  return res.json() as Promise<T>
}

export function getProducts(searchText?: string) {
  const query = searchText ? `?${new URLSearchParams({ search_text: searchText })}` : ''
  return request<ProductListing[]>(`/products${query}`)
}

export function getStores() {
  return request<Store[]>('/stores')
}

export function refreshStore(storeId: number) {
  return request<RefreshResult>(`/stores/${storeId}/refresh`, { method: 'POST' })
}

export function refreshAllStores() {
  return request<RefreshResult>('/stores/refresh', { method: 'POST' })
}