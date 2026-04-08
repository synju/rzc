import asyncio
import threading
import time
import traceback
from uuid import uuid4

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, Wallet, Transaction


RPC_URLS = [
    "https://avalanche-c-chain-rpc.publicnode.com",
    "https://api.avax.network/ext/bc/C/rpc",
]
CONTRACT_ADDRESS = "0x8583645670154b3bc3f9c48a1864261fd1f26758"
SYNC_INTERVAL = 300
SHUTDOWN_CHECK_INTERVAL = 1
ERROR_LOG = "error.log"


def log_error(msg: str):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{time.strftime('%Y-%m-%d %H:%M:%S')} - {msg}\n")
        f.write(traceback.format_exc())
        f.write("\n")


class BackgroundSync:
    def __init__(self):
        self.running = False
        self.thread = None
        self._stop_event = threading.Event()

    def start(self):
        if self.running:
            return
        with open(ERROR_LOG, "w") as f:
            f.write("")
        self.running = True
        self._stop_event.clear()
        self.thread = threading.Thread(target=self._run, daemon=True)
        self.thread.start()
        print(f"[BackgroundSync] Started - syncing every {SYNC_INTERVAL} seconds")

    def stop(self):
        self.running = False
        self._stop_event.set()
        if self.thread:
            self.thread.join(timeout=5)
        print("[BackgroundSync] Stopped")

    def _run(self):
        while self.running:
            try:
                asyncio.run(self._sync_all_wallets())
            except Exception as e:
                log_error(f"[BackgroundSync] Error: {e}")
            
            elapsed = 0
            while elapsed < SYNC_INTERVAL and self.running:
                time.sleep(SHUTDOWN_CHECK_INTERVAL)
                elapsed += SHUTDOWN_CHECK_INTERVAL

    async def _sync_all_wallets(self):
        print(f"[BackgroundSync] Starting sync at {time.strftime('%Y-%m-%d %H:%M:%S')}")
        
        async with AsyncSession(engine) as db:
            result = await db.execute(select(Wallet.id, Wallet.address, Wallet.last_synced_block))
            wallet_rows = result.all()
        
        wallet_data = [
            {"id": row[0], "address": row[1], "last_synced_block": row[2]}
            for row in wallet_rows
        ]
        
        for wdata in wallet_data:
            try:
                await self._sync_wallet(wdata)
            except Exception as e:
                log_error(f"[BackgroundSync] Error syncing wallet {wdata['address']}: {e}")

    async def _sync_wallet(self, wallet_data: dict):
        for rpc_url in RPC_URLS:
            try:
                await self._sync_wallet_with_rpc(wallet_data, rpc_url)
                return
            except Exception as e:
                log_error(f"[BackgroundSync] RPC {rpc_url} failed for {wallet_data['address']}: {e}")
                continue
        
        print(f"[BackgroundSync] All RPCs failed for wallet {wallet_data['address']}")

    async def _sync_wallet_with_rpc(self, wallet_data: dict, rpc_url: str):
        import httpx
        wallet_address = wallet_data["address"]
        wallet_id = wallet_data["id"]
        last_synced_block = wallet_data.get("last_synced_block")

        async with AsyncSession(engine) as db:
            await self._do_sync(db, wallet_id, wallet_address, last_synced_block, rpc_url)
            await db.commit()

    async def _do_sync(self, db: AsyncSession, wallet_id: str, wallet_address: str, last_synced_block, rpc_url: str):
        import httpx
        
        async with httpx.AsyncClient() as client:
            block_response = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_blockNumber",
                "params": [],
                "id": 1
            }, timeout=30.0)
            current_block = int(block_response.json()["result"], 16)

            balance_selector = "0x70a08231"
            address_hex = wallet_address[2:].lower().zfill(64)
            balance_data = balance_selector + address_hex

            balance_response = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_call",
                "params": [{"to": CONTRACT_ADDRESS, "data": balance_data}, "latest"],
                "id": 1
            }, timeout=30.0)
            
            balance_result = balance_response.json()
            balance_hex = balance_result.get("result", "0x0")
            new_balance = int(balance_hex, 16) if balance_hex and len(balance_hex) > 2 else 0

            from_block = last_synced_block if last_synced_block else max(0, current_block - 1000)
            
            incoming_filter = {
                "fromBlock": hex(from_block),
                "toBlock": hex(current_block),
                "address": CONTRACT_ADDRESS,
                "topics": [
                    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                    None,
                    "0x" + wallet_address.lower().replace("0x", "").zfill(64)
                ]
            }
            
            outgoing_filter = {
                "fromBlock": hex(from_block),
                "toBlock": hex(current_block),
                "address": CONTRACT_ADDRESS,
                "topics": [
                    "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                    "0x" + wallet_address.lower().replace("0x", "").zfill(64),
                    None
                ]
            }
            
            incoming_response = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [incoming_filter],
                "id": 1
            }, timeout=60.0)
            
            outgoing_response = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getLogs",
                "params": [outgoing_filter],
                "id": 1
            }, timeout=60.0)
            
            incoming_logs = incoming_response.json().get("result", [])
            outgoing_logs = outgoing_response.json().get("result", [])
            logs = incoming_logs + outgoing_logs
            
            new_tx_count = 0
            for log in logs:
                tx_hash = log["transactionHash"]
                
                existing = await db.execute(select(Transaction).where(Transaction.tx_hash == tx_hash))
                if existing.scalar_one_or_none():
                    continue

                block_number = int(log["blockNumber"][2:], 16)
                data = log["data"][2:]
                amount = int(data[:64], 16) if len(data) >= 64 else 0
                from_address = "0x" + log["topics"][1][26:]
                to_address = "0x" + log["topics"][2][26:]

                tx_type = "received" if from_address.lower() != wallet_address.lower() else "sent"
                
                tx_record = Transaction(
                    id=str(uuid4()),
                    wallet_id=wallet_id,
                    tx_hash=tx_hash,
                    type=tx_type,
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    block_number=block_number,
                    status="confirmed"
                )
                db.add(tx_record)
                new_tx_count += 1

            await db.execute(
                update(Wallet)
                .where(Wallet.id == wallet_id)
                .values(balance=new_balance, last_synced_block=current_block)
            )
            
            if new_tx_count > 0:
                print(f"[BackgroundSync] Wallet {wallet_address}: +{new_tx_count} txs, balance: {new_balance}")


background_sync = BackgroundSync()
