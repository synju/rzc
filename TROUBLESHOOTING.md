# Troubleshooting Guide

## Backend (core-backend)

### 1. Cloudflare Tunnel URL Changes Every Restart
**Problem**: Quick tunnels generate random URLs. URLs hardcoded in Google OAuth caused `redirect_uri_mismatch` errors.

**Solution**: 
- Added `FRONTEND_URL` to backend settings
- Updated redirect URI in Google Cloud Console for current tunnel
- Documented in AGENTS.md

---

### 2. PostgreSQL "another operation is in progress" Error
**Problem**: `AsyncSession(engine)` vs `async_session()` confusion caused SQLAlchemy to reuse connections improperly. Also caused "TCPTransport closed" errors.

**Solution**:
- Use `NullPool` for asyncpg: `poolclass=NullPool` in `create_async_engine`
- Keep httpx AsyncClient OUTSIDE of db session context
- Ensure each db operation gets fresh connection

---

### 3. Event Loop Closed Error
**Problem**: `reload=True` in `uvicorn.run()` caused requests to fail when uvicorn auto-reloaded mid-request.

**Solution**:
```python
uvicorn.run("app:app", host="0.0.0.0", port=settings.port, reload=False)
```

---

### 4. Google OAuth Login Redirect for Web
**Problem**: Web login showed "copy token" page instead of auto-redirecting.

**Solution**: 
- Added `FRONTEND_URL` setting to backend
- Changed `/auth/callback` to redirect to `{frontend_url}/auth/callback?token=xxx`
- Frontend `AuthCallback.vue` handles token and calls `/auth/me` to get full user data including `is_admin`

---

### 5. Missing AsyncSession Import
**Problem**: After rewriting auth.py, other routers lost `AsyncSession` import.

**Solution**: Added to each router file:
```python
from sqlalchemy.ext.asyncio import AsyncSession
```

---

### 6. User is_admin Not Being Returned
**Problem**: `is_admin` was added to User model but not returned in `/auth/me`.

**Solution**: Added `is_admin` to `/auth/me` response and frontend stores.

---

### 7. SQLAlchemy MissingGreenlet Error
**Problem**: After `await db.commit()`, ORM objects become expired. Accessing attributes later (e.g., `admin.address`) triggers lazy loading which fails in async context.

**Symptoms**:
```
sqlalchemy.exc.MissingGreenlet: greenlet_spawn has not been called; can't call await_only() here.
```

**Solution**:
- Extract all needed values from ORM objects BEFORE async operations
- Use `update()` statements instead of mutating ORM objects directly
- Example:
```python
# Bad - causes MissingGreenlet
admin.avax_balance = avax_balance
await db.commit()
return {"address": admin.address}  # admin is expired!

# Good - extract values first
admin_address = admin.address
await db.execute(
    update(AdminWallet)
    .where(AdminWallet.id == admin.id)
    .values(avax_balance=avax_balance)
)
await db.commit()
return {"address": admin_address}
```

---

### 8. Backend Shutdown Hangs
**Problem**: Pressing Ctrl+C to stop backend hangs indefinitely.

**Solution**: Modified background_sync to check for shutdown every 1 second instead of sleeping for full 300 seconds:
```python
SHUTDOWN_CHECK_INTERVAL = 1
# ...
elapsed = 0
while elapsed < SYNC_INTERVAL and self.running:
    time.sleep(SHUTDOWN_CHECK_INTERVAL)
    elapsed += SHUTDOWN_CHECK_INTERVAL
```

---

### 9. Error Logging
**Problem**: Errors in routers not being captured for debugging.

**Solution**: All routers now log errors to `error.log` with full traceback:
```python
def log_error(msg: str):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{msg}\n")
        f.write(traceback.format_exc())
        f.write("\n")
```
- Server startup clears the log
- All router endpoints wrapped with try/except

---

### 10. Internal Transfer tx_hash Too Long
**Problem**: Internal transfers failed with `StringDataRightTruncationError: value too long for type character varying(66)`.

**Cause**: Internal transfer tx_hash was generated as `internal-{from_wallet_id}-{to_wallet_id}-{amount}` which exceeded 66 characters.

**Solution**: 
- Changed tx_hash format to `internal-{uuid}` (much shorter)
- Removed `unique=True` constraint from `tx_hash` column (needed because both sent and received records share the same tx_hash for internal transfers)

---

### 11. Unhandled Exceptions Not Logged
**Problem**: Exceptions at the ASGI level (like database constraint errors) were not being captured in error.log.

**Solution**: Added global exception handler to `app.py`:
```python
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_error(f"[Unhandled] {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})
```

---

## Web Frontend (core-web-frontend)

*No issues documented yet*

---

## Mobile Frontend (core-mobile-frontend)

*No issues documented yet*
