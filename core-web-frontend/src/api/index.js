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

  createWallet: (name) => api.post('/wallet/create', { name }),

  switchWallet: (walletId) => api.post(`/wallet/switch/${walletId}`),

  renameWallet: (walletId, name) => api.patch(`/wallet/${walletId}`, { name }),

  deleteWallet: (walletId) => api.delete(`/wallet/${walletId}`),

  recreateWallet: (walletId) => api.post(`/wallet/recreate/${walletId}`),

  getBalance: () => api.get('/wallet/balance'),

  syncBalance: () => api.post('/wallet/sync-balance')
}

export const transactionsApi = {
  send: (toAddress, amount) => api.post('/transactions/send', {
    to_address: toAddress,
    amount: amount
  }),

  internalTransfer: (toWalletId, amount) => api.post('/transactions/internal-transfer', {
    to_wallet_id: toWalletId,
    amount: amount
  }),

  getHistory: () => api.get('/transactions/history'),

  syncTransactions: () => api.post('/transactions/sync-transactions')
}

export const recipientsApi = {
  getAll: () => api.get('/recipients/'),

  add: (name, address) => api.post('/recipients/', {
    name,
    address
  }),

  remove: (id) => api.delete(`/recipients/${id}`)
}

export const adminApi = {
  getWallet: () => api.get('/admin/wallet'),

  syncAvaxBalance: () => api.post('/admin/wallet/sync-balance'),

  getRzcBalance: () => api.get('/admin/wallet/rzc-balance'),

  getAllWallets: () => api.get('/admin/wallets'),

  getAdminTransactions: () => api.get('/admin/transactions'),

  syncAdminTransactions: () => api.post('/admin/sync-transactions')
}

export default api
