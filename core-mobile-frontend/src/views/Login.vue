<template>
  <div class="login">
    <div class="logo">RZC</div>
    <h1>Welcome Back</h1>
    <p>Sign in to continue</p>
    <button @click="openWebLogin" class="btn-google">
      <span class="google-icon">G</span>
      Continue with Google
    </button>
    <p class="divider">Or</p>
    <input v-model="manualToken" type="text" placeholder="Paste your token here" class="token-input" />
    <button @click="submitToken" class="btn-primary" :disabled="!manualToken">
      Submit Token
    </button>
    <p v-if="error" class="error">{{ error }}</p>
    <p v-if="success" class="success">{{ success }}</p>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'
import { Browser } from '@capacitor/browser'
import api from '../api'

const router = useRouter()
const authStore = useAuthStore()
const manualToken = ref('')
const error = ref('')
const success = ref('')

const openWebLogin = async () => {
  const baseUrl = import.meta.env.VITE_API_URL || 'http://localhost:8001'
  const loginUrl = `${baseUrl}/auth/google/login?show_token=true`
  await Browser.open({ url: loginUrl })
}

const submitToken = async () => {
  error.value = ''
  success.value = ''
  try {
    const response = await api.get('/auth/me', {
      headers: { Authorization: `Bearer ${manualToken.value}` }
    })
    success.value = 'Token valid! Redirecting...'
    await new Promise(r => setTimeout(r, 500))
    authStore.setAuth(manualToken.value, response.data)
    router.push('/dashboard')
  } catch (e: any) {
    error.value = e.response?.data?.detail || 'Invalid token'
  }
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  background: #0d0d14;
  color: #fff;
  text-align: center;
  padding: 2rem;
}

.logo {
  font-size: 3rem;
  font-weight: 700;
  color: #ffd700;
  letter-spacing: 4px;
  margin-bottom: 1rem;
}

h1 {
  font-size: 1.5rem;
  margin-bottom: 0.5rem;
}

p {
  color: #888;
  margin-bottom: 1rem;
}

.divider {
  margin: 1.5rem 0;
}

.token-input {
  width: 100%;
  padding: 1rem;
  border: 1px solid #333;
  border-radius: 10px;
  background: #13131f;
  color: #fff;
  font-size: 0.9rem;
  margin-bottom: 1rem;
  text-align: center;
}

.btn-google {
  display: flex;
  align-items: center;
  gap: 1rem;
  background: #fff;
  color: #333;
  border: none;
  padding: 1rem 2rem;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  font-size: 1rem;
  width: 100%;
  max-width: 300px;
  justify-content: center;
}

.google-icon {
  width: 24px;
  height: 24px;
  background: #4285f4;
  color: #fff;
  border-radius: 4px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-weight: 700;
}

.btn-primary {
  background: #ffd700;
  color: #0d0d14;
  border: none;
  padding: 1rem 2rem;
  border-radius: 10px;
  font-weight: 600;
  cursor: pointer;
  font-size: 1rem;
  width: 100%;
  max-width: 300px;
}

.btn-primary:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.error {
  color: #f44336;
  margin-top: 1rem;
}

.success {
  color: #4caf50;
  margin-top: 1rem;
}
</style>