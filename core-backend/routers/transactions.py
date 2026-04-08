import traceback
from uuid import uuid4
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database import engine, User, Wallet, Transaction, AdminWallet, settings
from routers.auth import get_current_user
from routers.wallet import decrypt_private_key

ERROR_LOG = "error.log"


def log_error(msg: str):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{msg}\n")
        f.write(traceback.format_exc())
        f.write("\n")


router = APIRouter(prefix="/transactions", tags=["transactions"])


class TransferRequest(BaseModel):
    to_address: str
    amount: int


class TransferResponse(BaseModel):
    success: bool
    tx_hash: str | None
    from_address: str
    to_address: str
    amount: int
    type: str


class InternalTransferRequest(BaseModel):
    to_wallet_id: str
    amount: int


async def send_transaction(from_address: str, to_address: str, amount: int, private_key: str) -> str:
    from httpx import AsyncClient

    rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"
    chain_id = 43114

    nonce_data = {
        "jsonrpc": "2.0",
        "method": "eth_getTransactionCount",
        "params": [from_address, "pending"],
        "id": 1
    }

    async with AsyncClient() as client:
        nonce_response = await client.post(rpc_url, json=nonce_data)
        nonce_result = nonce_response.json()
        nonce = int(nonce_result["result"][2:], 16) if nonce_result.get("result", "").startswith("0x") else 0

    gas_data = {
        "jsonrpc": "2.0",
        "method": "eth_gasPrice",
        "params": [],
        "id": 1
    }

    async with AsyncClient() as client:
        gas_response = await client.post(rpc_url, json=gas_data)
        gas_result = gas_response.json()
        gas_price = int(gas_result["result"][2:], 16) if gas_result.get("result", "").startswith("0x") else 25000000000

    to_address_normalized = to_address.lower().replace("0x", "")
    amount_hex = hex(amount)[2:].zfill(64)

    selector = "0xa9059cbb"
    padded_to = to_address_normalized.zfill(64)
    data = selector + padded_to + amount_hex

    gas_limit = 70000

    tx = {
        "from": from_address,
        "to": "0x8583645670154b3bc3f9c48a1864261fd1f26758",
        "nonce": hex(nonce),
        "gasPrice": hex(gas_price),
        "gasLimit": hex(gas_limit),
        "value": "0x0",
        "data": "0x" + data,
        "chainId": chain_id
    }

    from eth_account import Account
    signed_tx = Account.sign_transaction(tx, private_key)

    async with AsyncClient() as client:
        send_data = {
            "jsonrpc": "2.0",
            "method": "eth_sendRawTransaction",
            "params": ["0x" + signed_tx.rawTransaction.hex()],
            "id": 1
        }
        send_response = await client.post(rpc_url, json=send_data)
        send_result = send_response.json()

    if "result" in send_result:
        return send_result["result"]
    else:
        raise Exception(send_result.get("error", {}).get("message", "Unknown error"))


async def send_transaction_relayer(from_address: str, to_address: str, amount: int, private_key: str, rpc_url: str) -> tuple[str, int]:
    import httpx
    from eth_account import Account

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


@router.post("/send", response_model=TransferResponse)
async def send_rzc(
    request: TransferRequest,
    current_user: User = Depends(get_current_user)
):
    try:
        async with AsyncSession(engine) as db:
            admin_result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
            admin = admin_result.scalar_one_or_none()

            if not admin:
                raise HTTPException(status_code=404, detail="Relayer not available")

            if admin.avax_balance < 50000000000000000:
                raise HTTPException(status_code=400, detail="Insufficient AVAX in relayer for gas")

            wallet_result = await db.execute(
                select(Wallet).where(Wallet.user_id == current_user.id, Wallet.is_active == True)
            )
            wallet = wallet_result.scalar_one_or_none()

            if wallet is None or not wallet.address:
                raise HTTPException(status_code=404, detail="Wallet not found")

            if wallet.balance < request.amount:
                raise HTTPException(status_code=400, detail="Insufficient balance")

            if len(request.to_address) != 42 or not request.to_address.startswith("0x"):
                raise HTTPException(status_code=400, detail="Invalid recipient address")

            recipient_result = await db.execute(
                select(Wallet).where(Wallet.address == request.to_address)
            )
            recipient_wallet = recipient_result.scalar_one_or_none()

            if recipient_wallet and recipient_wallet.user_id == current_user.id:
                raise HTTPException(status_code=400, detail="Use internal-transfer for sending to your own wallets")

            admin_address = admin.address
            admin_id = admin.id
            wallet_id = wallet.id
            wallet_address = wallet.address
            admin_encrypted_pk = admin.encrypted_private_key

            rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"
            private_key = decrypt_private_key(admin_encrypted_pk, settings.encryption_key)
            tx_hash, gas_fee = await send_transaction_relayer(
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

            tx_record = Transaction(
                wallet_id=wallet_id,
                tx_hash=tx_hash,
                type="sent",
                from_address=wallet_address,
                to_address=request.to_address,
                amount=request.amount,
                status="confirmed"
            )
            db.add(tx_record)

            await db.commit()

            return TransferResponse(
                success=True,
                tx_hash=tx_hash,
                from_address=wallet_address,
                to_address=request.to_address,
                amount=request.amount,
                type="sent"
            )
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Transactions] send_rzc error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/internal-transfer", response_model=TransferResponse)
async def internal_transfer(
    request: InternalTransferRequest,
    current_user: User = Depends(get_current_user)
):
    async with AsyncSession(engine) as db:
        from_wallet_result = await db.execute(
            select(Wallet).where(Wallet.user_id == current_user.id, Wallet.is_active == True)
        )
        from_wallet = from_wallet_result.scalar_one_or_none()

        if from_wallet is None or not from_wallet.address:
            raise HTTPException(status_code=404, detail="Active wallet not found")

        if from_wallet.balance < request.amount:
            raise HTTPException(status_code=400, detail="Insufficient balance")

        to_wallet_result = await db.execute(
            select(Wallet).where(Wallet.id == request.to_wallet_id, Wallet.user_id == current_user.id)
        )
        to_wallet = to_wallet_result.scalar_one_or_none()

        if to_wallet is None or not to_wallet.address:
            raise HTTPException(status_code=404, detail="Recipient wallet not found")

        if from_wallet.id == to_wallet.id:
            raise HTTPException(status_code=400, detail="Cannot transfer to the same wallet")

        from_address = from_wallet.address
        to_address = to_wallet.address
        amount = request.amount

        from_wallet.balance -= amount
        to_wallet.balance += amount

        internal_id = str(uuid4())
        tx_record = Transaction(
            wallet_id=from_wallet.id,
            tx_hash=f"internal-{internal_id}",
            type="sent",
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            status="confirmed"
        )
        db.add(tx_record)

        tx_record_received = Transaction(
            wallet_id=to_wallet.id,
            tx_hash=f"internal-{internal_id}",
            type="received",
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            status="confirmed"
        )
        db.add(tx_record_received)

        await db.commit()

        return TransferResponse(
            success=True,
            tx_hash=None,
            from_address=from_address,
            to_address=to_address,
            amount=amount,
            type="internal"
        )


@router.get("/history")
async def get_history(current_user: User = Depends(get_current_user)):
    async with AsyncSession(engine) as db:
        result = await db.execute(
            select(Wallet).where(Wallet.user_id == current_user.id, Wallet.is_active == True)
        )
        wallet = result.scalar_one_or_none()

        if wallet is None:
            raise HTTPException(status_code=404, detail="Wallet not found")

        tx_result = await db.execute(
            select(Transaction)
            .where(Transaction.wallet_id == wallet.id)
            .order_by(Transaction.created_at.desc())
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
                "to_address": tx.to_address
            })

        return {"address": wallet.address, "transactions": transactions}


@router.post("/sync-transactions")
async def sync_transactions(current_user: User = Depends(get_current_user)):
    try:
        async with AsyncSession(engine) as db:
            result = await db.execute(
                select(Wallet).where(Wallet.user_id == current_user.id, Wallet.is_active == True)
            )
            wallet = result.scalar_one_or_none()

            if wallet is None or not wallet.address:
                raise HTTPException(status_code=404, detail="Wallet not found")

            wallet_id = wallet.id
            wallet_address = wallet.address

            from httpx import AsyncClient
            rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"

            async with AsyncClient() as client:
                block_response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_blockNumber",
                    "params": [],
                    "id": 1
                })
                current_block = int(block_response.json()["result"], 16)
                from_block = max(0, current_block - 1000)

                response = await client.post(rpc_url, json={
                    "jsonrpc": "2.0",
                    "method": "eth_getLogs",
                    "params": [{
                        "fromBlock": hex(from_block),
                        "toBlock": hex(current_block),
                        "address": "0x8583645670154b3bc3f9c48a1864261fd1f26758",
                        "topics": [
                            "0xddf252ad1be2c89b69c2b068fc378daa952ba7f163c4a11628f55a4df523b3ef",
                            None,
                            "0x" + wallet_address.lower().replace("0x", "").zfill(64)
                        ]
                    }],
                    "id": 1
                })

            result_data = response.json()
            logs = result_data.get("result", [])

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

                tx_record = Transaction(
                    wallet_id=wallet_id,
                    tx_hash=tx_hash,
                    type="received",
                    from_address=from_address,
                    to_address=to_address,
                    amount=amount,
                    block_number=block_number,
                    status="confirmed"
                )
                db.add(tx_record)
                new_tx_count += 1

            await db.commit()

            return {"message": f"Synced {new_tx_count} new transactions"}
    except HTTPException:
        raise
    except Exception as e:
        log_error(f"[Transactions] sync_transactions error: {e}")
        raise HTTPException(status_code=500, detail=str(e))
