<template>
  <div class="login">
    <div class="login-card">
      <h1>RZC</h1>
      <p class="subtitle">Sign in to your account</p>

      <button class="google-btn" @click="loginWithGoogle">
        <svg class="google-icon" viewBox="0 0 24 24">
          <path fill="#4285F4" d="M22.56 12.25c0-.78-.07-1.53-.2-2.25H12v4.26h5.92c-.26 1.37-1.04 2.53-2.21 3.31v2.77h3.57c2.08-1.92 3.28-4.74 3.28-8.09z"/>
          <path fill="#34A853" d="M12 23c2.97 0 5.46-.98 7.28-2.66l-3.57-2.77c-.98.66-2.23 1.06-3.71 1.06-2.86 0-5.29-1.93-6.16-4.53H2.18v2.84C3.99 20.53 7.7 23 12 23z"/>
          <path fill="#FBBC05" d="M5.84 14.09c-.22-.66-.35-1.36-.35-2.09s.13-1.43.35-2.09V7.07H2.18C1.43 8.55 1 10.22 1 12s.43 3.45 1.18 4.93l2.85-2.22.81-.62z"/>
          <path fill="#EA4335" d="M12 5.38c1.62 0 3.06.56 4.21 1.64l3.15-3.15C17.45 2.09 14.97 1 12 1 7.7 1 3.99 3.47 2.18 7.07l3.66 2.84c.87-2.6 3.3-4.53 6.16-4.53z"/>
        </svg>
        Continue with Google
      </button>

      <p class="terms">
        By continuing, you agree to our Terms of Service and Privacy Policy
      </p>
    </div>
  </div>
</template>

<script setup>
import { useRouter } from 'vue-router'
import api from '../api'

const router = useRouter()

const loginWithGoogle = () => {
  window.location.href = api.defaults.baseURL + '/auth/google/login'
}
</script>

<style scoped>
.login {
  min-height: 100vh;
  display: flex;
  justify-content: center;
  align-items: center;
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
}

.login-card {
  background: #0f0f1a;
  padding: 3rem;
  border-radius: 16px;
  text-align: center;
  max-width: 400px;
  width: 90%;
}

.login-card h1 {
  color: #ffd700;
  font-size: 2.5rem;
  margin: 0 0 0.5rem;
}

.subtitle {
  color: #888;
  margin: 0 0 2rem;
}

.google-btn {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 1rem;
  width: 100%;
  padding: 1rem;
  background: #fff;
  border: none;
  border-radius: 8px;
  font-size: 1rem;
  font-weight: 600;
  cursor: pointer;
  transition: all 0.2s;
}

.google-btn:hover {
  background: #f5f5f5;
  transform: translateY(-2px);
}

.google-icon {
  width: 24px;
  height: 24px;
}

.terms {
  color: #666;
  font-size: 0.8rem;
  margin: 2rem 0 0;
}
</style>
