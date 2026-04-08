<template>
  <div class="admin-dashboard">
    <header class="header">
      <div class="logo">RZC Admin</div>
      <div class="user-menu">
        <span class="email">{{ authStore.user?.email }}</span>
        <button @click="goToDashboard" class="btn-back">Dashboard</button>
        <button @click="handleLogout" class="btn-logout">Logout</button>
      </div>
    </header>

    <main class="content">
      <div class="left-column">
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
                <span class="value address tooltip" @click="copyAddress(adminWallet?.address)">
                  {{ adminWallet?.address }}
                  <span class="tooltip-text">Click to copy</span>
                </span>
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
                <span class="value address tooltip" @click="copyAddress(adminWallet?.address)">
                  {{ adminWallet?.address }}
                  <span class="tooltip-text">Click to copy</span>
                </span>
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
      </div>

      <div class="right-column">
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
                <span class="tx-hash">{{ tx.tx_hash.slice(0, 10) }}...{{ tx.tx_hash.slice(-6) }}</span>
                <a v-if="tx.tx_hash.startsWith('0x')" :href="`https://snowtrace.io/tx/${tx.tx_hash}`" target="_blank" class="snowtrace-link">View on Snowtrace</a>
                <span v-else class="internal-label">Internal Transfer</span>
              </div>
              <div class="tx-amount" :class="tx.type">
                {{ tx.type === 'received' ? '+' : '-' }}{{ tx.token === 'AVAX' ? formatAvax(tx.amount) : formatRzc(tx.amount) }} {{ tx.token || 'RZC' }}
              </div>
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

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { adminApi, walletApi, transactionsApi } from '../api'

const router = useRouter()
const authStore = useAuthStore()

const adminWallet = ref(null)
const adminRzcBalance = ref(0)
const totalWallets = ref(0)
const totalRzc = ref(0)
const syncingAvax = ref(false)
const syncingAll = ref(false)
const syncingTxs = ref(false)
const transactions = ref([])
const showCopiedToast = ref(false)

const formatAvax = (balance) => {
  if (!balance) return '0'
  return (Number(balance) / 1e18).toFixed(6)
}

const formatRzc = (balance) => {
  if (!balance) return '0'
  const formatted = Number(balance) / 1e18
  return formatted.toFixed(6)
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

const copyAddress = async (address) => {
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
  background: #ffd700;
  border: none;
  color: #0d0d14;
  padding: 0.5rem 1rem;
  border-radius: 8px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
}

.btn-back {
  background: #ffd700;
  border: none;
  color: #0d0d14;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
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

.tooltip {
  position: relative;
  cursor: pointer;
}

.tooltip .tooltip-text {
  display: none;
  position: absolute;
  background: #333;
  color: #fff;
  padding: 0.25rem 0.5rem;
  border-radius: 4px;
  font-size: 0.7rem;
  white-space: nowrap;
  z-index: 1;
  top: 100%;
  left: 50%;
  transform: translateX(-50%);
  margin-top: 4px;
}

.tooltip:hover .tooltip-text {
  display: block;
}

.value.address {
  font-family: monospace;
  font-size: 0.8rem;
  word-break: break-all;
  cursor: pointer;
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

.content {
  display: flex;
  gap: 2rem;
  max-width: 1200px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
}

.left-column {
  flex: 1;
}

.right-column {
  flex: 1;
}

.transactions-section {
  background: #13131f;
  border-radius: 16px;
  padding: 1.5rem;
  border: 1px solid #1f1f2e;
}

.transactions-section .card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 1rem;
}

.transactions-section .card-header h3 {
  color: #ffd700;
  font-size: 1rem;
  margin: 0;
}

.no-tx {
  text-align: center;
  padding: 2rem;
  color: #555;
}

.tx-list {
  display: flex;
  flex-direction: column;
  gap: 0.75rem;
}

.tx-item {
  display: flex;
  align-items: center;
  gap: 1rem;
  padding: 1rem;
  background: #0d0d14;
  border-radius: 10px;
}

.tx-icon {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.2rem;
  background: #1f1f2e;
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
  gap: 0.25rem;
}

.tx-type-label {
  font-size: 0.9rem;
  font-weight: 500;
}

.tx-hash {
  font-size: 0.75rem;
  color: #555;
  font-family: monospace;
}

.snowtrace-link {
  font-size: 0.7rem;
  color: #00d4ff;
  text-decoration: none;
  margin-top: 0.25rem;
}

.snowtrace-link:hover {
  text-decoration: underline;
}

.internal-label {
  font-size: 0.7rem;
  color: #888;
  margin-top: 0.25rem;
}

.tx-amount {
  font-weight: 600;
  font-size: 0.95rem;
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
  background: #1f1f2e;
  border: 1px solid #ffd700;
  border-radius: 12px;
  padding: 2rem;
  text-align: center;
  z-index: 1000;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.5);
}

.toast p {
  color: #fff;
  margin-bottom: 1.5rem;
}
</style>
