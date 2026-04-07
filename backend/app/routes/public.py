"""
Public Route
-------------
The /public/chat endpoint has been removed.
Public (unauthenticated) chat now goes through POST /process directly.
/process accepts optional JWT — guests get RAG-only answers; logged-in customers
also receive their personal account data.
"""
from fastapi import APIRouter

router = APIRouter()
