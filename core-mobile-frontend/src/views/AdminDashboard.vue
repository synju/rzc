<template>
  <div class="admin-dashboard">
    <header class="header">
      <div class="logo">RZC Admin</div>
      <div class="header-buttons">
        <button @click="goToDashboard" class="btn-back">Dashboard</button>
        <button @click="handleLogout" class="btn-logout">Logout</button>
      </div>
    </header>

    <main class="content">
      <div class="admin-card avax-card">
        <div class="card-header">
          <h2>Admin Wallets</h2>
          <button @click="syncBalances" class="btn-sync" :disabled="syncingAvax">
            {{ syncingAvax ? 'Syncing...' : 'Sync' }}
          </button>
        </div>
        <div class="card-body">
          <div class="wallet-section">
            <h3>AVAX Relayer (Gas)</h3>
            <div class="info-row">
              <span class="label">Address:</span>
              <span class="value address" @click="copyAddress(adminWallet?.address)">
                {{ adminWallet?.address || 'Loading...' }}
              </span>
            </div>
            <div class="info-row">
              <span class="label">AVAX Balance:</span>
              <span class="value avax-balance">{{ formatAvax(adminWallet?.avax_balance) }} AVAX</span>
            </div>
            <div class="info-row">
              <span class="info">Gas per tx: ~0.00005 AVAX</span>
            </div>
          </div>
          
          <div class="wallet-section">
            <h3>RZC Holdings</h3>
            <div class="info-row">
              <span class="label">Address:</span>
              <span class="value address">{{ adminWallet?.address || 'Loading...' }}</span>
            </div>
            <div class="info-row">
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
          <span class="stat-label">Total RZC</span>
        </div>
        <div class="stat-card">
          <span class="stat-value">{{ adminWallet?.avax_balance ? (Number(adminWallet.avax_balance) / 1e18 / 0.00005).toFixed(0) : 0 }}</span>
          <span class="stat-label">Txs Left</span>
        </div>
      </div>

      <div class="admin-card rzc-card">
        <div class="card-header">
          <h2>RZC Token</h2>
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

      <div class="admin-card">
        <h3>Actions</h3>
        <button @click="syncAllWallets" class="btn btn-primary btn-full" :disabled="syncingAll">
          {{ syncingAll ? 'Syncing...' : 'Sync All Wallet Balances' }}
        </button>
      </div>

      <div class="transactions-section">
        <div class="card-header">
          <h3>Recent Transactions</h3>
          <button @click="syncTransactions" class="btn-sync" :disabled="syncingTxs">
            {{ syncingTxs ? 'Syncing...' : 'Refresh' }}
          </button>
        </div>
        <div v-if="transactions.length === 0" class="no-tx">
          <p>No transactions yet</p>
        </div>
        <div v-else class="tx-list">
          <div v-for="tx in transactions" :key="tx.tx_hash" class="tx-item">
            <div class="tx-icon" :class="tx.type">
              {{ tx.type === 'received' ? '📥' : '📤' }}
            </div>
            <div class="tx-details">
              <span class="tx-type-label">{{ tx.type === 'received' ? 'Received' : 'Sent' }} {{ tx.token || 'RZC' }}</span>
              <span class="tx-hash">{{ tx.tx_hash.slice(0, 8) }}...{{ tx.tx_hash.slice(-6) }}</span>
              <a v-if="tx.tx_hash.startsWith('0x')" :href="`https://snowtrace.io/tx/${tx.tx_hash}`" target="_blank" class="snowtrace-link">View on Snowtrace</a>
              <span v-else class="internal-label">Internal Transfer</span>
            </div>
            <div class="tx-amount" :class="tx.type">
              {{ tx.type === 'received' ? '+' : '-' }}{{ tx.token === 'AVAX' ? formatAvax(tx.amount) : formatRzc(tx.amount) }} {{ tx.token || 'RZC' }}
            </div>
          </div>
        </div>
      </div>
    </main>

    <div v-if="showCopiedToast" class="toast">
      <p>Address copied!</p>
      <button @click="showCopiedToast = false" class="btn btn-primary">OK</button>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { adminApi, walletApi } from '../api'

const router = useRouter()
const authStore = useAuthStore()

const adminWallet = ref<any>(null)
const adminRzcBalance = ref(0)
const totalWallets = ref(0)
const totalRzc = ref(0)
const syncingAvax = ref(false)
const syncingAll = ref(false)
const syncingTxs = ref(false)
const transactions = ref<any[]>([])
const showCopiedToast = ref(false)

const formatAvax = (balance: any) => {
  if (!balance) return '0'
  return (Number(balance) / 1e18).toFixed(6)
}

const formatRzc = (balance: any) => {
  if (!balance) return '0'
  return (Number(balance) / 1e18).toFixed(6)
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
    const [walletRes, rzcRes, statsRes] = await Promise.all([
      adminApi.getWallet(),
      adminApi.getRzcBalance(),
      adminApi.getAllWallets()
    ])
    adminWallet.value = walletRes.data
    adminRzcBalance.value = rzcRes.data.rzc_balance
    totalWallets.value = statsRes.data.total_wallets
    totalRzc.value = statsRes.data.total_rzc
  } catch (e) {
    console.error('Failed to load admin wallet:', e)
  }
}

const loadTransactions = async () => {
  try {
    const response = await adminApi.getAdminTransactions()
    transactions.value = response.data.transactions || []
  } catch (e) {
    console.error('Failed to load transactions:', e)
  }
}

const syncTransactions = async () => {
  syncingTxs.value = true
  try {
    await adminApi.syncAdminTransactions()
    await loadTransactions()
  } catch (e) {
    console.error('Failed to sync transactions:', e)
  } finally {
    syncingTxs.value = false
  }
}

const copyAddress = async (address: string) => {
  if (address) {
    await navigator.clipboard.writeText(address)
    showCopiedToast.value = true
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/')
}

const goToDashboard = () => {
  router.push('/dashboard')
}

onMounted(() => {
  loadData()
  loadTransactions()
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
  padding: 1rem 1rem;
  background: #13131f;
  border-bottom: 1px solid #1f1f2e;
}

.logo {
  font-size: 1.2rem;
  font-weight: 700;
  color: #ffd700;
  letter-spacing: 2px;
}

.header-buttons {
  display: flex;
  gap: 0.5rem;
}

.btn-back, .btn-logout {
  background: #ffd700;
  border: none;
  color: #0d0d14;
  padding: 0.4rem 0.8rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
  font-weight: 600;
}

.content {
  padding: 1rem;
  max-width: 600px;
  margin: 0 auto;
}

.admin-card {
  background: #13131f;
  border-radius: 12px;
  padding: 1rem;
  margin-bottom: 1rem;
  border: 1px solid #1f1f2e;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.card-header h2, .card-header h3 {
  color: #ffd700;
  font-size: 0.9rem;
  margin: 0;
}

.card-header h3 {
  font-size: 0.8rem;
  margin-bottom: 0.5rem;
}

.btn-sync {
  background: #1f1f2e;
  border: 1px solid #333;
  color: #fff;
  padding: 0.4rem 0.75rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.75rem;
}

.btn-sync:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.wallet-section {
  padding-top: 0.75rem;
  border-top: 1px solid #1f1f2e;
}

.wallet-section:first-child {
  padding-top: 0;
  border-top: none;
}

.wallet-section h3 {
  color: #ffd700;
  font-size: 0.8rem;
  margin: 0 0 0.5rem;
}

.info-row {
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
}

.label {
  color: #666;
  font-size: 0.7rem;
}

.value {
  color: #fff;
  font-size: 0.85rem;
}

.value.address {
  font-family: monospace;
  font-size: 0.7rem;
  word-break: break-all;
  cursor: pointer;
  color: #00d4ff;
}

.value.avax-balance {
  font-size: 1.2rem;
  font-weight: 700;
  color: #00d4ff;
}

.value.rzc-balance {
  font-size: 1.2rem;
  font-weight: 700;
  color: #ffd700;
}

.info {
  color: #555;
  font-size: 0.7rem;
}

.stats-section {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.stat-card {
  background: #13131f;
  border-radius: 10px;
  padding: 0.75rem;
  text-align: center;
  border: 1px solid #1f1f2e;
}

.stat-value {
  display: block;
  font-size: 1.25rem;
  font-weight: 700;
  color: #ffd700;
  margin-bottom: 0.15rem;
}

.stat-label {
  color: #666;
  font-size: 0.6rem;
}

.btn {
  padding: 0.75rem 1rem;
  border-radius: 10px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.85rem;
}

.btn-primary {
  background: #ffd700;
  color: #0d0d14;
}

.btn-full {
  width: 100%;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.transactions-section {
  background: #13131f;
  border-radius: 12px;
  padding: 1rem;
  border: 1px solid #1f1f2e;
}

.transactions-section h3 {
  color: #ffd700;
  font-size: 0.9rem;
  margin: 0 0 0.75rem;
}

.no-tx {
  text-align: center;
  padding: 1.5rem;
  color: #555;
}

.tx-list {
  display: flex;
  flex-direction: column;
  gap: 0.5rem;
}

.tx-item {
  display: flex;
  align-items: center;
  gap: 0.75rem;
  padding: 0.75rem;
  background: #0d0d14;
  border-radius: 8px;
}

.tx-icon {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1rem;
  background: #1f1f2e;
  flex-shrink: 0;
}

.tx-icon.received {
  background: rgba(76, 175, 80, 0.2);
}

.tx-icon.sent {
  background: rgba(244, 67, 54, 0.2);
}

.tx-details {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
  min-width: 0;
}

.tx-type-label {
  font-size: 0.8rem;
  font-weight: 500;
}

.tx-hash {
  font-size: 0.6rem;
  color: #555;
  font-family: monospace;
}

.snowtrace-link {
  font-size: 0.6rem;
  color: #00d4ff;
  text-decoration: none;
}

.internal-label {
  font-size: 0.6rem;
  color: #888;
}

.tx-amount {
  font-weight: 600;
  font-size: 0.8rem;
  flex-shrink: 0;
}

.tx-amount.received {
  color: #4caf50;
}

.tx-amount.sent {
  color: #f44336;
}

.toast {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: #13131f;
  border: 1px solid #1f1f2e;
  border-radius: 12px;
  padding: 1.5rem;
  text-align: center;
  z-index: 100;
}

.toast p {
  margin: 0 0 1rem;
  color: #4caf50;
  font-weight: 600;
}
</style>
