# Windows async event loop fix for psycopg compatibility
import sys
import asyncio
if sys.platform.startswith("win"):
    asyncio.set_event_loop_policy(
        asyncio.WindowsSelectorEventLoopPolicy()
    )

# Make ai folder a Python package
from .ai_db import ai_db
from .prediction_service import prediction_service
from .outcome_checker import outcome_checker
from .experience_updater import experience_updater
from .experience_service import experience_service
from .scheduler import ai_scheduler
from .formula_integrator import formula_integrator, store_formula_signal

__all__ = [
    'ai_db',
    'prediction_service', 
    'outcome_checker',
    'experience_updater',
    'experience_service',
    'ai_scheduler',
    'formula_integrator',
    'store_formula_signal'
]
