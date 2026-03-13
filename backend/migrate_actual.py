#!/usr/bin/env python3
"""
Targeted migration based on actual files found
"""

import os
import shutil
from pathlib import Path

def migrate_actual_files():
    """Migrate actual existing files"""
    
    # Move AI engines to app/ai/
    ai_migrations = [
        ("backend/ai/learning_engine.py", "backend/app/ai/learning_engine.py"),
        ("backend/ai/adaptive_learning_engine.py", "backend/app/ai/adaptive_learning_engine.py"),
        ("backend/ai/trade_decision_engine.py", "backend/app/strategies/trade_decision_engine.py"),
        ("backend/ai/strike_selection_engine.py", "backend/app/strategies/strike_selection_engine.py"),
        ("backend/ai/strategy_planning_engine.py", "backend/app/strategies/strategy_planning_engine.py"),
        ("backend/ai/stoploss_hunt_engine.py", "backend/app/risk/stoploss_hunt_engine.py"),
    ]
    
    # Move services engines to proper locations
    service_migrations = [
        # Analytics
        ("backend/app/services/greeks_engine.py", "backend/app/analytics/greeks_engine.py"),
        ("backend/app/services/gamma_engine.py", "backend/app/analytics/gamma_engine.py"),
        ("backend/app/services/oi_buildup_engine.py", "backend/app/analytics/oi_buildup_engine.py"),
        ("backend/app/services/oi_heatmap_engine.py", "backend/app/analytics/oi_heatmap_engine.py"),
        ("backend/app/services/expected_move_engine.py", "backend/app/analytics/expected_move_engine.py"),
        
        # AI
        ("backend/app/services/ml_training_engine.py", "backend/app/ai/ml_training_engine.py"),
        
        # Strategies
        ("backend/app/services/advanced_strategies_engine.py", "backend/app/strategies/advanced_strategies_engine.py"),
        ("backend/app/services/trade_setup_engine.py", "backend/app/strategies/trade_setup_engine.py"),
        ("backend/app/services/signal_scoring_engine.py", "backend/app/strategies/signal_scoring_engine.py"),
    ]
    
    # Remove consolidated engines
    engines_to_remove = [
        "backend/ai/smart_money_engine.py",
        "backend/ai/regime_engine.py", 
        "backend/ai/risk_engine.py",
        "backend/ai/strategy_engine.py",
        "backend/app/services/market_data/smart_money_engine.py",
        "backend/app/services/market_data/smart_money_engine_v2.py",
        "backend/app/services/regime_confidence_engine.py",
        "backend/app/services/structure_engine.py",
        "backend/app/services/live_structural_engine.py",
        "backend/app/services/ai_signal_engine.py",
        "backend/app/services/ai_outcome_engine.py",
        "backend/app/services/ai_learning_engine.py",
    ]
    
    print("🔄 Migrating AI engines...")
    for source, dest in ai_migrations:
        if os.path.exists(source):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.move(source, dest)
                print(f"✓ Moved: {source} -> {dest}")
            except Exception as e:
                print(f"✗ Error: {e}")
        else:
            print(f"✗ Not found: {source}")
    
    print("\n🔄 Migrating service engines...")
    for source, dest in service_migrations:
        if os.path.exists(source):
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            try:
                shutil.move(source, dest)
                print(f"✓ Moved: {source} -> {dest}")
            except Exception as e:
                print(f"✗ Error: {e}")
        else:
            print(f"✗ Not found: {source}")
    
    print("\n🗑️ Removing consolidated engines...")
    for engine_path in engines_to_remove:
        if os.path.exists(engine_path):
            try:
                os.remove(engine_path)
                print(f"✓ Removed: {engine_path}")
            except Exception as e:
                print(f"✗ Error removing: {e}")
        else:
            print(f"✗ Not found: {engine_path}")
    
    print("\n✅ Migration complete!")

if __name__ == "__main__":
    migrate_actual_files()
