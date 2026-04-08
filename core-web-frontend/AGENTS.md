# RZC Core Frontend - Agent Instructions

## Project Overview

Vue.js 3 frontend for RZC Core wallet system.

## Setup

```bash
cd /path/to/rzc-core-frontend
npm install
```

## Environment Variables

Copy `.env.example` to `.env` and configure:
```
VITE_API_URL=http://localhost:8001
```

## Running Development Server

```bash
npm run dev
```

## Building for Production

```bash
npm run build
```

## Tech Stack

- Vue 3 (Composition API)
- Vite
- Vue Router
- Pinia (state management)
- Axios (HTTP client)

## Project Structure

```
src/
├── api/
│   └── index.js       # Axios API client
├── components/        # Reusable components
├── router/
│   └── index.js       # Vue Router config
├── stores/
│   └── auth.js        # Auth Pinia store
├── views/
│   ├── Landing.vue     # Landing page
│   ├── Login.vue       # Login page
│   ├── AuthCallback.vue # OAuth callback
│   └── Dashboard.vue   # Main wallet dashboard
├── App.vue
├── main.js
└── style.css
```

## Pages

| Route | Component | Description |
|-------|-----------|-------------|
| `/` | Landing | Landing page |
| `/login` | Login | Google OAuth login |
| `/auth/callback` | AuthCallback | OAuth redirect handler |
| `/dashboard` | Dashboard | User wallet dashboard |

## API Integration

Frontend communicates with RZC Core backend via Axios. All endpoints:

- `GET /auth/google/login` - Get Google OAuth URL
- `GET /auth/google/callback` - OAuth callback
- `GET /auth/me` - Get current user
- `GET /wallet/` - Get wallet info
- `POST /wallet/create` - Create wallet
- `POST /wallet/sync-balance` - Sync balance from blockchain
- `POST /transactions/send` - Send RZC
- `GET /transactions/history` - Get transaction history

## Authentication Flow

1. User clicks "Login with Google"
2. Redirect to backend `/auth/google/login`
3. Google OAuth consent screen
4. Callback to `/auth/callback?code=xxx`
5. Backend returns JWT token
6. Frontend stores token, redirects to Dashboard
7. All subsequent requests include `Authorization: Bearer <token>`
