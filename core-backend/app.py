import logging
import traceback
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from database import Base, engine, get_db, User, Wallet, settings
from routers import auth, wallet, transactions, recipients, admin
from background_sync import background_sync

ERROR_LOG = "error.log"


def log_error(msg: str):
    with open(ERROR_LOG, "a") as f:
        f.write(f"{msg}\n")
        f.write(traceback.format_exc())
        f.write("\n")


@asynccontextmanager
async def lifespan(app: FastAPI):
    with open(ERROR_LOG, "w") as f:
        f.write("")
    await engine.dispose()
    background_sync.start()
    yield
    background_sync.stop()


app = FastAPI(title="RZC Core API", version="1.0.0", lifespan=lifespan)


@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    log_error(f"[Unhandled] {request.method} {request.url.path}")
    return JSONResponse(status_code=500, content={"detail": str(exc)})


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
