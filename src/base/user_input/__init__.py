from aiogram import Router
from base.user_input.add_new_market_item import router as add_new_market_item_router


__all__ = ["router"]
router = Router()

router.include_routers(add_new_market_item_router)
