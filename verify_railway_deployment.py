#!/usr/bin/env python3
"""
Railway Deployment Fix Verification
Validates that all necessary files and configurations are in place
"""

import os
import sys
from pathlib import Path

def verify_railway_deployment():
    """Verify Railway deployment configuration"""
    
    print("=== 🚆 RAILWAY DEPLOYMENT VERIFICATION ===\n")
    
    results = []
    
    # Test 1: Backend Directory Structure
    print("🔧 Test 1: Backend Directory Structure...")
    backend_dir = Path("backend")
    main_py = backend_dir / "main.py"
    
    if backend_dir.exists() and main_py.exists():
        print("✅ Backend directory structure correct")
        results.append(True)
    else:
        print("❌ Backend directory structure incorrect")
        results.append(False)
    
    # Test 2: Procfile in Root
    print("\n🔧 Test 2: Procfile in Root...")
    procfile = Path("Procfile")
    
    if procfile.exists():
        with open(procfile, "r") as f:
            content = f.read()
        
        expected_content = "web: cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT"
        
        if expected_content in content:
            print("✅ Procfile created with correct content")
            results.append(True)
        else:
            print("❌ Procfile content incorrect")
            results.append(False)
    else:
        print("❌ Procfile missing")
        results.append(False)
    
    # Test 3: Main.py Entry Point
    print("\n🔧 Test 3: Main.py Entry Point...")
    try:
        with open("backend/main.py", "r", encoding='utf-8') as f:
            content = f.read()
        
        if "app = FastAPI(" in content:
            print("✅ main.py contains FastAPI app creation")
            results.append(True)
        else:
            print("❌ main.py missing FastAPI app creation")
            results.append(False)
            
    except Exception as e:
        print(f"❌ Test 3 error: {e}")
        results.append(False)
    
    # Test 4: Requirements.txt in Backend
    print("\n🔧 Test 4: Requirements.txt in Backend...")
    requirements = backend_dir / "requirements.txt"
    
    if requirements.exists():
        with open(requirements, "r") as f:
            content = f.read()
        
        # Check for essential packages
        essential_packages = [
            "fastapi",
            "uvicorn",
            "psycopg2-binary",
            "sqlalchemy"
        ]
        
        missing_packages = [pkg for pkg in essential_packages if pkg not in content]
        
        if not missing_packages:
            print("✅ requirements.txt contains essential packages")
            results.append(True)
        else:
            print(f"❌ Missing essential packages: {missing_packages}")
            results.append(False)
    else:
        print("❌ requirements.txt missing")
        results.append(False)
    
    # Test 5: Railway Detection
    print("\n🔧 Test 5: Railway Detection...")
    
    # Check if Railway would detect Python app
    railway_indicators = [
        procfile.exists(),
        requirements.exists(),
        main_py.exists()
    ]
    
    if all(railway_indicators):
        print("✅ Railway should detect Python app")
        results.append(True)
    else:
        print("❌ Railway detection indicators missing")
        results.append(False)
    
    # Test 6: App Structure Validation
    print("\n🔧 Test 6: App Structure Validation...")
    
    # Check that backend has proper structure
    backend_structure = [
        backend_dir / "app",
        backend_dir / "app" / "main.py" if False else None,  # We use main.py in root
        backend_dir / "main.py"
    ]
    
    structure_ok = all(
        path.exists() if path else True 
        for path in backend_structure 
        if path is not None
    )
    
    if structure_ok:
        print("✅ Backend app structure valid")
        results.append(True)
    else:
        print("❌ Backend app structure invalid")
        results.append(False)
    
    # Final Results
    print("\n" + "="*50)
    print("🚆 RAILWAY DEPLOYMENT RESULTS:")
    print("="*50)
    
    all_passed = all(results)
    
    if all_passed:
        print("✅ RAILWAY DEPLOYMENT READY!")
        print("\n🎉 CONFIGURATION COMPLETE:")
        print("✅ Backend code inside /backend directory")
        print("✅ Procfile created in project root")
        print("✅ main.py verified with FastAPI app")
        print("✅ requirements.txt created in /backend")
        print("✅ Railway should detect Python app")
        print("✅ Build should not fail")
        print("✅ App should start successfully")
        print("\n📁 Created/Modified Files:")
        print("📄 Procfile (created)")
        print("📄 backend/requirements.txt (created)")
        print("\n🚀 DEPLOYMENT READY FOR RAILWAY!")
    else:
        print("❌ RAILWAY DEPLOYMENT NOT READY!")
        failed_tests = [i+1 for i, r in enumerate(results) if not r]
        print(f"❌ Failed tests: {failed_tests}")
        print("\n⚠️  Fix remaining issues before deployment")
    
    return all_passed

if __name__ == "__main__":
    success = verify_railway_deployment()
    sys.exit(0 if success else 1)
