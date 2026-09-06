#!/usr/bin/env python3
"""
State management for Civis bot.
Defines FSM states and helper functions.
"""

from aiogram.fsm.state import State, StatesGroup

class Form(StatesGroup):
    """Survey states"""
    text = State()
    values = State()
    role = State()
    format = State()

class SurveyState:
    """Constants for survey state names"""
    LANGUAGE_SELECT = 'language_select'
    SURVEY_NAME = 'survey_name'
    SURVEY_ABOUT = 'survey_about'
    SURVEY_VALUES = 'survey_values'
    SURVEY_ROLE = 'survey_role'
    SURVEY_FORMAT = 'survey_format'
    OFFER = 'offer'
    REQUEST = 'request'
