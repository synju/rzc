<template>
  <div class="dashboard">
    <header class="header">
      <div class="logo">RZC</div>
      <div class="header-buttons">
        <span v-if="authStore.user?.email" class="user-email">{{ authStore.user?.email }}</span>
        <button v-if="authStore.isAdmin" @click="goToAdmin" class="btn-admin">Admin</button>
        <button @click="handleLogout" class="btn-logout">Logout</button>
      </div>
    </header>

    <div class="wallet-selector-bar" v-if="authStore.wallets.length > 0">
      <select v-model="selectedWalletId" @change="onWalletChange" class="wallet-select">
        <option v-for="w in authStore.wallets" :key="w.id" :value="w.id">
          {{ w.name }} ({{ w.address?.slice(0, 6) }}...{{ w.address?.slice(-4) }})
        </option>
      </select>
      <button @click="showWalletManager = true" class="btn-add">Manage</button>
    </div>

    <main class="content">
      <div class="balance-card">
        <span class="balance-label">Total Balance</span>
        <span v-if="syncing" class="balance-value syncing">⟳</span>
        <span v-else class="balance-value">{{ formatBalance(authStore.activeWallet?.balance) }} <small>RZC</small></span>
        <span class="balance-address">{{ authStore.activeWallet?.address }}</span>
      </div>

      <div v-if="!authStore.activeWallet?.address" class="create-wallet-section">
        <p class="no-wallet-msg">No wallet found</p>
        <button @click="showCreateWalletModal = true" class="btn btn-primary" :disabled="authStore.loading">
          {{ authStore.loading ? 'Creating...' : 'Create Wallet' }}
        </button>
        <p v-if="authStore.error" class="error">{{ authStore.error }}</p>
      </div>

      <div v-else class="actions">
        <button @click="copyAddress" class="action-btn">
          <span class="action-icon">📋</span>
          <span>Copy Address</span>
        </button>
        <button @click="syncBalance" class="action-btn" :disabled="syncing">
          <span class="action-icon">🔄</span>
          <span>Sync</span>
        </button>
        <button @click="showSendModal = true" class="action-btn">
          <span class="action-icon">📤</span>
          <span>Send</span>
        </button>
        <button @click="showTransferModal = true" class="action-btn">
          <span class="action-icon">↔️</span>
          <span>Transfer</span>
        </button>
        <button @click="showRecipientsModal = true" class="action-btn">
          <span class="action-icon">👥</span>
          <span>Recipients</span>
        </button>
        <button @click="showBuyModal = true" class="action-btn">
          <span class="action-icon">💲</span>
          <span>Buy</span>
        </button>
        <button @click="showRecreateModal = true" class="action-btn danger">
          <span class="action-icon">⚠️</span>
          <span>Recreate</span>
        </button>
        <button @click="handleDeleteClick" class="action-btn danger">
          <span class="action-icon">🗑️</span>
          <span>Delete</span>
        </button>
      </div>

      <div class="transactions-section">
        <div class="section-header">
          <h3>Transaction History</h3>
          <button @click="syncTransactions" class="btn-refresh" :disabled="syncingTxs">
            {{ syncingTxs ? '⟳' : '🔃' }}
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
              <span class="tx-type-label">{{ tx.type === 'received' ? 'Received' : 'Sent' }}</span>
              <span class="tx-hash">{{ tx.tx_hash.slice(0, 8) }}...{{ tx.tx_hash.slice(-6) }}</span>
              <a v-if="tx.tx_hash.startsWith('0x')" :href="`https://snowtrace.io/tx/${tx.tx_hash}`" target="_blank" class="snowtrace-link">View on Snowtrace</a>
              <span v-else class="internal-label">Internal Transfer</span>
            </div>
            <div class="tx-amount" :class="tx.type">
              {{ tx.type === 'received' ? '+' : '-' }}{{ formatBalance(tx.amount) }} RZC
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
            <option value="">Enter manually...</option>
            <option v-for="r in recipients" :key="r.id" :value="r.address">
              {{ r.name }} ({{ r.address.slice(0, 6) }}...{{ r.address.slice(-4) }})
            </option>
          </select>
        </div>
        <div v-if="!sendForm.toAddress" class="form-group">
          <label>Address</label>
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
        <p class="transfer-info">From {{ authStore.activeWallet?.name }}</p>
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
      <div class="modal">
        <h3>Recipients</h3>
        <div class="recipient-form">
          <input v-model="newRecipient.name" type="text" placeholder="Name" class="recipient-input" />
          <input v-model="newRecipient.address" type="text" placeholder="0x..." class="recipient-input" />
          <button @click="addRecipient" class="btn btn-primary">+</button>
        </div>
        <input v-model="recipientSearch" type="text" placeholder="Search..." class="recipient-search" />
        <p v-if="recipientError" class="error">{{ recipientError }}</p>
        <div class="recipients-list">
          <div v-if="filteredRecipients.length === 0" class="no-recipients">
            {{ recipientSearch ? 'No matches' : 'No recipients' }}
          </div>
          <div v-for="r in filteredRecipients" :key="r.id" class="recipient-item">
            <div class="recipient-info">
              <span class="recipient-name">{{ r.name }}</span>
              <span class="recipient-address">{{ r.address.slice(0, 8) }}...{{ r.address.slice(-6) }}</span>
            </div>
            <button @click="removeRecipient(r.id)" class="btn-remove">✕</button>
          </div>
        </div>
        <button @click="showRecipientsModal = false" class="btn btn-secondary btn-full">Done</button>
      </div>
    </div>

    <div v-if="showRecreateModal" class="modal-overlay" @click.self="showRecreateModal = false">
      <div class="modal">
        <h3>Recreate Wallet</h3>
        <p class="warning-text">Delete wallet and create new. Transfer funds first!</p>
        <div class="form-group">
          <label>Type <strong>RECREATE WALLET</strong> to confirm:</label>
          <input v-model="recreateConfirm" type="text" placeholder="RECREATE WALLET" class="form-input" />
        </div>
        <p v-if="recreateError" class="error">{{ recreateError }}</p>
        <div class="modal-actions">
          <button @click="showRecreateModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="recreateWallet" class="btn btn-danger" :disabled="recreateConfirm !== 'RECREATE WALLET' || recreating">
            {{ recreating ? 'Recreating...' : 'Recreate' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal-overlay" @click.self="showDeleteModal = false">
      <div class="modal">
        <h3>Delete Wallet</h3>
        <p class="warning-text">Permanently delete wallet. Transfer funds first!</p>
        <div class="form-group">
          <label>Type <strong>DELETE WALLET</strong> to confirm:</label>
          <input v-model="deleteConfirm" type="text" placeholder="DELETE WALLET" class="form-input" />
        </div>
        <p v-if="deleteError" class="error">{{ deleteError }}</p>
        <div class="modal-actions">
          <button @click="showDeleteModal = false" class="btn btn-secondary">Cancel</button>
          <button @click="deleteWallet" class="btn btn-danger" :disabled="deleteConfirm !== 'DELETE WALLET' || deleting">
            {{ deleting ? 'Deleting...' : 'Delete' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="showBuyModal" class="modal-overlay" @click.self="showBuyModal = false">
      <div class="modal">
        <h3>Buy RZC</h3>
        <p class="coming-soon">Purchase RZC with card or bank transfer.</p>
        <p class="coming-soon-sub">Google Pay & Apple Pay coming soon.</p>
        <button @click="showBuyModal = false" class="btn btn-secondary btn-full">Close</button>
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
          <button @click="confirmDeleteWallet" class="btn btn-danger btn-full" :disabled="deleteWalletConfirm !== 'DELETE'">
            Confirm Delete
          </button>
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

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { transactionsApi, walletApi, recipientsApi } from '../api'

const router = useRouter()
const authStore = useAuthStore()

const selectedWalletId = ref<string | null>(null)
const showSendModal = ref(false)
const showRecipientsModal = ref(false)
const showCopiedToast = ref(false)
const sendForm = ref({ toAddress: '', toAddressManual: '', amount: 0 })
const sending = ref(false)
const sendError = ref('')
const syncing = ref(false)
const syncingTxs = ref(false)
const transactions = ref<any[]>([])
const recipients = ref<any[]>([])
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

const formatBalance = (balance: any) => {
  if (!balance) return '0.0000'
  return (Number(balance) / 1e18).toFixed(4)
}

const handleDeleteClick = () => {
  if (authStore.wallets.length <= 1) {
    deleteError.value = 'Cannot delete your only wallet. Create another wallet first.'
    showDeleteModal.value = true
  } else {
    deleteError.value = ''
    showDeleteModal.value = true
  }
}

const syncTransactions = async () => {
  syncingTxs.value = true
  try {
    await transactionsApi.syncTransactions()
    await loadTransactions()
  } catch (e) {
    console.error('Sync transactions error:', e)
  } finally {
    syncingTxs.value = false
  }
}

const showWalletManager = ref(false)
const editingWalletId = ref<string | null>(null)
const editingWalletName = ref('')
const renameError = ref('')
const deletingWalletId = ref<string | null>(null)
const deleteWalletConfirm = ref('')
const deleteWalletError = ref('')
const showCreateWalletModal = ref(false)
const newWalletNameInput = ref('')
const createWalletError = ref('')
const creatingWallet = ref(false)

const startRename = (wallet: any) => {
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
    await walletApi.renameWallet(editingWalletId.value!, editingWalletName.value.trim())
    await authStore.loadWallets()
    cancelEdit()
  } catch (e: any) {
    renameError.value = e.response?.data?.detail || 'Failed to rename wallet'
  }
}

const startDelete = (walletId: string) => {
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
    await authStore.deleteWallet(deletingWalletId.value!)
    deletingWalletId.value = null
    deleteWalletConfirm.value = ''
    if (authStore.activeWallet) {
      selectedWalletId.value = authStore.activeWallet.id
    }
  } catch (e: any) {
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
  } catch (e: any) {
    createWalletError.value = e.response?.data?.detail || 'Failed to create wallet'
  } finally {
    creatingWallet.value = false
  }
}

const onWalletChange = async () => {
  if (selectedWalletId.value && selectedWalletId.value !== authStore.activeWallet?.id) {
    await authStore.switchWallet(selectedWalletId.value)
    await loadTransactions()
  }
}

const copyAddress = async () => {
  await navigator.clipboard.writeText(authStore.activeWallet?.address || '')
  showCopiedToast.value = true
}

const deleteWallet = async () => {
  deleting.value = true
  deleteError.value = ''
  try {
    await authStore.deleteWallet(authStore.activeWallet!.id)
    showDeleteModal.value = false
    deleteConfirm.value = ''
    if (authStore.activeWallet) {
      selectedWalletId.value = authStore.activeWallet.id
    }
  } catch (e: any) {
    deleteError.value = e.response?.data?.detail || 'Failed to delete wallet'
  } finally {
    deleting.value = false
  }
}

const recreateWallet = async () => {
  recreating.value = true
  recreateError.value = ''
  try {
    await walletApi.recreateWallet(authStore.activeWallet!.id)
    await authStore.loadWallets()
    showRecreateModal.value = false
    recreateConfirm.value = ''
  } catch (e: any) {
    recreateError.value = e.response?.data?.detail || 'Failed to recreate'
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
  } catch (e: any) {
    recipientError.value = e.response?.data?.detail || 'Failed to add'
  }
}

const removeRecipient = async (id: string) => {
  try {
    await recipientsApi.remove(id)
    recipients.value = recipients.value.filter(r => r.id !== id)
  } catch (e: any) {
    recipientError.value = e.response?.data?.detail || 'Failed to remove'
  }
}

const sendRZC = async () => {
  sending.value = true
  sendError.value = ''
  const address = sendForm.value.toAddress || sendForm.value.toAddressManual
  if (!address) {
    sendError.value = 'Address required'
    sending.value = false
    return
  }
  try {
    const amountWei = BigInt(sendForm.value.amount * 1e18)
    await transactionsApi.send(address, Number(amountWei))
    showSendModal.value = false
    sendForm.value = { toAddress: '', toAddressManual: '', amount: 0 }
    await syncBalance()
  } catch (e: any) {
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
  } catch (e: any) {
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
  padding: 1rem 1.5rem;
  background: #13131f;
  border-bottom: 1px solid #1f1f2e;
}

.logo {
  font-size: 1.5rem;
  font-weight: 700;
  color: #ffd700;
  letter-spacing: 2px;
}

.header-buttons {
  display: flex;
  gap: 0.5rem;
  align-items: center;
}

.user-email {
  color: #666;
  font-size: 0.75rem;
  max-width: 120px;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.btn-admin {
  background: #ffd700;
  border: none;
  color: #0d0d14;
  padding: 0.5rem 1rem;
  border-radius: 6px;
  cursor: pointer;
  font-size: 0.85rem;
  font-weight: 600;
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

.wallet-selector-bar {
  display: flex;
  gap: 0.5rem;
  padding: 0.75rem 1rem;
  background: #13131f;
}

.wallet-select {
  flex: 1;
  padding: 0.6rem;
  background: #1f1f2e;
  border: 1px solid #333;
  border-radius: 8px;
  color: #fff;
  font-size: 0.9rem;
}

.btn-add {
  padding: 0.6rem 1rem;
  background: #ffd700;
  color: #0d0d14;
  border: none;
  border-radius: 8px;
  font-weight: 600;
  cursor: pointer;
}

.content {
  padding: 1rem;
  max-width: 600px;
  margin: 0 auto;
}

.balance-card {
  background: linear-gradient(135deg, #1f1f2e 0%, #252536 100%);
  border-radius: 16px;
  padding: 1.5rem;
  text-align: center;
  border: 1px solid #2a2a40;
  margin-bottom: 1rem;
}

.balance-label {
  display: block;
  color: #666;
  font-size: 0.75rem;
  margin-bottom: 0.5rem;
  text-transform: uppercase;
  letter-spacing: 1px;
}

.balance-value {
  display: block;
  font-size: 2rem;
  font-weight: 700;
  color: #ffd700;
  margin-bottom: 0.5rem;
}

.balance-value small {
  font-size: 1rem;
  color: #888;
}

.balance-address {
  font-size: 0.7rem;
  color: #555;
  font-family: monospace;
  word-break: break-all;
  cursor: pointer;
}

.toast {
  position: fixed;
  top: 50%;
  left: 50%;
  transform: translate(-50%, -50%);
  background: #13131f;
  border: 1px solid #1f1f2e;
  border-radius: 16px;
  padding: 1.5rem;
  text-align: center;
  z-index: 200;
}

.toast p {
  margin: 0 0 1rem;
  color: #4caf50;
  font-weight: 600;
}

.create-wallet-section {
  text-align: center;
  padding: 1.5rem;
  background: #13131f;
  border-radius: 16px;
  margin-bottom: 1rem;
}

.no-wallet-msg {
  color: #666;
  margin-bottom: 1rem;
}

.actions {
  display: grid;
  grid-template-columns: repeat(3, 1fr);
  gap: 0.5rem;
  margin-bottom: 1rem;
}

.action-btn {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 0.25rem;
  padding: 0.75rem 0.5rem;
  background: #13131f;
  border: 1px solid #1f1f2e;
  border-radius: 10px;
  color: #fff;
  cursor: pointer;
  font-size: 0.7rem;
}

.action-icon {
  font-size: 1.75rem;
}

.action-btn span:last-child {
  font-size: 0.65rem;
  color: #888;
}

.action-btn.danger {
  border-color: #f44336;
}

.action-btn.danger span:last-child {
  color: #f44336;
}

.transactions-section {
  background: #13131f;
  border-radius: 16px;
  padding: 1rem;
}

.transactions-section h3 {
  color: #ffd700;
  font-size: 0.9rem;
  margin: 0;
}

.section-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 0.75rem;
}

.btn-refresh {
  background: transparent;
  border: 1px solid #333;
  color: #888;
  width: 28px;
  height: 28px;
  border-radius: 50%;
  cursor: pointer;
  font-size: 0.85rem;
  display: flex;
  align-items: center;
  justify-content: center;
}

.btn-refresh:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.no-tx {
  text-align: center;
  padding: 1.5rem;
  color: #555;
  font-size: 0.9rem;
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
  border-radius: 10px;
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
  margin-top: 0.15rem;
}

.internal-label {
  font-size: 0.6rem;
  color: #888;
  margin-top: 0.15rem;
}

.tx-amount {
  font-weight: 600;
  font-size: 0.85rem;
}

.tx-amount.received {
  color: #4caf50;
}

.tx-amount.sent {
  color: #f44336;
}

.btn {
  padding: 0.75rem 1rem;
  border-radius: 10px;
  border: none;
  font-weight: 600;
  cursor: pointer;
  font-size: 0.9rem;
}

.btn-primary {
  background: #ffd700;
  color: #0d0d14;
}

.btn-secondary {
  background: #333;
  color: #fff;
}

.btn-danger {
  background: #f44336;
  color: #fff;
}

.btn-full {
  width: 100%;
}

.btn:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  color: #f44336;
  margin: 0.5rem 0;
  font-size: 0.8rem;
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  right: 0;
  bottom: 0;
  background: rgba(0, 0, 0, 0.9);
  display: flex;
  justify-content: center;
  align-items: center;
  z-index: 100;
  padding: 1rem;
}

.modal {
  background: #13131f;
  border-radius: 16px;
  padding: 1.5rem;
  width: 100%;
  max-width: 400px;
  border: 1px solid #1f1f2e;
}

.modal h3 {
  color: #ffd700;
  margin: 0 0 1rem;
  font-size: 1.1rem;
}

.warning-text {
  color: #f44336;
  font-size: 0.85rem;
  margin-bottom: 1rem;
}

.transfer-info {
  color: #888;
  font-size: 0.9rem;
  margin-bottom: 1rem;
}

.coming-soon {
  color: #ffd700;
  font-size: 0.9rem;
  margin-bottom: 0.5rem;
}

.coming-soon-sub {
  color: #666;
  font-size: 0.8rem;
  margin-bottom: 1rem;
}

.form-group {
  margin-bottom: 0.75rem;
}

.form-group label {
  display: block;
  color: #888;
  margin-bottom: 0.35rem;
  font-size: 0.8rem;
}

.form-group input,
.form-group select,
.form-input,
.form-select {
  width: 100%;
  padding: 0.75rem;
  border: 1px solid #333;
  border-radius: 8px;
  background: #0d0d14;
  color: #fff;
  font-size: 0.9rem;
  box-sizing: border-box;
}

.form-group input:focus,
.form-group select:focus,
.form-input:focus,
.form-select:focus {
  outline: none;
  border-color: #ffd700;
}

.modal-actions {
  display: flex;
  gap: 0.75rem;
  margin-top: 1rem;
}

.modal-actions .btn {
  flex: 1;
}

.recipient-form {
  display: flex;
  gap: 0.5rem;
  margin-bottom: 0.75rem;
  flex-wrap: nowrap;
}

.recipient-form .recipient-input {
  flex: 1;
  min-width: 0;
}

.recipient-form .btn {
  flex-shrink: 0;
  width: 44px;
  height: 44px;
  padding: 0;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 1.5rem;
}

.recipient-input {
  flex: 1;
  padding: 0.6rem;
  border: 1px solid #333;
  border-radius: 8px;
  background: #0d0d14;
  color: #fff;
  font-size: 0.85rem;
}

.recipient-search {
  width: 100%;
  padding: 0.6rem;
  border: 1px solid #333;
  border-radius: 8px;
  background: #0d0d14;
  color: #fff;
  font-size: 0.85rem;
  margin-bottom: 0.75rem;
  box-sizing: border-box;
}

.recipients-list {
  max-height: 200px;
  overflow-y: auto;
  margin-bottom: 0.75rem;
}

.no-recipients {
  text-align: center;
  padding: 1rem;
  color: #555;
  font-size: 0.85rem;
}

.recipient-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.6rem;
  background: #0d0d14;
  border-radius: 8px;
  margin-bottom: 0.4rem;
}

.recipient-info {
  display: flex;
  flex-direction: column;
  gap: 0.1rem;
}

.recipient-name {
  font-weight: 500;
  font-size: 0.85rem;
}

.recipient-address {
  font-size: 0.6rem;
  color: #555;
  font-family: monospace;
}

.btn-remove {
  background: transparent;
  border: none;
  color: #666;
  font-size: 0.9rem;
  cursor: pointer;
  padding: 0.4rem 0.6rem;
  border-radius: 4px;
}

.btn-remove:hover {
  background: #1f1f2e;
  color: #f44336;
}

.wallet-manager-modal {
  max-width: 95%;
  width: 95%;
  box-sizing: border-box;
}

.wallet-list {
  max-height: 250px;
  overflow-y: auto;
  margin-bottom: 0.75rem;
}

.wallet-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 0.75rem;
  background: #0d0d14;
  border-radius: 8px;
  margin-bottom: 0.4rem;
}

.wallet-info {
  flex: 1;
  display: flex;
  flex-direction: column;
  gap: 0.15rem;
  min-width: 0;
}

.wallet-name-row {
  display: flex;
  align-items: center;
  gap: 0.4rem;
}

.wallet-name {
  font-weight: 600;
  color: #fff;
  font-size: 0.9rem;
}

.active-badge {
  background: #ffd700;
  color: #0d0d14;
  font-size: 0.55rem;
  padding: 0.1rem 0.3rem;
  border-radius: 3px;
  font-weight: 600;
}

.wallet-address {
  font-size: 0.6rem;
  color: #555;
  font-family: monospace;
  word-break: break-all;
}

.wallet-balance {
  font-size: 0.75rem;
  color: #888;
}

.wallet-edit {
  flex: 1;
}

.wallet-edit .form-input {
  padding: 0.5rem;
  font-size: 0.85rem;
}

.wallet-actions {
  display: flex;
  gap: 0.3rem;
  margin-left: 0.5rem;
}

.btn-icon {
  background: transparent;
  border: 1px solid #333;
  color: #666;
  padding: 0.3rem 0.5rem;
  border-radius: 4px;
  cursor: pointer;
  font-size: 0.8rem;
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
  margin-bottom: 0.75rem;
}

.delete-confirm .warning-text {
  margin-bottom: 0.4rem;
  font-size: 0.85rem;
}
</style>
