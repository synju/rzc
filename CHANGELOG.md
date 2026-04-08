# Changelog

## [Unreleased]

### Added
- `TROUBLESHOOTING.md` - Document for tracking known issues and solutions
- `error.log` - Backend error logging (cleared on startup)
- Error logging to `error.log` in all backend routers
- Admin Dashboard page with "Back to Dashboard" button
- Background sync shutdown improvements (1-second check interval)
- Global exception handler in app.py to capture all unhandled exceptions
- `/admin/wallets` endpoint returning total wallets and RZC in system
- `/admin/transactions` and `/admin/sync-transactions` endpoints
- AdminTransaction model and table for tracking admin RZC transactions
- "Refresh" button on balance card for syncing transaction history
- Copy to clipboard on admin wallet addresses
- Snowtrace API fallback for RPC failures (AVAX and RZC balance queries)

### Changed
- Updated project structure in PROJECT.md
- All wallet/ORM object mutations now use `update()` statements instead of direct attribute assignment
- Admin email removed from public docs (now in PRIVATE.md only)
- Renamed `changelog.md` to `CHANGELOG.md`, `private.md` to `PRIVATE.md`
- AGENTS.md now reminds to document solved problems in TROUBLESHOOTING.md
- Internal transfer tx_hash now uses `internal-{uuid}` format (was including wallet IDs and amount)
- formatRzc now shows 6 decimal places (was 2)
- Dashboard layout: wallet selector moved above balance card
- Admin transaction amount column changed to NUMERIC(78, 0) to support large values

### Fixed
- SQLAlchemy MissingGreenlet errors by extracting ORM values before async operations
- Backend shutdown hanging issue
- Various router endpoint errors now properly logged
- Internal transfer failing: tx_hash was too long for database column (66 chars) - shortened format and removed unique constraint
