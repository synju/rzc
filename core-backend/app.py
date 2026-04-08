from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from database import Base, engine, get_db, User, Wallet, settings
from routers import auth, wallet, transactions, recipients, admin
from background_sync import background_sync


@asynccontextmanager
async def lifespan(app: FastAPI):
    await engine.dispose()
    background_sync.start()
    yield
    background_sync.stop()


app = FastAPI(title="RZC Core API", version="1.0.0", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router)
app.include_router(wallet.router)
app.include_router(transactions.router)
app.include_router(recipients.router)
app.include_router(admin.router)


@app.get("/")
async def root():
    return {"message": "RZC Core API", "status": "running"}


@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=settings.port, reload=False)
