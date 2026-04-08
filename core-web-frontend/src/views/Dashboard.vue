<template>
  <div class="dashboard">
    <header class="header">
      <div class="logo">RZC</div>
      <div class="header-center">
        <div class="wallet-selector" v-if="authStore.wallets.length > 0">
          <select v-model="selectedWalletId" @change="onWalletChange" class="wallet-select">
            <option v-for="w in authStore.wallets" :key="w.id" :value="w.id">
              {{ w.name }} ({{ w.address?.slice(0, 6) }}...{{ w.address?.slice(-4) }})
            </option>
          </select>
          <button @click="showWalletManager = true" class="btn-add-wallet">Manage</button>
        </div>
      </div>
      <div class="user-menu">
        <span class="email">{{ authStore.user?.email }}</span>
        <button v-if="authStore.isAdmin" @click="goToAdmin" class="btn-admin">Admin</button>
        <button @click="handleLogout" class="btn-logout">Logout</button>
      </div>
    </header>

    <main class="main-content">
      <div class="left-column">
        <div class="balance-section">
          <div class="balance-card">
            <span class="balance-label">Total Balance</span>
            <span v-if="syncing" class="balance-value syncing">⟳</span>
            <span v-else class="balance-value">{{ formatBalance(authStore.activeWallet?.balance) }} <small>RZC</small></span>
            <span class="balance-address tooltip" @click="copyAddress">{{ authStore.activeWallet?.address }}<span class="tooltip-text">Click to copy</span></span>
          </div>
        </div>

        <div v-if="!authStore.activeWallet?.address" class="create-wallet-section">
          <p class="no-wallet-msg">No wallet found</p>
          <button @click="showAddWalletModal = true" class="btn btn-primary btn-large" :disabled="authStore.loading">
            {{ authStore.loading ? 'Creating Wallet...' : 'Create Wallet' }}
          </button>
          <p v-if="authStore.error" class="error">{{ authStore.error }}</p>
        </div>

        <div v-else class="actions-section">
          <button @click="copyAddress" class="action-btn">
            <span class="action-icon">📋</span>
            <span class="action-label">Copy Address</span>
          </button>
          <button @click="syncBalance" class="action-btn" :disabled="syncing">
            <span class="action-icon">🔄</span>
            <span class="action-label">Sync Balance</span>
          </button>
          <button @click="showSendModal = true" class="action-btn">
            <span class="action-icon">📤</span>
            <span class="action-label">Send RZC</span>
          </button>
          <button @click="showTransferModal = true" class="action-btn">
            <span class="action-icon">↔️</span>
            <span class="action-label">Transfer</span>
          </button>
          <button @click="showRecipientsModal = true" class="action-btn">
            <span class="action-icon">👥</span>
            <span class="action-label">Recipients</span>
          </button>
          <button @click="showBuyModal = true" class="action-btn">
            <span class="action-icon">💲</span>
            <span class="action-label">Buy RZC</span>
          </button>
          <button @click="showRecreateModal = true" class="action-btn danger">
            <span class="action-icon">⚠️</span>
            <span class="action-label">Recreate</span>
          </button>
          <button @click="showDeleteModal = true" class="action-btn danger">
            <span class="action-icon">🗑️</span>
            <span class="action-label">Delete</span>
          </button>
        </div>
      </div>

      <div class="right-column">
        <div class="transactions-section">
          <h3>Transaction History</h3>
          <div v-if="transactions.length === 0" class="no-tx">
            <p>No transactions yet</p>
          </div>
          <div v-else class="tx-list">
            <div v-for="tx in transactions" :key="tx.tx_hash" class="tx-item">
              <div class="tx-icon" :class="tx.type">
                {{ tx.type === 'received' ? '📥' : '📤' }}
              </div>
              <div class="tx-details">
                <span class="tx-type-label">{{ tx.type === 'received' ? 'Received' : 'Sent' }}</span>
                <span class="tx-hash">{{ tx.tx_hash.slice(0, 10) }}...{{ tx.tx_hash.slice(-6) }}</span>
              </div>
              <div class="tx-amount" :class="tx.type">
                {{ tx.type === 'received' ? '+' : '-' }}{{ formatBalance(tx.amount) }} RZC
              </div>
            </div>
          </div>
        </div>
      </div>
    </main>

    <div v-if="showCopiedToast" class="toast">
        <p>Wallet address copied!</p>
        <button @click="showCopiedToast = false" class="btn btn-primary">OK</button>
      </div>

    <div v-if="showSendModal" class="modal-overlay" @click.self="showSendModal = false">
      <div class="modal">
        <h3>Send RZC</h3>
        <div class="form-group">
          <label>Recipient</label>
          <select v-model="sendForm.toAddress" class="form-select">
            <option value="">Enter address manually...</option>
            <option v-for="r in recipients" :key="r.id" :value="r.address">
              {{ r.name }} ({{ r.address.slice(0, 6) }}...{{ r.address.slice(-4) }})
            </option>
          </select>
        </div>
        <div v-if="!sendForm.toAddress" class="form-group">
          <label>Recipient Address</label>
          <input v-model="sendForm.toAddressManual" type="text" placeholder="0x..." />
        </div>
        <div class="form-group">
          <label>Amount</label>
          <input v-model="sendForm.amount" type="number" placeholder="0" />
        </div>
        <p v-if="sendError" class="error">{{ sendError }}</p>
        <div class="modal-actions">
          <button @click="showSendModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="sendRZC" class="btn btn-primary" :disabled="sending">
            {{ sending ? 'Sending...' : 'Send' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showTransferModal" class="modal-overlay" @click.self="showTransferModal = false">
      <div class="modal">
        <h3>Transfer Between Wallets</h3>
        <p class="transfer-info">Transfer from {{ authStore.activeWallet?.name }} to another wallet</p>
        <div class="form-group">
          <label>To Wallet</label>
          <select v-model="transferForm.toWalletId" class="form-select">
            <option value="">Select wallet...</option>
            <option v-for="w in otherWallets" :key="w.id" :value="w.id">
              {{ w.name }} ({{ w.address?.slice(0, 6) }}...{{ w.address?.slice(-4) }})
            </option>
          </select>
        </div>
        <div class="form-group">
          <label>Amount</label>
          <input v-model="transferForm.amount" type="number" placeholder="0" />
        </div>
        <p v-if="transferError" class="error">{{ transferError }}</p>
        <div class="modal-actions">
          <button @click="showTransferModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="transferBetweenWallets" class="btn btn-primary" :disabled="transferring || !transferForm.toWalletId">
            {{ transferring ? 'Transferring...' : 'Transfer' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showRecipientsModal" class="modal-overlay" @click.self="showRecipientsModal = false">
      <div class="modal recipients-modal">
        <h3>Recipients</h3>
        <div class="recipient-form">
          <input v-model="newRecipient.name" type="text" placeholder="Name" class="recipient-input" />
          <input v-model="newRecipient.address" type="text" placeholder="0x..." class="recipient-input" />
          <button @click="addRecipient" class="btn btn-primary">Add</button>
        </div>
        <input v-model="recipientSearch" type="text" placeholder="Search..." class="recipient-search" />
        <p v-if="recipientError" class="error">{{ recipientError }}</p>
        <div class="recipients-list">
          <div v-if="filteredRecipients.length === 0" class="no-recipients">
            {{ recipientSearch ? 'No matches found' : 'No recipients saved' }}
          </div>
          <div v-for="r in filteredRecipients" :key="r.id" class="recipient-item">
            <div class="recipient-info">
              <span class="recipient-name">{{ r.name }}</span>
              <span class="recipient-address">{{ r.address.slice(0, 10) }}...{{ r.address.slice(-6) }}</span>
            </div>
            <button @click="removeRecipient(r.id)" class="btn-remove">✕</button>
          </div>
        </div>
        <div class="modal-actions">
          <button @click="showRecipientsModal = false" class="btn btn-secondary">Done</button>
        </div>
      </div>
    </div>

    <div v-if="showRecreateModal" class="modal-overlay" @click.self="showRecreateModal = false">
      <div class="modal">
        <h3>Recreate Wallet</h3>
        <p class="warning-text">This will delete your current wallet and create a new one. Make sure you have transferred any funds!</p>
        <div class="form-group">
          <label>Type <strong>RECREATE WALLET</strong> to confirm:</label>
          <input v-model="recreateConfirm" type="text" placeholder="RECREATE WALLET" class="form-input" />
        </div>
        <p v-if="recreateError" class="error">{{ recreateError }}</p>
        <div class="modal-actions">
          <button @click="showRecreateModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="recreateWallet" class="btn btn-danger" :disabled="recreateConfirm !== 'RECREATE WALLET' || recreating">
            {{ recreating ? 'Recreating...' : 'Recreate Wallet' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal">
        <h3>Delete Wallet</h3>
        <p class="warning-text">This will permanently delete this wallet. Transfer any funds first!</p>
        <div class="form-group">
          <label>Type <strong>DELETE WALLET</strong> to confirm:</label>
          <input v-model="deleteConfirm" type="text" placeholder="DELETE WALLET" class="form-input" />
        </div>
        <p v-if="deleteError" class="error">{{ deleteError }}</p>
        <div class="modal-actions">
          <button @click="showDeleteModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="deleteWallet" class="btn btn-danger" :disabled="deleteConfirm !== 'DELETE WALLET' || deleting">
            {{ deleting ? 'Deleting...' : 'Delete Wallet' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showAddWalletModal" class="modal-overlay" @click.self="showAddWalletModal = false">
      <div class="modal">
        <h3>Create New Wallet</h3>
        <div class="form-group">
          <label>Wallet Name</label>
          <input v-model="newWalletName" type="text" :placeholder="'Wallet ' + (authStore.wallets.length + 1)" class="form-input" />
        </div>
        <p v-if="addWalletError" class="error">{{ addWalletError }}</p>
        <div class="modal-actions">
          <button @click="showAddWalletModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="createWallet" class="btn btn-primary" :disabled="addingWallet">
            {{ addingWallet ? 'Creating...' : 'Create' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showBuyModal" class="modal-overlay" @click.self="showBuyModal = false">
      <div class="modal">
        <h3>Buy RZC</h3>
        <p class="coming-soon">Purchase RZC directly with your credit card or bank transfer.</p>
        <p class="coming-soon-sub">Google Pay and Apple Pay support coming soon.</p>
        <div class="modal-actions">
          <button @click="showBuyModal = false" class="btn btn-secondary">Close</button>
        </div>
      </div>
    </div>

    <div v-if="showWalletManager" class="modal-overlay" @click.self="closeWalletManager">
      <div class="modal wallet-manager-modal">
        <h3>Manage Wallets</h3>
        
        <div class="wallet-list">
          <div v-for="wallet in authStore.wallets" :key="wallet.id" class="wallet-item">
            <div class="wallet-info" v-if="editingWalletId !== wallet.id">
              <div class="wallet-name-row">
                <span class="wallet-name">{{ wallet.name }}</span>
                <span v-if="wallet.is_active" class="active-badge">Active</span>
              </div>
              <span class="wallet-address">{{ wallet.address }}</span>
              <span class="wallet-balance">{{ formatBalance(wallet.balance) }} RZC</span>
            </div>
            <div class="wallet-edit" v-else>
              <input v-model="editingWalletName" type="text" class="form-input" placeholder="Wallet name" />
            </div>
            <div class="wallet-actions">
              <template v-if="editingWalletId !== wallet.id">
                <button @click="startRename(wallet)" class="btn-icon" title="Rename">✏️</button>
                <button @click="startDelete(wallet.id)" class="btn-icon" title="Delete">🗑️</button>
              </template>
              <template v-else>
                <button @click="saveRename" class="btn-icon btn-save" title="Save">✓</button>
                <button @click="cancelEdit" class="btn-icon" title="Cancel">✕</button>
              </template>
            </div>
          </div>
        </div>

        <p v-if="renameError" class="error">{{ renameError }}</p>
        <p v-if="deleteWalletError" class="error">{{ deleteWalletError }}</p>

        <div v-if="deletingWalletId" class="delete-confirm">
          <p class="warning-text">Type DELETE to confirm:</p>
          <input v-model="deleteWalletConfirm" type="text" placeholder="DELETE" class="form-input" />
        </div>

        <div class="modal-actions">
          <button @click="showCreateWalletModal = true" class="btn btn-primary">+ Create New</button>
          <button @click="closeWalletManager" class="btn btn-secondary">Done</button>
        </div>
      </div>
    </div>

    <div v-if="showCreateWalletModal" class="modal-overlay" @click.self="showCreateWalletModal = false">
      <div class="modal">
        <h3>Create New Wallet</h3>
        <div class="form-group">
          <label>Wallet Name</label>
          <input v-model="newWalletNameInput" type="text" :placeholder="'Wallet ' + (authStore.wallets.length + 1)" class="form-input" />
        </div>
        <p v-if="createWalletError" class="error">{{ createWalletError }}</p>
        <div class="modal-actions">
          <button @click="showCreateWalletModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="createWalletFromManager" class="btn btn-primary" :disabled="creatingWallet">
            {{ creatingWallet ? 'Creating...' : 'Create' }}
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { transactionsApi, walletApi, recipientsApi } from '../api'

const router = useRouter()
const authStore = useAuthStore()

const selectedWalletId = ref(null)
const showSendModal = ref(false)
const showRecipientsModal = ref(false)
const showCopiedToast = ref(false)
const sendForm = ref({ toAddress: '', toAddressManual: '', amount: 0 })
const sending = ref(false)
const sendError = ref('')
const syncing = ref(false)
const transactions = ref([])
const recipients = ref([])
const newRecipient = ref({ name: '', address: '' })
const recipientError = ref('')
const recipientSearch = ref('')
const showRecreateModal = ref(false)
const recreateConfirm = ref('')
const recreating = ref(false)
const recreateError = ref('')
const showBuyModal = ref(false)
const showDeleteModal = ref(false)
const deleteConfirm = ref('')
const deleting = ref(false)
const deleteError = ref('')
const showTransferModal = ref(false)
const transferForm = ref({ toWalletId: '', amount: 0 })
const transferring = ref(false)
const transferError = ref('')
const showWalletManager = ref(false)
const editingWalletId = ref(null)
const editingWalletName = ref('')
const renameError = ref('')
const deletingWalletId = ref(null)
const deleteWalletConfirm = ref('')
const deleteWalletError = ref('')
const showCreateWalletModal = ref(false)
const newWalletNameInput = ref('')
const createWalletError = ref('')
const creatingWallet = ref(false)

const otherWallets = computed(() => {
  return authStore.wallets.filter(w => w.id !== authStore.activeWallet?.id)
})

const filteredRecipients = computed(() => {
  if (!recipientSearch.value) return recipients.value
  const query = recipientSearch.value.toLowerCase()
  return recipients.value.filter(r =>
    r.name.toLowerCase().includes(query) ||
    r.address.toLowerCase().includes(query)
  )
})

const formatBalance = (balance) => {
  if (!balance) return '0.0000'
  return (Number(balance) / 1e18).toFixed(4)
}

const onWalletChange = async () => {
  if (selectedWalletId.value && selectedWalletId.value !== authStore.activeWallet?.id) {
    await authStore.switchWallet(selectedWalletId.value)
    await loadTransactions()
  }
}

const copyAddress = async () => {
  await navigator.clipboard.writeText(authStore.activeWallet.address)
  showCopiedToast.value = true
}

const createWallet = async () => {
  addingWallet.value = true
  addWalletError.value = ''
  try {
    const name = newWalletName.value || `Wallet ${authStore.wallets.length + 1}`
    await authStore.createWallet(name)
    newWalletName.value = ''
    showAddWalletModal.value = false
    selectedWalletId.value = authStore.activeWallet?.id
  } catch (e) {
    addWalletError.value = e.response?.data?.detail || 'Failed to create wallet'
  } finally {
    addingWallet.value = false
  }
}

const deleteWallet = async () => {
  deleting.value = true
  deleteError.value = ''
  try {
    await authStore.deleteWallet(authStore.activeWallet.id)
    showDeleteModal.value = false
    deleteConfirm.value = ''
    if (authStore.activeWallet) {
      selectedWalletId.value = authStore.activeWallet.id
    }
  } catch (e) {
    deleteError.value = e.response?.data?.detail || 'Failed to delete wallet'
  } finally {
    deleting.value = false
  }
}

const startRename = (wallet) => {
  editingWalletId.value = wallet.id
  editingWalletName.value = wallet.name
  renameError.value = ''
}

const cancelEdit = () => {
  editingWalletId.value = null
  editingWalletName.value = ''
  renameError.value = ''
}

const saveRename = async () => {
  if (!editingWalletName.value.trim()) {
    renameError.value = 'Wallet name is required'
    return
  }
  try {
    await walletApi.renameWallet(editingWalletId.value, editingWalletName.value.trim())
    await authStore.loadWallets()
    cancelEdit()
  } catch (e) {
    renameError.value = e.response?.data?.detail || 'Failed to rename wallet'
  }
}

const startDelete = (walletId) => {
  deletingWalletId.value = walletId
  deleteWalletConfirm.value = ''
  deleteWalletError.value = ''
}

const confirmDeleteWallet = async () => {
  if (deleteWalletConfirm.value !== 'DELETE') {
    deleteWalletError.value = 'Type DELETE to confirm'
    return
  }
  try {
    await authStore.deleteWallet(deletingWalletId.value)
    deletingWalletId.value = null
    deleteWalletConfirm.value = ''
    if (authStore.activeWallet) {
      selectedWalletId.value = authStore.activeWallet.id
    }
  } catch (e) {
    deleteWalletError.value = e.response?.data?.detail || 'Failed to delete wallet'
  }
}

const closeWalletManager = () => {
  showWalletManager.value = false
  cancelEdit()
  deletingWalletId.value = null
  deleteWalletConfirm.value = ''
}

const createWalletFromManager = async () => {
  creatingWallet.value = true
  createWalletError.value = ''
  try {
    const name = newWalletNameInput.value || `Wallet ${authStore.wallets.length + 1}`
    await authStore.createWallet(name)
    newWalletNameInput.value = ''
    showCreateWalletModal.value = false
  } catch (e) {
    createWalletError.value = e.response?.data?.detail || 'Failed to create wallet'
  } finally {
    creatingWallet.value = false
  }
}

const recreateWallet = async () => {
  recreating.value = true
  recreateError.value = ''
  try {
    const response = await walletApi.recreateWallet(authStore.activeWallet.id)
    await authStore.loadWallets()
    showRecreateModal.value = false
    recreateConfirm.value = ''
  } catch (e) {
    recreateError.value = e.response?.data?.detail || 'Failed to recreate wallet'
  } finally {
    recreating.value = false
  }
}

const syncBalance = async () => {
  syncing.value = true
  try {
    await walletApi.syncBalance()
    await authStore.loadWallets()
    await loadTransactions()
  } catch (e) {
    console.error('Sync error:', e)
  } finally {
    syncing.value = false
  }
}

const loadTransactions = async () => {
  try {
    const response = await transactionsApi.getHistory()
    transactions.value = response.data.transactions || []
  } catch (e) {
    console.error('Load transactions error:', e)
  }
}

const loadRecipients = async () => {
  try {
    const response = await recipientsApi.getAll()
    recipients.value = response.data || []
  } catch (e) {
    console.error('Load recipients error:', e)
  }
}

const addRecipient = async () => {
  recipientError.value = ''
  const address = sendForm.value.toAddress ? sendForm.value.toAddress : newRecipient.value.address
  if (!newRecipient.value.name || !address) {
    recipientError.value = 'Name and address required'
    return
  }
  try {
    const response = await recipientsApi.add(newRecipient.value.name, address)
    recipients.value.push(response.data)
    newRecipient.value = { name: '', address: '' }
  } catch (e) {
    recipientError.value = e.response?.data?.detail || 'Failed to add recipient'
  }
}

const removeRecipient = async (id) => {
  try {
    await recipientsApi.remove(id)
    recipients.value = recipients.value.filter(r => r.id !== id)
  } catch (e) {
    recipientError.value = e.response?.data?.detail || 'Failed to remove recipient'
  }
}

const sendRZC = async () => {
  sending.value = true
  sendError.value = ''
  const address = sendForm.value.toAddress || sendForm.value.toAddressManual
  if (!address) {
    sendError.value = 'Recipient address required'
    sending.value = false
    return
  }
  try {
    const amountWei = BigInt(sendForm.value.amount * 1e18)
    await transactionsApi.send(address, Number(amountWei))
    showSendModal.value = false
    sendForm.value = { toAddress: '', toAddressManual: '', amount: 0 }
    await syncBalance()
  } catch (e) {
    sendError.value = e.response?.data?.detail || 'Failed to send'
  } finally {
    sending.value = false
  }
}

const transferBetweenWallets = async () => {
  transferring.value = true
  transferError.value = ''
  if (!transferForm.value.toWalletId) {
    transferError.value = 'Select a wallet'
    transferring.value = false
    return
  }
  try {
    const amountWei = BigInt(transferForm.value.amount * 1e18)
    await transactionsApi.internalTransfer(transferForm.value.toWalletId, Number(amountWei))
    showTransferModal.value = false
    transferForm.value = { toWalletId: '', amount: 0 }
    await authStore.loadWallets()
  } catch (e) {
    transferError.value = e.response?.data?.detail || 'Failed to transfer'
  } finally {
    transferring.value = false
  }
}

const handleLogout = () => {
  authStore.logout()
  router.push('/')
}

const goToAdmin = () => {
  router.push('/admin')
}

onMounted(async () => {
  await authStore.loadWallets()
  if (authStore.activeWallet) {
    selectedWalletId.value = authStore.activeWallet.id
  }
  await loadTransactions()
  await loadRecipients()
})
</script>

<style scoped>
@keyframes spin {
  from { transform: rotate(0deg); }
  to { transform: rotate(360deg); }
}

.syncing {
  display: inline-block;
  animation: spin 1s linear infinite;
}

.dashboard {
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

.header-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.wallet-selector {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.wallet-select {
  padding: 0.5rem 1rem;
  background: #1f1f2e;
  border: 1px solid #333;
  border-radius: 8px;
  color: #fff;
  font-size: 0.9rem;
  min-width: 200px;
}

.btn-add-wallet {
  padding: 0.5rem 1rem;
  background: #ffd700;
  color: #0d0d14;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.85rem;
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

.main-content {
  max-width: 1000px;
  margin: 0 auto;
  padding: 2rem 1.5rem;
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 2rem;
}

.left-column {
  display: flex;
  flex-direction: column;
}

.right-column {
  display: flex;
  flex-direction: column;
}

.balance-section {
  margin-bottom: 2rem;
}

.balance-card {
  background: linear-gradient(135deg, #1f1f2e 0%, #252536 100%);
  border-radius: 20px;
  padding: 2rem;
  text-align: center;
  border: 1px solid #2a2a40;
}

.balance-label {
  display: block;
  color: #666;
  font-size: 0.85rem;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.balance-value {
  display: block;
  font-size: 2.5rem;
  font-weight: 700;
  color: #ffd700;
  margin-bottom: 0.5rem;
}

.balance-value small {
  font-size: 1.2rem;
  color: #888;
}

.balance-address {
  font-size: 0.75rem;
  color: #555;
  font-family: monospace;
  word-break: break-all;
  cursor: pointer;
  position: relative;
}

.tooltip .tooltip-text {
  visibility: hidden;
  position: absolute;
  bottom: 100%;
  left: 50%;
  transform: translateX(-50%);
  background: #333;
  color: #fff;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  font-size: 0.7rem;
  white-space: nowrap;
  opacity: 0;
  transition: opacity 0.2s;
  pointer-events: none;
  margin-bottom: 0.5rem;
}

.tooltip:hover .tooltip-text {
  visibility: visible;
  opacity: 1;
}

.toast {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: #13131f;
  border: 1px solid #1f1f2e;
  border-radius: 16px;
  padding: 2rem;
  text-align: center;
  z-index: 200;
  box-shadow: 0 4px 20px rgba(0,0,0,0.5);
}

.toast p {
  margin: 0 0 1.5rem;
  color: #4caf50;
  font-weight: 600;
}

.create-wallet-section {
  text-align: center;
  padding: 2rem;
  background: #13131f;
  border-radius: 16px;
  margin-bottom: 2rem;
}

.no-wallet-msg {
  color: #666;
  margin-bottom: 1rem;
}

.actions-section {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  gap: 0.75rem;
  margin-bottom: 2rem;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.5rem;
  padding: 1.25rem 1rem;
  background: #13131f;
  border: 1px solid #1f1f2e;
  border-radius: 12px;
  color: #fff;
  cursor: pointer;
  transition: all 0.2s;
}

.action-btn:hover {
  background: #1a1a28;
  border-color: #333;
}

.action-btn.primary {
  background: #ffd700;
  color: #0d0d14;
  border-color: #ffd700;
}

.action-btn.primary:hover {
  background: #ffed4a;
}

.action-icon {
  font-size: 1.5rem;
}

.action-label {
  font-size: 0.75rem;
  color: #888;
}

.action-btn.primary .action-label {
  color: #0d0d14;
  font-weight: 600;
}

.action-btn.danger {
  border-color: #f44336;
}

.action-btn.danger .action-label {
  color: #f44336;
}

.btn-danger {
  background: #f44336;
  color: #fff;
}

.btn-danger:hover:not(:disabled) {
  background: #d32f2f;
}

.btn-danger:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.warning-text {
  color: #f44336;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  line-height: 1.4;
}

.transfer-info {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.coming-soon {
  color: #ffd700;
  font-size: 1rem;
  margin-bottom: 0.5rem;
}

.coming-soon-sub {
  color: #666;
  font-size: 0.85rem;
  margin-bottom: 1.5rem;
}

.form-input {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 1px solid #333;
  border-radius: 10px;
  background: #0d0d14;
  color: #fff;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-input:focus {
  outline: none;
  border-color: #ffd700;
}

.transactions-section {
  background: #13131f;
  border-radius: 16px;
  padding: 1.5rem;
}

.transactions-section h3 {
  color: #ffd700;
  font-size: 1rem;
  margin: 0 0 1rem;
  font-weight: 600;
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

.btn {
  padding: 0.75rem 1.5rem;
  border-radius: 10px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.btn-primary {
  background: #ffd700;
  color: #0d0d14;
}

.btn-primary:hover:not(:disabled) {
  background: #ffed4a;
}

.btn-secondary {
  background: #333;
  color: #fff;
}

.btn-large {
  padding: 1rem 2rem;
  font-size: 1rem;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  color: #f44336;
  margin: 0.5rem 0;
  font-size: 0.85rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.85);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
}

.modal {
  background: #13131f;
  border-radius: 20px;
  padding: 2rem;
  width: 90%;
  max-width: 400px;
  border: 1px solid #1f1f2e;
  box-sizing: border-box;
}

.modal h3 {
  color: #ffd700;
  margin: 0 0 1.5rem;
}

.form-group {
  margin-bottom: 1rem;
}

.form-group label {
  display: block;
  color: #888;
  margin-bottom: 0.5rem;
  font-size: 0.85rem;
}

.form-group input {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 1px solid #333;
  border-radius: 10px;
  background: #0d0d14;
  color: #fff;
  font-size: 1rem;
  box-sizing: border-box;
}

.form-group input[type="number"]::-webkit-outer-spin-button,
.form-group input[type="number"]::-webkit-inner-spin-button {
  -webkit-appearance: none;
  margin: 0;
}

.form-group input[type="number"] {
  -moz-appearance: textfield;
}

.form-group input:focus {
  outline: none;
  border-color: #ffd700;
}

.modal-actions {
  display: flex;
  gap: 1rem;
  margin-top: 1.5rem;
}

.modal-actions .btn {
  flex: 1;
}

.form-select {
  width: 100%;
  padding: 0.875rem 1rem;
  border: 1px solid #333;
  border-radius: 10px;
  background: #0d0d14;
  color: #fff;
  font-size: 1rem;
  box-sizing: border-box;
  appearance: none;
  cursor: pointer;
}

.form-select:focus {
  outline: none;
  border-color: #ffd700;
}

.recipients-modal {
  max-width: 500px;
  width: 95%;
  box-sizing: border-box;
}

.recipient-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.recipient-form .btn {
  padding: 0.75rem 1rem;
  white-space: nowrap;
}

.recipient-input {
  flex: 1;
  min-width: 0;
  padding: 0.75rem;
  border: 1px solid #333;
  border-radius: 10px;
  background: #0d0d14;
  color: #fff;
  font-size: 0.9rem;
}

.recipient-input:focus {
  outline: none;
  border-color: #ffd700;
}

.recipient-input::placeholder {
  color: #555;
}

.recipient-search {
  width: 100%;
  padding: 0.75rem 1rem;
  border: 1px solid #333;
  border-radius: 10px;
  background: #0d0d14;
  color: #fff;
  font-size: 0.9rem;
  box-sizing: border-box;
  margin-bottom: 1rem;
}

.recipient-search:focus {
  outline: none;
  border-color: #ffd700;
}

.recipient-search::placeholder {
  color: #555;
}

.recipients-list {
  max-height: 250px;
  overflow-y: auto;
  margin-bottom: 1rem;
}

.no-recipients {
  text-align: center;
  padding: 1.5rem;
  color: #555;
}

.recipient-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.875rem;
  background: #0d0d14;
  border-radius: 10px;
  margin-bottom: 0.5rem;
}

.recipient-info {
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.recipient-name {
  font-weight: 500;
  color: #fff;
}

.recipient-address {
  font-size: 0.75rem;
  color: #555;
  font-family: monospace;
}

.btn-remove {
  background: transparent;
  border: none;
  color: #666;
  font-size: 1rem;
  cursor: pointer;
  padding: 0.5rem;
  border-radius: 6px;
}

.btn-remove:hover {
  background: #1f1f2e;
  color: #f44336;
}

.wallet-manager-modal {
  max-width: 500px;
  width: 95%;
  box-sizing: border-box;
}

.wallet-list {
  max-height: 300px;
  overflow-y: auto;
  margin-bottom: 1rem;
}

.wallet-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 1rem;
  background: #0d0d14;
  border-radius: 10px;
  margin-bottom: 0.5rem;
}

.wallet-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.25rem;
}

.wallet-name-row {
  display: flex;
  align-items: center;
  gap: 0.5rem;
}

.wallet-name {
  font-weight: 600;
  color: #fff;
}

.active-badge {
  background: #ffd700;
  color: #0d0d14;
  font-size: 0.65rem;
  padding: 0.15rem 0.4rem;
  border-radius: 4px;
  font-weight: 600;
}

.wallet-address {
  font-size: 0.7rem;
  color: #555;
  font-family: monospace;
}

.wallet-balance {
  font-size: 0.8rem;
  color: #888;
}

.wallet-edit {
  flex: 1;
}

.wallet-edit .form-input {
  padding: 0.5rem;
  font-size: 0.9rem;
}

.wallet-actions {
  display: flex;
  gap: 0.5rem;
  margin-left: 0.5rem;
}

.btn-icon {
  background: transparent;
  border: 1px solid #333;
  color: #666;
  padding: 0.4rem 0.6rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-icon:hover {
  background: #1f1f2e;
  color: #fff;
}

.btn-icon.btn-save {
  background: #ffd700;
  color: #0d0d14;
  border-color: #ffd700;
}

.btn-icon.btn-save:hover {
  background: #ffed4a;
}

.delete-confirm {
  margin-bottom: 1rem;
}

.delete-confirm .warning-text {
  margin-bottom: 0.5rem;
}
</style>
