
try:
    print("Testing imports...")
    import sys
    import os
    sys.path.append(os.path.join(os.getcwd(), 'backend'))
    from app.ai.ai_orchestrator import ai_orchestrator
    print("Import success!")
except Exception as e:
    print(f"Import failed: {e}")
    import traceback
    traceback.print_exc()
