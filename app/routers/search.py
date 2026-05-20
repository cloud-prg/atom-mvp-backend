from fastapi import APIRouter, Depends

from app.deps import get_current_user
from app.models import User
from app.schemas import SearchIn, SearchOut, SearchResultOut
from app.services.search_provider import search

router = APIRouter(prefix="/search", tags=["search"])


@router.post("", response_model=SearchOut)
async def search_route(payload: SearchIn, _user: User = Depends(get_current_user)) -> SearchOut:
    provider, status, results = await search(payload.query, payload.mode)
    return SearchOut(
        provider=provider,
        status=status,
        results=[SearchResultOut(**result.__dict__) for result in results],
    )

