import traceback
from eth_account import Account
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from database import engine, User, Wallet, Transaction, AdminWallet, AdminTransaction, settings
from routers.auth import get_current_user

ERROR_LOG = "error.log"


def log_error(msg: str):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{msg}\n")
        f.write(traceback.format_exc())
        f.write("\n")


router = APIRouter(prefix="/admin", tags=["admin"])


class CreateAdminWalletResponse(BaseModel):
    address: str
    encrypted_private_key: str


class AdminWalletResponse(BaseModel):
    address: str
    avax_balance: int


class RelayerSendRequest(BaseModel):
    from_wallet_id: str
    to_address: str
    amount: int


class RelayerSendResponse(BaseModel):
    success: bool
    tx_hash: str | None
    from_address: str
    to_address: str
    amount: int
    gas_fee: int


def encrypt_private_key(private_key: str, encryption_key: str) -> str:
    from cryptography.fernet import Fernet
    import base64
    key = base64.urlsafe_b64encode(encryption_key.encode().ljust(32)[:32])
    f = Fernet(key)
    return f.encrypt(private_key.encode()).decode()


def decrypt_private_key(encrypted_key: str, encryption_key: str) -> str:
    from cryptography.fernet import Fernet
    import base64
    key = base64.urlsafe_b64encode(encryption_key.encode().ljust(32)[:32])
    f = Fernet(key)
    return f.decrypt(encrypted_key.encode()).decode()


async def send_transaction(from_address: str, to_address: str, amount: int, private_key: str, rpc_url: str) -> tuple[str, int]:
    import httpx
    
    chain_id = 43114

    nonce_data = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionCount",
        "params": [from_address, "pending"],
        "id": 1
    }

    async with httpx.AsyncClient() as client:
        nonce_response = await client.post(rpc_url, json=nonce_data, timeout=30.0)
        nonce_result = nonce_response.json()
        nonce = int(nonce_result["result"][2:], 16) if nonce_result.get("result", "").startswith("0x") else 0

    gas_data = {
        "jsonrpc": "2.0",
        "method": "eth_gasPrice",
        "params": [],
        "id": 1
    }

    async with httpx.AsyncClient() as client:
        gas_response = await client.post(rpc_url, json=gas_data, timeout=30.0)
        gas_result = gas_response.json()
        gas_price = int(gas_result["result"][2:], 16) if gas_result.get("result", "").startswith("0x") else 25000000000

    token_address = "0x8583645670154b3bc3f9c48a1864261fd1f26758"
    to_address_normalized = to_address.lower().replace("0x", "")
    amount_hex = hex(amount)[2:].zfill(64)

    selector = "0xa9059cbb"
    padded_to = to_address_normalized.zfill(64)
    data = selector + padded_to + amount_hex

    gas_limit = 70000

    tx = {
        "from": from_address,
        "to": token_address,
        "nonce": hex(nonce),
        "gasPrice": hex(gas_price),
        "gasLimit": hex(gas_limit),
        "value": "0x0",
        "data": "0x" + data,
        "chainId": chain_id
    }

    signed_tx = Account.sign_transaction(tx, private_key)

    async with httpx.AsyncClient() as client:
        send_data = {
            "jsonrpc": "2.0",
            "method": "eth_sendRawTransaction",
            "params": ["0x" + signed_tx.rawTransaction.hex()],
            "id": 1
        }
        send_response = await client.post(rpc_url, json=send_data, timeout=30.0)
        send_result = send_response.json()

    if "result" in send_result:
        gas_fee = 70000 * gas_price
        return send_result["result"], gas_fee
    else:
        raise Exception(send_result.get("error", {}).get("message", "Unknown error"))


@router.post("/wallet", response_model=CreateAdminWalletResponse)
async def create_admin_wallet(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    async with AsyncSession(engine) as db:
        result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
        existing = result.scalar_one_or_none()
        
        if existing:
            raise HTTPException(status_code=400, detail="Admin wallet already exists")

        acct = Account.create()
        encrypted_pk = encrypt_private_key(acct.key.hex(), settings.encryption_key)

        admin_wallet = AdminWallet(
            id=str(uuid4()),
            address=acct.address,
            encrypted_private_key=encrypted_pk,
            avax_balance=0,
            is_active=True
        )
        db.add(admin_wallet)
        await db.commit()

        return CreateAdminWalletResponse(
            address=acct.address,
            encrypted_private_key=encrypted_pk
        )


@router.get("/wallet", response_model=AdminWalletResponse)
async def get_admin_wallet(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    async with AsyncSession(engine) as db:
        result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
        admin = result.scalar_one_or_none()

        if not admin:
            raise HTTPException(status_code=404, detail="Admin wallet not found")

        return AdminWalletResponse(
            address=admin.address,
            avax_balance=admin.avax_balance
        )


@router.post("/wallet/sync-balance")
async def sync_admin_avax_balance(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
            admin = result.scalar_one_or_none()

            if not admin:
                raise HTTPException(status_code=404, detail="Admin wallet not found")

            admin_address = admin.address

            import httpx
            rpc_urls = [
                "https://avalanche-c-chain-rpc.publicnode.com",
                "https://api.avax.network/ext/bc/C/rpc",
            ]
            
            avax_balance = 0
            
            for rpc_url in rpc_urls:
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(rpc_url, json={
                            "jsonrpc": "2.0",
                            "method": "eth_getBalance",
                            "params": [admin_address, "latest"],
                            "id": 1
                        }, timeout=30.0)
                        result_data = response.json()

                    balance_hex = result_data.get("result", "0x0")
                    avax_balance = int(balance_hex, 16) if balance_hex and len(balance_hex) > 2 else 0
                    if avax_balance > 0:
                        break
                except:
                    continue
            
            if avax_balance == 0:
                async with httpx.AsyncClient() as client:
                    snowtrace_url = f"https://api.snowtrace.io/api?module=account&action=balance&address={admin_address}"
                    response = await client.get(snowtrace_url, timeout=30.0)
                    data = response.json()
                    if data.get("status") == "1" and data.get("result"):
                        avax_balance = int(data["result"])

            from sqlalchemy import update
            await db.execute(
                update(AdminWallet)
                .where(AdminWallet.id == admin.id)
                .values(avax_balance=avax_balance)
            )
            await db.commit()

            return {"address": admin_address, "avax_balance": avax_balance}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Admin] sync_admin_avax_balance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallet/rzc-balance")
async def get_admin_rzc_balance(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
            admin = result.scalar_one_or_none()

            if not admin:
                raise HTTPException(status_code=404, detail="Admin wallet not found")

            admin_address = admin.address

            import httpx
            token_address = "0x8583645670154b3bc3f9c48a1864261fd1f26758"

            rpc_urls = [
                "https://avalanche-c-chain-rpc.publicnode.com",
                "https://api.avax.network/ext/bc/C/rpc",
            ]
            
            rzc_balance = 0
            
            for rpc_url in rpc_urls:
                try:
                    balance_selector = "0x70a08231"
                    address_hex = admin_address[2:].lower().zfill(64)
                    balance_data = balance_selector + address_hex

                    async with httpx.AsyncClient() as client:
                        response = await client.post(rpc_url, json={
                            "jsonrpc": "2.0",
                            "method": "eth_call",
                            "params": [{"to": token_address, "data": "0x" + balance_data}, "latest"],
                            "id": 1
                        }, timeout=30.0)
                        result_data = response.json()

                    balance_hex = result_data.get("result", "0x0")
                    rzc_balance = int(balance_hex, 16) if balance_hex and len(balance_hex) > 2 else 0
                    if rzc_balance > 0:
                        break
                except:
                    continue
            
            if rzc_balance == 0:
                async with httpx.AsyncClient() as client:
                    snowtrace_url = f"https://api.snowtrace.io/api?module=account&action=tokenbalance&contractaddress={token_address}&address={admin_address}"
                    response = await client.get(snowtrace_url, timeout=30.0)
                    data = response.json()
                    if data.get("status") == "1" and data.get("result"):
                        rzc_balance = int(data["result"])

            return {"address": admin_address, "rzc_balance": rzc_balance}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Admin] get_admin_rzc_balance error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/wallets")
async def get_all_wallets(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(Wallet).where(Wallet.address.isnot(None)))
            wallets = result.scalars().all()
            
            total_rzc = sum(w.balance or 0 for w in wallets)
            
            return {
                "total_wallets": len(wallets),
                "total_rzc": total_rzc,
                "wallets": [
                    {
                        "id": w.id,
                        "address": w.address,
                        "balance": w.balance,
                        "user_id": w.user_id
                    }
                    for w in wallets
                ]
            }
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Admin] get_all_wallets error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/transactions")
async def get_admin_transactions(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
            admin = result.scalar_one_or_none()

            if not admin:
                raise HTTPException(status_code=404, detail="Admin wallet not found")

            tx_result = await db.execute(
                select(AdminTransaction)
                .where(AdminTransaction.admin_wallet_id == admin.id)
                .order_by(AdminTransaction.created_at.desc())
                .limit(50)
            )
            db_transactions = tx_result.scalars().all()

            transactions = []
            for tx in db_transactions:
                transactions.append({
                    "type": tx.type,
                    "tx_hash": tx.tx_hash,
                    "block": tx.block_number or 0,
                    "amount": tx.amount,
                    "from_address": tx.from_address,
                    "to_address": tx.to_address,
                    "token": tx.token
                })

            return {"address": admin.address, "transactions": transactions}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Admin] get_admin_transactions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/sync-transactions")
async def sync_admin_transactions(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
            admin = result.scalar_one_or_none()

            if not admin:
                raise HTTPException(status_code=404, detail="Admin wallet not found")

            admin_address = admin.address
            admin_id = admin.id

            import httpx
            rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"
            token_address = "0x8583645670154b3bc3f9c48a1864261fd1f26758"

            async with httpx.AsyncClient() as client:
                block_response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                }, timeout=30.0)
                current_block = int(block_response.json()["result"], 16)
                from_block = max(0, current_block - 1000)

                incoming_filter = {
                    "fromBlock": hex(from_block),
                    "toBlock": hex(current_block),
                    "address": token_address,
                    "topics": [
                        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                        None,
                        "0x" + admin_address.lower().replace("0x", "").zfill(64)
                    ]
                }

                outgoing_filter = {
                    "fromBlock": hex(from_block),
                    "toBlock": hex(current_block),
                    "address": token_address,
                    "topics": [
                        "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                        "0x" + admin_address.lower().replace("0x", "").zfill(64),
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

                existing = await db.execute(select(AdminTransaction).where(AdminTransaction.tx_hash == tx_hash))
                if existing.scalar_one_or_none():
                    continue

                block_number = int(log["blockNumber"][2:], 16)
                data = log["data"][2:]
                amount = int(data[:64], 16) if len(data) >= 64 else 0
                from_address = "0x" + log["topics"][1][26:]
                to_address = "0x" + log["topics"][2][26:]

                tx_type = "received" if from_address.lower() != admin_address.lower() else "sent"

                tx_record = AdminTransaction(
                    admin_wallet_id=admin_id,
                    tx_hash=tx_hash,
                    type=tx_type,
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    block_number=block_number,
                    token="RZC",
                    status="confirmed"
                )
                db.add(tx_record)
                new_tx_count += 1

            await db.commit()

            return {"message": f"Synced {new_tx_count} new transactions"}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Admin] sync_admin_transactions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/relayer/send", response_model=RelayerSendResponse)
async def relayer_send(request: RelayerSendRequest, current_user: User = Depends(get_current_user)):
    try:
        async with AsyncSession(engine) as db:
            admin_result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
            admin = admin_result.scalar_one_or_none()

            if not admin:
                raise HTTPException(status_code=404, detail="Admin wallet not found")

            if admin.avax_balance < 50000000000000000:
                raise HTTPException(status_code=400, detail="Insufficient AVAX in relayer for gas")

            wallet_result = await db.execute(
                select(Wallet).where(Wallet.id == request.from_wallet_id, Wallet.user_id == current_user.id)
            )
            wallet = wallet_result.scalar_one_or_none()

            if not wallet or not wallet.address:
                raise HTTPException(status_code=404, detail="Wallet not found")

            if wallet.balance < request.amount:
                raise HTTPException(status_code=400, detail="Insufficient RZC balance")

            if len(request.to_address) != 42 or not request.to_address.startswith("0x"):
                raise HTTPException(status_code=400, detail="Invalid recipient address")

            admin_address = admin.address
            admin_encrypted_pk = admin.encrypted_private_key
            admin_id = admin.id
            wallet_address = wallet.address
            wallet_id = wallet.id

            rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"
            
            private_key = decrypt_private_key(admin_encrypted_pk, settings.encryption_key)
            tx_hash, gas_fee = await send_transaction(
                admin_address,
                request.to_address,
                request.amount,
                "0x" + private_key,
                rpc_url
            )

            from sqlalchemy import update
            await db.execute(
                update(AdminWallet).where(AdminWallet.id == admin_id).values(avax_balance=admin.avax_balance - gas_fee)
            )
            await db.execute(
                update(Wallet).where(Wallet.id == wallet_id).values(balance=wallet.balance - request.amount)
            )
            await db.commit()

            return RelayerSendResponse(
                success=True,
                tx_hash=tx_hash,
                from_address=wallet_address,
                to_address=request.to_address,
                amount=request.amount,
                gas_fee=gas_fee
            )
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Admin] relayer_send error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
