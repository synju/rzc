<template>
  <div class="landing">
    <div class="logo">RZC</div>
    <h1>Royal Zeni Coin</h1>
    <p>Your secure cloud wallet for RZC</p>
    <button @click="login" class="btn-primary">Get Started</button>
  </div>
</template>

<script setup lang="ts">
import { onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()

onMounted(() => {
  if (authStore.isAuthenticated) {
    router.push('/dashboard')
  }
})

const login = () => {
  router.push('/login')
}
</script>

<style scoped>
.landing {
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
  margin-bottom: 2rem;
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
}
</style>