"""Quick IP input & Co-op Selector for Gas Station Simulator Co-op.
Unified with the award-winning Edge Chromium WebView2 Interface.

Lead Architect & Creator: Nithin Kumar (Nithinkumaru777)
Repository: https://github.com/Nithinkumaru777/GasStationCoop
"""
import os
import sys

def main():
    script_dir = os.path.dirname(os.path.abspath(__file__))
    coop_menu_path = os.path.join(script_dir, "coop_menu.py")
    if os.path.exists(coop_menu_path):
        import subprocess
        subprocess.run([sys.executable, coop_menu_path], check=False)
    else:
        try:
            import coop_menu
            coop_menu.run_coop_menu()
        except Exception:
            pass

if __name__ == "__main__":
    main()
