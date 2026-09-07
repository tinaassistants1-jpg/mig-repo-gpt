"""Сборка роутеров. Порядок важен: запасные хендлеры регистрируются последними."""

from aiogram import Router

from bot.handlers import admin, common, errors, lead


def build_router() -> Router:
    """Свежее дерево роутеров. Router нельзя переиспользовать между
    диспетчерами, поэтому каждый модуль отдаёт новый экземпляр."""
    root = Router(name="root")
    root.include_router(errors.build_router())
    root.include_router(common.build_router())
    root.include_router(lead.build_router())
    root.include_router(admin.build_router())
    root.include_router(errors.build_fallback_router())
    return root


__all__ = ["build_router"]
