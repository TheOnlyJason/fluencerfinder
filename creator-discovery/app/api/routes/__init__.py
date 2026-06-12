from fastapi import APIRouter

from app.api.routes import accounts, creators, exports, identity, imports, search

api_router = APIRouter()
api_router.include_router(search.router)
api_router.include_router(accounts.router)
api_router.include_router(creators.router)
api_router.include_router(identity.router)
api_router.include_router(imports.router)
api_router.include_router(exports.router)
