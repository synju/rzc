#!/bin/bash
echo "Stopping cloudflared..."
pkill -f "cloudflared tunnel" 2>/dev/null
sleep 1
echo "Stopping uvicorn..."
pkill -f "uvicorn app:app" 2>/dev/null
fuser -k 8001/tcp 2>/dev/null
sleep 1
echo "Checking processes..."
ps aux | grep -E "cloudflared|uvicorn|8001" | grep -v grep || echo "All stopped"
