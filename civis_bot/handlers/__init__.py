#!/usr/bin/env python3
"""
Handlers module for Civis bot.
Exports all command handlers and the set_bot function.
"""

from .commands import register_handlers, set_bot

__all__ = ['register_handlers', 'set_bot']
