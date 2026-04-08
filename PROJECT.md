# RZC (Royal Zeni Coin) Project Documentation

## Project Overview

RZC is a cryptocurrency token system built on Avalanche C-Chain with:
- Smart contract on Avalanche
- Backend API (FastAPI + PostgreSQL)
- Web frontend (Vue.js)
- Mobile app (Capacitor + Vue.js)

## System Architecture

### Components

1. **Smart Contract**: See `PRIVATE.md` (RZC Token on Avalanche C-Chain)
2. **Backend**: FastAPI on port 8001
3. **Frontend Web**: Vue.js dev server on port 5173
4. **Mobile App**: Capacitor-built Android app
5. **Database**: PostgreSQL (local)
6. **Tunnel**: Cloudflare quick tunnel for mobile access

## Project Structure

```
...../rzc/
├── core-backend/           # FastAPI backend
│   ├── app.py              # Main FastAPI app
│   ├── database.py         # SQLAlchemy models & engine
│   ├── background_sync.py   # 5-minute wallet sync
│   └── routers/
│       ├── auth.py          # Google OAuth authentication
│       ├── wallet.py        # Wallet CRUD operations
│       ├── transactions.py   # Send/transfer RZC
│       ├── recipients.py     # Saved recipients
│       └── admin.py         # Admin/relayer operations
├── core-web-frontend/       # Vue.js web frontend
├── core-mobile-frontend/   # Capacitor mobile app
└── utilities/             # Helper scripts
```

## Key Features

### Multi-Wallet Support
Users can create, switch, rename, and delete wallets. Each wallet has:
- Ethereum-format address
- Balance (stored as BigInteger)
- Encrypted private key blob

### Internal vs External Transfers
- **Internal transfers**: Free, DB-only balance updates (not real blockchain txs)
- **External sends**: Uses admin wallet as relayer to pay AVAX gas for blockchain transaction

### Relayer System
The admin wallet pays gas for external transfers. This allows users without AVAX to send RZC.

### Background Sync
Every 5 minutes, the system syncs all wallets with the blockchain:
- Fetches transaction logs (Transfer events)
- Updates wallet balances
- Records transaction history

## Starting Services

> **CRITICAL: Do NOT start any services unless explicitly asked.**
> The user starts all services. Only stop processes, make code changes, or build when requested.

### Backend (WSL/Linux)
```bash
cd ...../rzc/core-backend
source venv/bin/activate
uvicorn app:app --host 0.0.0.0 --port 8001
```

### Cloudflare Tunnel (WSL/Linux)
```bash
/tmp/cloudflared tunnel --url http://localhost:8001
```

### Web Frontend (WSL/Linux)
```bash
cd ...../rzc/core-web-frontend
npm run dev
```

### Restart PostgreSQL (Windows/Linux - requires sudo)
```bash
sudo systemctl restart postgresql
```

## Issues Encountered & Solutions

### 1. Cloudflare Tunnel URL Changes Every Restart
**Problem**: Quick tunnels generate random URLs. URLs hardcoded in Google OAuth caused `redirect_uri_mismatch` errors.

**Solution**: 
- Added `FRONTEND_URL` to backend settings
- Updated redirect URI in Google Cloud Console for current tunnel
- Documented in AGENTS.md

### 2. PostgreSQL "another operation is in progress" Error
**Problem**: `AsyncSession(engine)` vs `async_session()` confusion caused SQLAlchemy to reuse connections improperly. Also caused "TCPTransport closed" errors.

**Solution**:
- Use `NullPool` for asyncpg: `poolclass=NullPool` in `create_async_engine`
- Keep httpx AsyncClient OUTSIDE of db session context
- Ensure each db operation gets fresh connection

### 3. Event Loop Closed Error
**Problem**: `reload=True` in `uvicorn.run()` caused requests to fail when uvicorn auto-reloaded mid-request.

**Solution**:
```python
uvicorn.run("app:app", host="0.0.0.0", port=settings.port, reload=False)
```

### 4. Google OAuth Login Redirect for Web
**Problem**: Web login showed "copy token" page instead of auto-redirecting.

**Solution**: 
- Added `FRONTEND_URL` setting to backend
- Changed `/auth/callback` to redirect to `{frontend_url}/auth/callback?token=xxx`
- Frontend `AuthCallback.vue` handles token and calls `/auth/me` to get full user data including `is_admin`

### 5. Missing AsyncSession Import
**Problem**: After rewriting auth.py, other routers lost `AsyncSession` import.

**Solution**: Added to each router file:
```python
from sqlalchemy.ext.asyncio import AsyncSession
```

### 6. User is_admin Not Being Returned
**Problem**: `is_admin` was added to User model but not returned in `/auth/me`.

**Solution**: Added `is_admin` to `/auth/me` response and frontend stores.

### 7. SQLAlchemy MissingGreenlet Error
**Problem**: After `await db.commit()`, ORM objects become expired. Accessing attributes later (e.g., `admin.address`) triggers lazy loading which fails in async context.

**Solution**: 
- Extract all needed values from ORM objects BEFORE async operations
- Use `update()` statements instead of mutating ORM objects directly
- All routers and background_sync log errors to `error.log`

## Error Logging

All backend errors are logged to `error.log` in `core-backend/` with full traceback:
- Server startup clears the log
- All router endpoints log exceptions
- Background sync errors are captured

## API Endpoints

### Auth
- `GET /auth/google/login` - Redirect to Google OAuth
- `GET /auth/google/callback` - Handle OAuth callback
- `GET /auth/me` - Get current user (includes `is_admin`)
- `POST /auth/google-mobile` - Mobile OAuth

### Wallet
- `GET /wallet/` - List user wallets
- `POST /wallet/` - Create wallet
- `POST /wallet/switch/{id}` - Switch active wallet
- `DELETE /wallet/{id}` - Delete wallet

### Transactions
- `POST /transactions/send` - External send (via relayer)
- `POST /transactions/transfer` - Internal transfer (free)
- `GET /transactions/` - Transaction history

### Admin
- `GET /admin/wallet` - Admin wallet info
- `GET /admin/wallet/rzc-balance` - Admin RZC balance
- `POST /admin/wallet/sync-balance` - Sync AVAX balance

## Database Schema

### Users
```sql
id, email, google_id, is_admin, created_at, updated_at
```

### Wallets
```sql
id, user_id, name, address, balance, is_active, encrypted_wallet_blob, last_synced_block, created_at, updated_at
```

### Transactions
```sql
id, wallet_id, tx_hash, type, from_address, to_address, amount, block_number, status, created_at
```

### Recipients
```sql
id, user_id, name, address, created_at
```

### AdminWallet
```sql
id, address, encrypted_private_key, avax_balance, is_active, created_at, updated_at
```

## Frontend Environment Variables

### Backend .env
```
GOOGLE_REDIRECT_URI=https://{tunnel_url}/auth/google/callback
FRONTEND_URL=http://localhost:5173
```

### Mobile .env (`...../rzc/core-mobile-frontend/.env`)
```
VITE_API_URL=https://{tunnel_url}
```

### Mobile Login.vue (`...../rzc/core-mobile-frontend/src/views/Login.vue`)
Uses `import.meta.env.VITE_API_URL` for Browser plugin login - NOT hardcoded

## Notes for New Sessions

1. **NO HARDCODED URLs** - Never hardcode any URLs (Cloudflare, API endpoints, etc.) in source code. All URLs must be in `.env` files and accessed programmatically via `import.meta.env` or `settings`
2. **Cloudflare URL changes** - Always check current tunnel URL before testing OAuth (stored in AGENTS.md)
3. **Backend uses NullPool** - This was necessary to fix async connection issues
4. **Frontend needs vite restart** - After .env changes
5. **Mobile needs rebuild** - After code or .env changes (in `...../rzc/core-mobile-frontend/`): `npm run build && npx cap sync android`
6. **Private credentials** - See `PRIVATE.md` (DO NOT COMMIT)
7. **Error log** - Check `core-backend/error.log` for backend errors with full traceback

## Testing Admin Features

1. Login with admin email (see `PRIVATE.md`)
2. Click "Admin" button in header
3. View admin wallet balances (AVAX + RZC)

## Tracking Transactions on Snowtrace

**Avalanche C-Chain Explorer**: https://snowtrace.io

### To track a transaction:
- Paste the `tx_hash` from the response into Snowtrace's search bar
- Example: `https://snowtrace.io/tx/0x...`

### To track an address:
- Paste any wallet address to see its token balances and history
- Example: `https://snowtrace.io/address/0x...`

### Network Details
- **Network**: Avalanche C-Chain
- **Chain ID**: 43114
- **RZC Token Contract**: See `PRIVATE.md`
