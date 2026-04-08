# RZC Project Notes

> **Full documentation**: See `...../rzc/PROJECT.md` for complete project details.

## CRITICAL: Do NOT Start Services

**The user starts all services. You are NOT permitted to start anything.**

Do NOT:
- Start uvicorn/backend
- Start cloudflared
- Start vite
- Start any other services

Only:
- Stop processes if asked
- Make code changes
- Update configuration files
- Run lint/typecheck
- Build frontends when requested

## CRITICAL: NO HARDCODED URLs

**Never hardcode any URLs in source code.** All URLs must be:
- In `.env` files
- Accessed programmatically (e.g., `import.meta.env.VITE_API_URL` or `settings.google_redirect_uri`)

If you see a hardcoded URL, fix it to use the env var approach.

## Cloudflare Tunnel

**IMPORTANT**: Cloudflared quick tunnels (`cloudflared tunnel --url http://localhost:8001`) ALWAYS generate a NEW random URL every time they restart. They do NOT persist URLs between restarts.

If you need a PERSISTENT URL, you must:
1. Create a named tunnel with `cloudflared tunnel create <name>`
2. Configure DNS records
3. Use `cloudflared tunnel run <name>`

For quick tunnels used during development:
- The URL changes on EVERY restart
- Update all references after restarting (backend .env, mobile .env, Google OAuth redirect URIs)
- Or: keep the tunnel running and don't restart it

## Google OAuth Redirect URIs

When the tunnel URL changes:
1. Update `GOOGLE_REDIRECT_URI` in `...../rzc/core-backend/.env`
2. Update `VITE_API_URL` in `...../rzc/core-mobile-frontend/.env`
3. Update the redirect URI in Google Cloud Console
4. Rebuild and sync the mobile app

## Cloudflare Tunnel URL

Always changes whenever cloudflare is started up again.

Always update these when URL changes:
1. Backend: `...../rzc/core-backend/.env` → `GOOGLE_REDIRECT_URI`
2. Mobile: `...../rzc/core-mobile-frontend/.env` → `VITE_API_URL`
3. Google OAuth Console → redirect URIs
