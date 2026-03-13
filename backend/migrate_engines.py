#!/usr/bin/env python3
"""
StrikeIQ Engine Migration Script
Moves engines to their new organized structure
"""

import os
import shutil
from pathlib import Path

def migrate_engines():
    """Migrate engines to new structure"""
    
    # Define migrations (source -> destination)
    migrations = [
        # Analytics Layer
        ("backend/app/services/greeks_engine.py", "backend/app/analytics/greeks_engine.py"),
        ("backend/app/services/gamma_engine.py", "backend/app/analytics/gamma_engine.py"),
        ("backend/app/services/oi_engine.py", "backend/app/analytics/oi_engine.py"),
        ("backend/app/services/expected_move_engine.py", "backend/app/analytics/expected_move_engine.py"),
        
        # AI Layer (remaining engines)
        ("backend/ai/learning_engine.py", "backend/app/ai/learning_engine.py"),
        ("backend/ai/adaptive_learning_engine.py", "backend/app/ai/adaptive_learning_engine.py"),
        ("backend/app/services/ml_training_engine.py", "backend/app/ai/ml_training_engine.py"),
        
        # Strategy Layer
        ("backend/ai/trade_decision_engine.py", "backend/app/strategies/trade_decision_engine.py"),
        ("backend/ai/strike_selection_engine.py", "backend/app/strategies/strike_selection_engine.py"),
        ("backend/ai/strategy_planning_engine.py", "backend/app/strategies/strategy_planning_engine.py"),
        
        # Risk Layer (remaining engines)
        ("backend/ai/stoploss_hunt_engine.py", "backend/app/risk/stoploss_hunt_engine.py"),
        ("backend/app/services/position_sizing_engine.py", "backend/app/risk/position_sizing_engine.py"),
    ]
    
    # Create directories
    directories = [
        "backend/app/analytics",
        "backend/app/ai",
        "backend/app/strategies", 
        "backend/app/risk",
        "backend/app/core/market_data",
        "backend/app/core/features",
        "backend/app/core/infrastructure"
    ]
    
    print("Creating directories...")
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✓ Created: {directory}")
    
    print("\nMigrating engines...")
    migrated = 0
    skipped = 0
    
    for source, destination in migrations:
        if os.path.exists(source):
            # Create destination directory if needed
            os.makedirs(os.path.dirname(destination), exist_ok=True)
            
            try:
                shutil.move(source, destination)
                print(f"✓ Moved: {source} -> {destination}")
                migrated += 1
            except Exception as e:
                print(f"✗ Error moving {source}: {e}")
                skipped += 1
        else:
            print(f"✗ Source not found: {source}")
            skipped += 1
    
    print(f"\nMigration complete:")
    print(f"  Migrated: {migrated} files")
    print(f"  Skipped: {skipped} files")
    
    # Remove old engines that are now consolidated
    engines_to_remove = [
        "backend/ai/smart_money_engine.py",  # Consolidated into analytics/institutional_flow_engine.py
        "backend/app/services/market_data/smart_money_engine.py",  # Consolidated
        "backend/app/services/market_data/smart_money_engine_v2.py",  # Consolidated
        "backend/ai/regime_engine.py",  # Consolidated into analytics/regime_engine.py
        "backend/app/services/regime_confidence_engine.py",  # Consolidated
        "backend/app/services/structure_engine.py",  # Consolidated into analytics/structure_engine.py
        "backend/app/services/zone_detection_engine.py",  # Consolidated
        "backend/app/services/wave_engine.py",  # Consolidated
        "backend/app/services/live_structural_engine.py",  # Consolidated
        "backend/app/services/live_analytics_engine.py",  # Old version
        "backend/app/services/ai_signal_engine.py",  # Consolidated into AI orchestrator
        "backend/app/services/ai_outcome_engine.py",  # Consolidated into AI orchestrator
        "backend/app/services/ai_learning_engine.py",  # Consolidated
        "backend/app/services/advanced_strategies_engine.py",  # Consolidated into strategy engine
    ]
    
    print("\nRemoving consolidated engines...")
    removed = 0
    
    for engine_path in engines_to_remove:
        if os.path.exists(engine_path):
            try:
                os.remove(engine_path)
                print(f"✓ Removed: {engine_path}")
                removed += 1
            except Exception as e:
                print(f"✗ Error removing {engine_path}: {e}")
        else:
            print(f"✗ File not found: {engine_path}")
    
    print(f"\nRemoved {removed} consolidated engines")
    
    print("\n✅ Engine migration complete!")
    print("\nNew structure:")
    print("├── backend/app/")
    print("│   ├── analytics/")
    print("│   │   ├── institutional_flow_engine.py (NEW)")
    print("│   │   ├── regime_engine.py (NEW)")
    print("│   │   ├── structure_engine.py (NEW)")
    print("│   │   ├── greeks_engine.py")
    print("│   │   ├── gamma_engine.py")
    print("│   │   ├── oi_engine.py")
    print("│   │   └── expected_move_engine.py")
    print("│   ├── ai/")
    print("│   │   ├── ai_orchestrator.py (NEW)")
    print("│   │   ├── probability_engine.py")
    print("│   │   ├── learning_engine.py")
    print("│   │   ├── adaptive_learning_engine.py")
    print("│   │   └── ml_training_engine.py")
    print("│   ├── strategies/")
    print("│   │   ├── strategy_engine.py (NEW)")
    print("│   │   ├── trade_decision_engine.py")
    print("│   │   ├── strike_selection_engine.py")
    print("│   │   └── strategy_planning_engine.py")
    print("│   ├── risk/")
    print("│   │   ├── risk_engine.py (NEW)")
    print("│   │   ├── stoploss_hunt_engine.py")
    print("│   │   └── position_sizing_engine.py")
    print("│   ├── core/")
    print("│   │   ├── market_data/")
    print("│   │   │   └── market_feed_engine.py (NEW)")
    print("│   │   ├── features/")
    print("│   │   │   └── feature_builder.py (NEW)")
    print("│   │   └── infrastructure/")
    print("│   │       └── analytics_broadcaster.py (NEW)")
    print("│   ├── services/ (remaining services)")
    print("│   └── engines/ (remaining engines)")
    print("└── backend/ai/ (remaining AI engines)")

if __name__ == "__main__":
    migrate_engines()
