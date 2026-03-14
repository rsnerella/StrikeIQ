#!/usr/bin/env python3
"""
Mode Switcher for Upstox WebSocket
Easily switch between subscription modes to test complete options data
"""

import os
import sys

# Available modes
MODES = {
    "1": "ltp",
    "2": "option_greek", 
    "3": "full",
    "4": "full_d30",
    "5": "full_d5",
    "6": "full_d10"
}

DESCRIPTIONS = {
    "ltp": "LTP Only - Fastest updates, minimal data",
    "option_greek": "Options Greeks Only - Delta, theta, gamma, vega, rho",
    "full": "Full Data - LTP, some bid/ask, limited Greeks",
    "full_d30": "Full Market Depth (30 levels) - Complete bid/ask, all Greeks, OI, volume",
    "full_d5": "Full Market Depth (5 levels) - Complete data with 5 depth levels",
    "full_d10": "Full Market Depth (10 levels) - Complete data with 10 depth levels"
}

def switch_mode(mode: str):
    """Switch subscription mode in websocket_market_feed.py"""
    file_path = "app/services/websocket_market_feed.py"
    
    if not os.path.exists(file_path):
        print(f"ERROR: File not found: {file_path}")
        return False
    
    # Read the file
    with open(file_path, 'r') as f:
        content = f.read()
    
    # Find and replace the mode line
    old_line = '                "mode": "full_d30",  # Use full_d30 mode for complete options data with bid/ask/greeks'
    new_line = f'                "mode": "{mode}",  # {DESCRIPTIONS.get(mode, mode)} mode'
    
    if old_line not in content:
        print(f"ERROR: Could not find mode line to replace")
        print(f"Looking for: {old_line}")
        return False
    
    # Replace the line
    content = content.replace(old_line, new_line)
    
    # Write back to file
    with open(file_path, 'w') as f:
        f.write(content)
    
    print(f"✅ Switched to {mode} mode")
    print(f"📝 Description: {DESCRIPTIONS.get(mode, mode)}")
    print(f"🔄 Restart the system to apply changes")
    return True

def main():
    """Main function"""
    print("🔧 Upstox WebSocket Mode Switcher")
    print("=" * 50)
    print("Switch between subscription modes to test complete options data")
    print("=" * 50)
    
    print("\n📋 Available Modes:")
    for num, mode in MODES.items():
        desc = DESCRIPTIONS.get(mode, "")
        print(f"  {num}. {mode:<12} - {desc}")
    
    print("\n🎯 Current Mode: full_d30")
    print("📊 Expected: Complete bid/ask, all Greeks, OI, volume")
    
    if len(sys.argv) > 1:
        mode_num = sys.argv[1]
        if mode_num in MODES:
            mode = MODES[mode_num]
            print(f"🔄 Switching to mode {mode_num}: {mode}")
            if switch_mode(mode):
                print("\n✅ SUCCESS! Mode switched successfully")
                print("🚀 Restart the system with: python main.py")
                print("📊 Monitor logs for complete options data")
            else:
                print("\n❌ FAILED! Could not switch mode")
        else:
            print(f"\n❌ Invalid mode number: {mode_num}")
            print("Choose from available modes above")
    else:
        print(f"\n💡 Usage: python {sys.argv[0]} [mode_number]")
        print(f"Example: python {sys.argv[0]} 4  # Switch to full_d30 mode")
        print(f"Example: python {sys.argv[0]} 5  # Switch to full_d5 mode")
        print(f"Example: python {sys.argv[0]} 6  # Switch to full_d10 mode")

if __name__ == "__main__":
    main()
