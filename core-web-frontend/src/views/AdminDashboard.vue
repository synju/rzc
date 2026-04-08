<template>
  <div class="admin-dashboard">
    <header class="header">
      <div class="logo">RZC Admin</div>
      <div class="user-menu">
        <span class="email">{{ authStore.user?.email }}</span>
        <button @click="handleLogout" class="btn-logout">Logout</button>
      </div>
    </header>

    <main class="content">
      <div class="admin-card avax-card">
        <div class="card-header">
          <h2>Admin Wallets</h2>
          <button @click="syncBalances" class="btn-sync" :disabled="syncingAvax">
            {{ syncingAvax ? 'Syncing...' : 'Sync All' }}
          </button>
        </div>
        <div class="card-body">
          <div class="wallet-section">
            <h3>AVAX Relayer Wallet (Gas)</h3>
            <div class="address-row">
              <span class="label">Address:</span>
              <span class="value address">{{ adminWallet?.address }}</span>
            </div>
            <div class="balance-row">
              <span class="label">AVAX Balance:</span>
              <span class="value avax-balance">{{ formatAvax(adminWallet?.avax_balance) }} AVAX</span>
            </div>
            <div class="info-row">
              <span class="info">Gas cost per tx: ~0.00005 AVAX</span>
            </div>
          </div>
          
          <div class="wallet-section">
            <h3>RZC Wallet (Admin Holdings)</h3>
            <div class="address-row">
              <span class="label">Address:</span>
              <span class="value address">{{ adminWallet?.address }}</span>
            </div>
            <div class="balance-row">
              <span class="label">RZC Balance:</span>
              <span class="value rzc-balance">{{ formatRzc(adminRzcBalance) }} RZC</span>
            </div>
          </div>
        </div>
      </div>

      <div class="stats-section">
        <div class="stat-card">
          <span class="stat-value">{{ totalWallets }}</span>
          <span class="stat-label">Total Wallets</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ formatRzc(totalRzc) }}</span>
          <span class="stat-label">Total RZC in System</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ adminWallet?.avax_balance ? (Number(adminWallet.avax_balance) / 1e18 / 0.00005).toFixed(0) : 0 }}</span>
          <span class="stat-label">Txs Until Empty</span>
        </div>
      </div>

      <div class="admin-card rzc-card">
        <div class="card-header">
          <h2>RZC Token Info</h2>
        </div>
        <div class="card-body">
          <div class="info-row">
            <span class="label">Contract:</span>
            <span class="value address">0x8583645670154b3bc3f9c48a1864261fd1f26758</span>
          </div>
          <div class="info-row">
            <span class="label">Network:</span>
            <span class="value">Avalanche C-Chain</span>
          </div>
          <div class="info-row">
            <span class="label">Total Supply:</span>
            <span class="value">21,000,000 RZC</span>
          </div>
        </div>
      </div>

      <div class="actions-section">
        <h3>Admin Actions</h3>
        <button @click="syncAllWallets" class="btn btn-primary" :disabled="syncingAll">
          {{ syncingAll ? 'Syncing All...' : 'Sync All Wallet Balances' }}
        </button>
      </div>
    </main>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { adminApi, walletApi } from '../api'

const router = useRouter()
const authStore = useAuthStore()

const adminWallet = ref(null)
const adminRzcBalance = ref(0)
const totalWallets = ref(0)
const totalRzc = ref(0)
const syncingAvax = ref(false)
const syncingAll = ref(false)

const formatAvax = (balance) => {
  if (!balance) return '0'
  return (Number(balance) / 1e18).toFixed(6)
}

const formatRzc = (balance) => {
  if (!balance) return '0'
  return (Number(balance) / 1e18).toFixed(2)
}

const syncBalances = async () => {
  syncingAvax.value = true
  try {
    await Promise.all([
      adminApi.syncAvaxBalance(),
      adminApi.getRzcBalance()
    ])
    await loadData()
  } catch (e) {
    console.error('Failed to sync balances:', e)
  } finally {
    syncingAvax.value = false
  }
}

const syncAllWallets = async () => {
  syncingAll.value = true
  try {
    await walletApi.syncBalance()
    await loadData()
  } catch (e) {
    console.error('Failed to sync wallets:', e)
  } finally {
    syncingAll.value = false
  }
}

const loadData = async () => {
  try {
    const [walletRes, rzcRes] = await Promise.all([
      adminApi.getWallet(),
      adminApi.getRzcBalance()
    ])
    adminWallet.value = walletRes.data
    adminRzcBalance.value = rzcRes.data.rzc_balance
  } catch (e) {
    console.error('Failed to load admin wallet:', e)
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/')
}

onMounted(() => {
  loadData()
})
</script>

<style scoped>
.admin-dashboard {
  min-height: 100vh;
  background: #0d0d14;
  color: #fff;
}

.header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1.25rem 2rem;
  background: #13131f;
  border-bottom: 1px solid #1f1f2e;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffd700;
  letter-spacing: 2px;
}

.user-menu {
  display: flex;
  align-items: center;
  gap: 1rem;
}

.email {
  color: #888;
  font-size: 0.9rem;
}

.btn-logout {
  background: transparent;
  border: 1px solid #333;
  color: #666;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
}

.content {
  max-width: 800px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.admin-card {
  background: #13131f;
  border-radius: 16px;
  padding: 1.5rem;
  margin-bottom: 1.5rem;
  border: 1px solid #1f1f2e;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.card-header h2 {
  color: #ffd700;
  font-size: 1.1rem;
  margin: 0;
}

.btn-sync {
  background: #1f1f2e;
  border: 1px solid #333;
  color: #fff;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-sync:hover:not(:disabled) {
  background: #2a2a40;
}

.btn-sync:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.wallet-section {
  padding-top: 1rem;
  border-top: 1px solid #1f1f2e;
}

.wallet-section:first-child {
  padding-top: 0;
  border-top: none;
}

.wallet-section h3 {
  color: #ffd700;
  font-size: 0.95rem;
  margin: 0 0 0.75rem;
}

.address-row, .balance-row, .info-row {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.label {
  color: #666;
  font-size: 0.8rem;
}

.value {
  color: #fff;
  font-size: 0.95rem;
}

.value.address {
  font-family: monospace;
  font-size: 0.8rem;
  word-break: break-all;
}

.value.avax-balance {
  font-size: 1.5rem;
  font-weight: 700;
  color: #00d4ff;
}

.value.rzc-balance {
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffd700;
}

.info {
  color: #555;
  font-size: 0.8rem;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 1rem;
  margin-bottom: 1.5rem;
}

.stat-card {
  background: #13131f;
  border-radius: 12px;
  padding: 1.25rem;
  text-align: center;
  border: 1px solid #1f1f2e;
}

.stat-value {
  display: block;
  font-size: 1.75rem;
  font-weight: 700;
  color: #ffd700;
  margin-bottom: 0.25rem;
}

.stat-label {
  color: #666;
  font-size: 0.75rem;
}

.rzc-card .info-row {
  flex-direction: row;
  justify-content: space-between;
}

.actions-section {
  background: #13131f;
  border-radius: 16px;
  padding: 1.5rem;
  border: 1px solid #1f1f2e;
}

.actions-section h3 {
  color: #ffd700;
  margin: 0 0 1rem;
  font-size: 1rem;
}

.btn {
  padding: 0.875rem 1.5rem;
  border-radius: 10px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.95rem;
  width: 100%;
}

.btn-primary {
  background: #ffd700;
  color: #0d0d14;
}

.btn-primary:hover:not(:disabled) {
  background: #ffed4a;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}
</style>
