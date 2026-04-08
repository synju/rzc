from eth_account import Account
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import uuid4

from database import engine, User, Wallet, Transaction, AdminWallet, settings
from routers.auth import get_current_user


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

    async with AsyncSession(engine) as db:
        result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
        admin = result.scalar_one_or_none()

        if not admin:
            raise HTTPException(status_code=404, detail="Admin wallet not found")

        import httpx
        rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"

        async with httpx.AsyncClient() as client:
            response = await client.post(rpc_url, json={
                "jsonrpc": "2.0",
                "method": "eth_getBalance",
                "params": [admin.address, "latest"],
                "id": 1
            }, timeout=30.0)
            result_data = response.json()

        balance_hex = result_data.get("result", "0x0")
        avax_balance = int(balance_hex, 16) if balance_hex and len(balance_hex) > 2 else 0

        admin.avax_balance = avax_balance
        await db.commit()

        return {"address": admin.address, "avax_balance": avax_balance}


@router.get("/wallet/rzc-balance")
async def get_admin_rzc_balance(current_user: User = Depends(get_current_user)):
    if not current_user.is_admin:
        raise HTTPException(status_code=403, detail="Admin access required")

    async with AsyncSession(engine) as db:
        result = await db.execute(select(AdminWallet).where(AdminWallet.is_active == True))
        admin = result.scalar_one_or_none()

        if not admin:
            raise HTTPException(status_code=404, detail="Admin wallet not found")

        import httpx
        rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"
        token_address = "0x8583645670154b3bc3f9c48a1864261fd1f26758"

        balance_selector = "0x70a08231"
        address_hex = admin.address[2:].lower().zfill(64)
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

        return {"address": admin.address, "rzc_balance": rzc_balance}


@router.post("/relayer/send", response_model=RelayerSendResponse)
async def relayer_send(request: RelayerSendRequest, current_user: User = Depends(get_current_user)):
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

        rpc_url = "https://avalanche-c-chain-rpc.publicnode.com"
        
        private_key = decrypt_private_key(admin.encrypted_private_key, settings.encryption_key)
        tx_hash, gas_fee = await send_transaction(
            admin.address,
            request.to_address,
            request.amount,
            "0x" + private_key,
            rpc_url
        )

        admin.avax_balance -= gas_fee

        wallet.balance -= request.amount
        await db.commit()

        return RelayerSendResponse(
            success=True,
            tx_hash=tx_hash,
            from_address=wallet.address,
            to_address=request.to_address,
            amount=request.amount,
            gas_fee=gas_fee
        )
