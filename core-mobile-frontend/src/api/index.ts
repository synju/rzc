import axios from 'axios'

const api = axios.create({
  baseURL: import.meta.env.VITE_API_URL || 'http://localhost:8001',
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  const token = localStorage.getItem('rzc_token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      localStorage.removeItem('rzc_token')
      localStorage.removeItem('rzc_user')
      window.location.href = '/login'
    }
    return Promise.reject(error)
  }
)

export const authApi = {
  googleLogin: () => `${api.defaults.baseURL}/auth/google/login`,

  getMe: () => api.get('/auth/me'),

  logout: () => {
    localStorage.removeItem('rzc_token')
    localStorage.removeItem('rzc_user')
  }
}

export const walletApi = {
  getWallets: () => api.get('/wallet/'),

  createWallet: (name: string) => api.post('/wallet/create', { name }),

  switchWallet: (walletId: string) => api.post(`/wallet/switch/${walletId}`),

  renameWallet: (walletId: string, name: string) => api.patch(`/wallet/${walletId}`, { name }),

  deleteWallet: (walletId: string) => api.delete(`/wallet/${walletId}`),

  recreateWallet: (walletId: string) => api.post(`/wallet/recreate/${walletId}`),

  getBalance: () => api.get('/wallet/balance'),

  syncBalance: () => api.post('/wallet/sync-balance')
}

export const transactionsApi = {
  send: (toAddress: string, amount: number) => api.post('/transactions/send', {
    to_address: toAddress,
    amount: amount
  }),

  internalTransfer: (toWalletId: string, amount: number) => api.post('/transactions/internal-transfer', {
    to_wallet_id: toWalletId,
    amount: amount
  }),

  getHistory: () => api.get('/transactions/history')
}

export const recipientsApi = {
  getAll: () => api.get('/recipients/'),

  add: (name: string, address: string) => api.post('/recipients/', {
    name,
    address
  }),

  remove: (id: string) => api.delete(`/recipients/${id}`)
}

export default api
