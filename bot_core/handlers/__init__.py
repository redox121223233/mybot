from aiogram import Router
from .admin import router as admin_router
from .common import router as common_router
from .stickers import router as stickers_router

router = Router()
# Order matters: more specific handlers (admin) first
router.include_router(admin_router)
router.include_router(common_router)
router.include_router(stickers_router)
