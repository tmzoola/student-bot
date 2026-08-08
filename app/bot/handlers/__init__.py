"""Malaka bot handler'lari (feature-per-file)."""
from bot.handlers.referral_admin_events import router as referral_admin_events_router
from bot.handlers.referral_chat_member import router as referral_chat_member_router
from bot.handlers.referral_event import router as referral_event_router
from bot.handlers.referral_inline import router as referral_inline_router
from bot.handlers.referral_join_request import router as referral_join_request_router
from bot.handlers.referral_menu import router as referral_menu_router

__all__ = [
    "referral_admin_events_router",
    "referral_chat_member_router",
    "referral_event_router",
    "referral_inline_router",
    "referral_join_request_router",
    "referral_menu_router",
]
