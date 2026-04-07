from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import logging
from app.routes import chat, process, auth, manager, customer, public, history
from app.config import settings
from app.db.database import init_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# Initialize SQLite on startup
init_db()

app = FastAPI(
    title="World Bank AI Banking Assistant",
    description="Secure, role-based AI banking assistant with RAG + SQLite hybrid architecture.",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins.split(","),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(auth.router,     prefix="/auth",     tags=["Authentication"])
app.include_router(manager.router,  prefix="/manager",  tags=["Manager"])
app.include_router(process.router,  prefix="/process",  tags=["AI Assistant"])
app.include_router(chat.router,     prefix="/chat",     tags=["Chat"])
app.include_router(customer.router, prefix="/customer", tags=["Customer"])
app.include_router(public.router,   prefix="/public",   tags=["Public"])
app.include_router(history.router,  prefix="/history",  tags=["Chat History"])

@app.get("/")
async def root():
    return {"message": "World Bank AI Banking Assistant API v2.0", "docs": "/docs"}
