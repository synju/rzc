import { defineStore } from 'pinia'
import { authApi, walletApi } from '../api'

interface Wallet {
  id: string
  name: string
  address: string | null
  balance: number
  is_active: boolean
}

interface WalletsResponse {
  wallets: Wallet[]
  active_wallet: Wallet | null
}

export const useAuthStore = defineStore('auth', {
  state: () => ({
    user: JSON.parse(localStorage.getItem('rzc_user') || 'null') as any,
    token: localStorage.getItem('rzc_token') || null as string | null,
    wallets: [] as Wallet[],
    activeWallet: null as Wallet | null,
    loading: false,
    error: null as string | null
  }),

  getters: {
    isAuthenticated: (state) => !!state.token,
    hasWallet: (state) => !!state.activeWallet?.address,
    isAdmin: (state) => state.user?.is_admin === true
  },

  actions: {
    async checkAuth() {
      if (!this.token) return false
      try {
        const response = await authApi.getMe()
        this.user = response.data
        return true
      } catch (error: any) {
        this.logout()
        return false
      }
    },

    async loadWallets() {
      if (!this.token) return
      try {
        const response = await walletApi.getWallets()
        const data = response.data as WalletsResponse
        this.wallets = data.wallets
        this.activeWallet = data.active_wallet
      } catch (error: any) {
        if (error.response?.status === 404) {
          this.wallets = []
          this.activeWallet = null
        }
      }
    },

    async createWallet(name: string = 'Wallet') {
      this.loading = true
      this.error = null
      try {
        const response = await walletApi.createWallet(name)
        const newWallet: Wallet = {
          id: response.data.id,
          name: response.data.name,
          address: response.data.address,
          balance: 0,
          is_active: true
        }
        this.wallets.push(newWallet)
        this.activeWallet = newWallet
        return response.data
      } catch (error: any) {
        this.error = error.response?.data?.detail || 'Failed to create wallet'
        throw error
      } finally {
        this.loading = false
      }
    },

    async switchWallet(walletId: string) {
      this.loading = true
      this.error = null
      try {
        await walletApi.switchWallet(walletId)
        await this.loadWallets()
      } catch (error: any) {
        this.error = error.response?.data?.detail || 'Failed to switch wallet'
        throw error
      } finally {
        this.loading = false
      }
    },

    async deleteWallet(walletId: string) {
      this.loading = true
      this.error = null
      try {
        await walletApi.deleteWallet(walletId)
        this.wallets = this.wallets.filter(w => w.id !== walletId)
        if (this.activeWallet?.id === walletId) {
          this.activeWallet = this.wallets[0] || null
        }
      } catch (error: any) {
        this.error = error.response?.data?.detail || 'Failed to delete wallet'
        throw error
      } finally {
        this.loading = false
      }
    },

    logout() {
      authApi.logout()
      this.user = null
      this.token = null
      this.wallets = []
      this.activeWallet = null
    },

    setAuth(token: string, user: any) {
      this.token = token
      this.user = user
      localStorage.setItem('rzc_token', token)
      localStorage.setItem('rzc_user', JSON.stringify(user))
    }
  }
})
