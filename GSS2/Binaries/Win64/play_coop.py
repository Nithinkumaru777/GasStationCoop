"""Award-Winning, Next-Gen Co-op Launcher for Gas Station Simulator.
Built with Edge Chromium Webview2, Ultra-Smooth Async Engine, High-Contrast Cyber Aesthetic,
Interactive 3D Character Selector, Continuous Multi-Subnet Auto-Discovery & Zero-Freeze Win32 Clipboard.

Lead Architect & Creator: Nithin Kumar (Nithinkumaru777)
Repository: https://github.com/Nithinkumaru777/GasStationCoop
"""

import os
import sys
import socket
import subprocess
import ctypes
from ctypes import wintypes
import webbrowser
import threading
import time
import webview

CREATE_NO_WINDOW = 0x08000000

# -------------------------------------------------------------
# Pure Win32 Zero-Latency Clipboard (Non-blocking fallback)
# -------------------------------------------------------------
user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
CF_UNICODETEXT = 13

kernel32.GlobalAlloc.restype = ctypes.c_void_p
kernel32.GlobalAlloc.argtypes = [wintypes.UINT, ctypes.c_size_t]
kernel32.GlobalLock.restype = ctypes.c_void_p
kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
user32.GetClipboardData.restype = ctypes.c_void_p
user32.GetClipboardData.argtypes = [wintypes.UINT]
user32.SetClipboardData.restype = ctypes.c_void_p
user32.SetClipboardData.argtypes = [wintypes.UINT, ctypes.c_void_p]

def win32_get_clipboard_text():
    if not user32.OpenClipboard(None):
        return ""
    try:
        h = user32.GetClipboardData(CF_UNICODETEXT)
        if not h:
            return ""
        p = kernel32.GlobalLock(h)
        if not p:
            return ""
        val = ctypes.c_wchar_p(p).value
        kernel32.GlobalUnlock(h)
        return val or ""
    finally:
        user32.CloseClipboard()

def win32_set_clipboard_text(text):
    if not user32.OpenClipboard(None):
        return False
    try:
        user32.EmptyClipboard()
        data = (text + "\0").encode("utf-16le")
        h = kernel32.GlobalAlloc(0x0042, len(data))
        p = kernel32.GlobalLock(h)
        ctypes.memmove(p, data, len(data))
        kernel32.GlobalUnlock(h)
        user32.SetClipboardData(CF_UNICODETEXT, h)
        return True
    finally:
        user32.CloseClipboard()

def get_screen_metrics():
    try:
        user32.SetProcessDPIAware()
        w = user32.GetSystemMetrics(0)
        h = user32.GetSystemMetrics(1)
        if w > 0 and h > 0:
            return w, h
    except Exception:
        pass
    return 2560, 1600

# -------------------------------------------------------------
# Background Multi-Subnet Continuous Auto-Discovery (0ms UI latency)
# -------------------------------------------------------------
CACHED_IPS = ["127.0.0.1"]
DISCOVERED_HOST = {"found": False, "ip": "", "name": ""}

def get_broadcast_targets(port=7777):
    targets = [("<broadcast>", port), ("255.255.255.255", port), ("127.0.0.1", port)]
    for ip in CACHED_IPS:
        parts = ip.split(".")
        if len(parts) == 4 and not ip.startswith("127."):
            targets.append((f"{parts[0]}.{parts[1]}.{parts[2]}.255", port))
    return list(set(targets))

def _continuous_discovery_worker():
    global CACHED_IPS, DISCOVERED_HOST
    # 1. Resolve network IPs
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith("127."):
            CACHED_IPS = [primary]
    except Exception:
        pass

    try:
        out = subprocess.check_output("ipconfig", text=True, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        for line in out.splitlines():
            if "IPv4" in line:
                val = line.split(":")[-1].strip()
                if val and val not in CACHED_IPS and not val.startswith("127."):
                    CACHED_IPS.append(val)
    except Exception:
        pass

    # 2. Continuous scanning loop (every 1.5s)
    last_found_time = 0
    while True:
        try:
            ds = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            ds.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
            ds.settimeout(0.5)

            for bcast_ip, bcast_port in get_broadcast_targets(7777):
                try:
                    ds.sendto(b"GSS_DISCOVER", (bcast_ip, bcast_port))
                except Exception:
                    pass

            start_t = time.time()
            found_this_cycle = False
            while time.time() - start_t < 0.5:
                try:
                    data, addr = ds.recvfrom(1024)
                    text = data.decode("utf-8", errors="replace")
                    if text.startswith("GSS_OFFER:") or text.startswith("GSS_BEACON:"):
                        parts = text.split(":", 2)
                        name = parts[2] if len(parts) >= 3 else "Friend's Station"
                        DISCOVERED_HOST = {"found": True, "ip": addr[0], "name": name}
                        last_found_time = time.time()
                        found_this_cycle = True
                        break
                except socket.timeout:
                    break
                except Exception:
                    pass
            ds.close()

            if not found_this_cycle and (time.time() - last_found_time > 6.0):
                DISCOVERED_HOST = {"found": False, "ip": "", "name": ""}

        except Exception:
            pass

        time.sleep(1.5)

threading.Thread(target=_continuous_discovery_worker, daemon=True).start()

def find_game_directory():
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(cur_dir, "GSS2-Win64-Shipping.exe")):
        return cur_dir
    sub = os.path.join(cur_dir, "GSS2", "Binaries", "Win64")
    if os.path.exists(os.path.join(sub, "GSS2-Win64-Shipping.exe")):
        return sub
    for p in [r"D:\coop-sandbox\gss\A\GSS2\Binaries\Win64", r"D:\coop-sandbox\gss\B\GSS2\Binaries\Win64"]:
        if os.path.exists(os.path.join(p, "GSS2-Win64-Shipping.exe")):
            return p
    for d in ["C", "D", "E", "F", "G", "H"]:
        for pat in [
            r"{}:\SteamLibrary\steamapps\common\Gas Station Simulator\GSS2\Binaries\Win64",
            r"{}:\Program Files (x86)\Steam\steamapps\common\Gas Station Simulator\GSS2\Binaries\Win64",
            r"{}:\Steam\steamapps\common\Gas Station Simulator\GSS2\Binaries\Win64"
        ]:
            cand = pat.format(d)
            if os.path.exists(os.path.join(cand, "GSS2-Win64-Shipping.exe")):
                return cand
    return cur_dir

def ensure_starter_saves(game_dir):
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    src_saves = os.path.join(cur_dir, "SaveGames")
    if not os.path.exists(src_saves):
        alt = os.path.join(game_dir, "SaveGames")
        if os.path.exists(alt):
            src_saves = alt

    target_dirs = []
    appdata = os.getenv("LOCALAPPDATA")
    if appdata:
        target_dirs.append(os.path.join(appdata, "GSS2", "Saved", "SaveGames"))
    target_dirs.append(os.path.join(game_dir, "GSS2", "Saved", "SaveGames"))

    if "coop-sandbox" in game_dir:
        target_dirs.append(r"D:\coop-sandbox\gss\userA\Saved__coopA\SaveGames")
        target_dirs.append(r"D:\coop-sandbox\gss\userB\Saved__coopB\SaveGames")

    if os.path.exists(src_saves):
        import shutil
        for tdir in target_dirs:
            try:
                os.makedirs(tdir, exist_ok=True)
                for sav_file in os.listdir(src_saves):
                    if sav_file.endswith(".sav"):
                        src_f = os.path.join(src_saves, sav_file)
                        dst_f = os.path.join(tdir, sav_file)
                        if not os.path.exists(dst_f):
                            shutil.copy2(src_f, dst_f)
            except Exception:
                pass

def launch_game_process(role, target_ip="127.0.0.1", character="biker", player_name="Nithin"):
    game_dir = find_game_directory()
    exe_path = os.path.join(game_dir, "GSS2-Win64-Shipping.exe")
    scr_w, scr_h = get_screen_metrics()
    ensure_starter_saves(game_dir)

    def safe_write_all(filenames, content):
        for fname in filenames:
            for base in [game_dir, os.path.join(game_dir, "net"), os.path.join(game_dir, "Mods", "GasStationCoop")]:
                target = os.path.join(base, fname)
                try:
                    d = os.path.dirname(target)
                    if d:
                        os.makedirs(d, exist_ok=True)
                    with open(target, "w", encoding="utf-8") as f:
                        f.write(content + "\n")
                except Exception:
                    pass

    safe_write_all(["role.txt"], role)
    safe_write_all(["character.txt"], character)
    safe_write_all(["player_name.txt"], player_name)

    if role == "guest":
        safe_write_all(["host_ip.txt"], target_ip)

    relay_script = os.path.join(game_dir, "gss_relay.py")
    if not os.path.exists(relay_script):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        alt_relay = os.path.join(cur_dir, "gss_relay.py")
        if os.path.exists(alt_relay):
            import shutil
            shutil.copy2(alt_relay, relay_script)

    if os.path.exists(relay_script):
        cmd = ["pythonw", relay_script]
        if role == "host":
            cmd.extend(["--mode", "host", "--netdir", os.path.join(game_dir, "net")])
        else:
            cmd.extend(["--mode", "client", "--connect", target_ip, "--netdir", os.path.join(game_dir, "net")])
        subprocess.Popen(cmd, cwd=game_dir, creationflags=CREATE_NO_WINDOW)

    args = [
        exe_path,
        "-borderless",
        f"-ResX={scr_w}",
        f"-ResY={scr_h}",
        "-nosplash",
    ]
    if "coop-sandbox" in game_dir and "\\A\\" in game_dir:
        args.extend(["-saveddirsuffix=_coopA", '-userdir="D:\\coop-sandbox\\gss\\userA"'])
    elif "coop-sandbox" in game_dir and "\\B\\" in game_dir:
        args.extend(["-saveddirsuffix=_coopB", '-userdir="D:\\coop-sandbox\\gss\\userB"'])

    subprocess.Popen(args, cwd=game_dir, creationflags=CREATE_NO_WINDOW)


class LauncherApi:
    def __init__(self, window=None):
        self.window = window

    def set_window(self, win):
        self.window = win

    def get_network_info(self):
        return {
            "primary_ip": CACHED_IPS[0] if CACHED_IPS else "127.0.0.1",
            "all_ips": CACHED_IPS
        }

    def check_for_host(self):
        return DISCOVERED_HOST

    def copy_to_clipboard(self, text):
        return win32_set_clipboard_text(text)

    def read_clipboard(self):
        return win32_get_clipboard_text()

    def host_world(self, character="biker", player_name="Nithin"):
        primary = CACHED_IPS[0] if CACHED_IPS else "127.0.0.1"
        win32_set_clipboard_text(primary)

        def do_launch():
            time.sleep(0.8)
            launch_game_process("host", target_ip="127.0.0.1", character=character, player_name=player_name)
            time.sleep(1.2)
            if self.window:
                self.window.destroy()

        threading.Thread(target=do_launch, daemon=True).start()
        return {"status": "ok", "ip": primary}

    def join_world(self, target_ip, character="delivery", player_name="Player 2"):
        clean_ip = (target_ip or "").strip()
        if not clean_ip:
            clean_ip = "127.0.0.1"

        def do_launch():
            time.sleep(0.8)
            launch_game_process("guest", target_ip=clean_ip, character=character, player_name=player_name)
            time.sleep(1.2)
            if self.window:
                self.window.destroy()

        threading.Thread(target=do_launch, daemon=True).start()
        return {"status": "ok", "connecting_to": clean_ip}

    def open_github(self):
        try:
            webbrowser.open("https://github.com/Nithinkumaru777/GasStationCoop")
            return True
        except Exception:
            return False


HTML_UI = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Gas Station Simulator Co-op Launcher</title>
<style>
  :root {
    --bg-base: #060911;
    --card-surface: rgba(15, 23, 42, 0.78);
    --card-border: rgba(255, 255, 255, 0.09);
    --card-hover-border: rgba(255, 255, 255, 0.22);
    --amber-neon: #f59e0b;
    --amber-glow: rgba(245, 158, 11, 0.45);
    --cyan-neon: #06b6d4;
    --cyan-glow: rgba(6, 182, 212, 0.4);
    --emerald-neon: #10b981;
    --emerald-glow: rgba(16, 185, 129, 0.45);
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
    --text-accent: #38bdf8;
  }

  * {
    margin: 0; padding: 0; box-sizing: border-box;
  }

  body {
    background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #090d18 50%, #04060a 100%);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--text-primary);
    min-height: 100vh;
    overflow-y: auto;
    overflow-x: hidden;
    display: flex;
    flex-direction: column;
    padding: 20px 22px 20px 22px;
    position: relative;
    user-select: none;
    -webkit-user-select: none;
  }

  ::-webkit-scrollbar { width: 5px; }
  ::-webkit-scrollbar-track { background: rgba(0, 0, 0, 0.2); }
  ::-webkit-scrollbar-thumb { background: rgba(255, 255, 255, 0.2); border-radius: 4px; }
  ::-webkit-scrollbar-thumb:hover { background: rgba(255, 255, 255, 0.4); }

  .glow-orb-1 {
    position: absolute; width: 320px; height: 320px;
    background: radial-gradient(circle, var(--amber-glow) 0%, transparent 70%);
    top: -100px; right: -80px; filter: blur(60px); opacity: 0.5;
    pointer-events: none; animation: floatOrb 8s infinite alternate ease-in-out;
  }
  .glow-orb-2 {
    position: absolute; width: 340px; height: 340px;
    background: radial-gradient(circle, var(--cyan-glow) 0%, transparent 70%);
    bottom: -90px; left: -90px; filter: blur(65px); opacity: 0.45;
    pointer-events: none; animation: floatOrb 9s infinite alternate-reverse ease-in-out;
  }
  @keyframes floatOrb {
    0% { transform: translateY(0) scale(1); }
    100% { transform: translateY(25px) scale(1.12); }
  }

  .hero-header {
    text-align: center;
    position: relative;
    z-index: 2;
    margin-bottom: 12px;
  }

  .route66-badge-container {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    margin-bottom: 6px;
    position: relative;
  }

  .shield-outer {
    width: 52px; height: 52px;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 2px solid var(--amber-neon);
    border-radius: 16px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 25px var(--amber-glow), inset 0 1px 1px rgba(255, 255, 255, 0.3);
  }

  .shield-inner {
    font-size: 24px;
  }

  h1.main-title {
    font-size: 22px;
    font-weight: 800;
    letter-spacing: 1.5px;
    background: linear-gradient(180deg, #ffffff 0%, #cbd5e1 100%);
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    text-shadow: 0 4px 20px rgba(0,0,0,0.6);
    margin-bottom: 3px;
  }

  .sub-tagline {
    font-size: 10px;
    font-weight: 700;
    letter-spacing: 2.2px;
    text-transform: uppercase;
    color: var(--amber-neon);
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    margin-bottom: 10px;
  }

  .sub-tagline::before, .sub-tagline::after {
    content: "";
    width: 26px; height: 1.5px;
    background: linear-gradient(90deg, transparent, var(--amber-neon), transparent);
  }

  /* Creator Credit Banner */
  .creator-banner {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(30, 41, 59, 0.65);
    border: 1px solid var(--card-border);
    backdrop-filter: blur(12px);
    border-radius: 12px;
    padding: 8px 14px;
    margin-bottom: 14px;
    box-shadow: 0 4px 15px rgba(0, 0, 0, 0.3);
  }

  .creator-left {
    display: flex;
    align-items: center;
    gap: 9px;
  }

  .creator-avatar {
    width: 30px; height: 30px;
    border-radius: 50%;
    background: linear-gradient(135deg, #f59e0b, #ef4444);
    display: flex; align-items: center; justify-content: center;
    font-weight: 800; font-size: 11px; color: #fff;
    box-shadow: 0 0 10px var(--amber-glow);
  }

  .creator-info h4 {
    font-size: 11px;
    font-weight: 700;
    color: #f1f5f9;
  }

  .creator-info p {
    font-size: 9.5px;
    color: var(--amber-neon);
    font-weight: 600;
  }

  .github-btn {
    display: inline-flex;
    align-items: center;
    gap: 5px;
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.16);
    color: #f8fafc;
    padding: 5px 11px;
    border-radius: 7px;
    font-size: 10px;
    font-weight: 600;
    cursor: pointer;
    text-decoration: none;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .github-btn:hover {
    background: rgba(255, 255, 255, 0.18);
    border-color: #fff;
    transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(255,255,255,0.15);
  }

  /* Player Name & Character Selector Section */
  .section-title {
    font-size: 10.5px;
    font-weight: 700;
    letter-spacing: 1.5px;
    text-transform: uppercase;
    color: #cbd5e1;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }

  .player-name-row {
    margin-bottom: 12px;
  }

  .player-name-input {
    width: 100%;
    background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 9px;
    padding: 9px 13px;
    color: #fff;
    font-size: 12px;
    font-weight: 600;
    outline: none;
    transition: all 0.2s;
  }

  .player-name-input:focus {
    border-color: var(--cyan-neon);
    box-shadow: 0 0 15px var(--cyan-glow);
  }

  /* 4 Character Cards */
  .char-grid {
    display: grid;
    grid-template-columns: repeat(4, 1fr);
    gap: 8px;
    margin-bottom: 14px;
  }

  .char-card {
    background: rgba(15, 23, 42, 0.7);
    border: 1px solid var(--card-border);
    border-radius: 10px;
    padding: 9px 6px;
    text-align: center;
    cursor: pointer;
    transition: all 0.22s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
  }

  .char-card:hover {
    border-color: rgba(255, 255, 255, 0.3);
    transform: translateY(-2px);
  }

  .char-card.selected {
    border-color: var(--amber-neon);
    background: rgba(245, 158, 11, 0.12);
    box-shadow: 0 0 16px var(--amber-glow);
  }

  .char-icon {
    font-size: 22px;
    margin-bottom: 4px;
  }

  .char-name {
    font-size: 10px;
    font-weight: 700;
    color: #f8fafc;
    line-height: 1.2;
  }

  .char-role {
    font-size: 8px;
    color: var(--text-secondary);
    margin-top: 2px;
  }

  /* Host & Join Main Cards */
  .mode-cards {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 14px;
  }

  .mode-card {
    background: var(--card-surface);
    border: 1px solid var(--card-border);
    border-radius: 14px;
    padding: 14px 16px;
    backdrop-filter: blur(16px);
    transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    position: relative;
    overflow: hidden;
  }

  .mode-card:hover {
    border-color: var(--card-hover-border);
    box-shadow: 0 8px 30px rgba(0, 0, 0, 0.45);
    transform: translateY(-2px);
  }

  .card-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }

  .mode-pill {
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
    text-transform: uppercase;
    padding: 3px 8px;
    border-radius: 20px;
    display: inline-flex;
    align-items: center;
    gap: 5px;
  }

  .pill-host {
    background: rgba(245, 158, 11, 0.15);
    color: var(--amber-neon);
    border: 1px solid rgba(245, 158, 11, 0.35);
  }

  .pill-join {
    background: rgba(6, 182, 212, 0.15);
    color: var(--cyan-neon);
    border: 1px solid rgba(6, 182, 212, 0.35);
  }

  .mode-title {
    font-size: 16px;
    font-weight: 800;
    color: #fff;
    margin-bottom: 4px;
  }

  .mode-desc {
    font-size: 11px;
    color: var(--text-secondary);
    line-height: 1.4;
    margin-bottom: 10px;
  }

  .action-btn {
    width: 100%;
    padding: 11px 18px;
    border-radius: 9px;
    font-size: 12.5px;
    font-weight: 700;
    letter-spacing: 0.5px;
    cursor: pointer;
    border: none;
    outline: none;
    display: flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .btn-host {
    background: linear-gradient(135deg, #f59e0b 0%, #d97706 100%);
    color: #000;
    box-shadow: 0 4px 18px var(--amber-glow);
  }

  .btn-host:hover {
    box-shadow: 0 6px 25px rgba(245, 158, 11, 0.7);
    transform: translateY(-1px);
    filter: brightness(1.1);
  }

  .btn-join {
    background: linear-gradient(135deg, #06b6d4 0%, #0284c7 100%);
    color: #fff;
    box-shadow: 0 4px 18px var(--cyan-glow);
  }

  .btn-join:hover {
    box-shadow: 0 6px 25px rgba(6, 182, 212, 0.7);
    transform: translateY(-1px);
    filter: brightness(1.1);
  }

  .ip-input-container {
    display: flex;
    gap: 8px;
    margin-bottom: 9px;
  }

  .ip-input {
    flex: 1;
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.16);
    border-radius: 8px;
    padding: 10px 14px;
    color: #fff;
    font-size: 13px;
    font-family: monospace;
    font-weight: 600;
    outline: none;
    transition: all 0.2s;
  }

  .ip-input:focus {
    border-color: var(--cyan-neon);
    box-shadow: 0 0 15px var(--cyan-glow);
  }

  .paste-btn {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.18);
    color: #fff;
    border-radius: 8px;
    padding: 0 14px;
    font-size: 11px;
    font-weight: 700;
    cursor: pointer;
    transition: all 0.2s;
    display: flex; align-items: center; gap: 4px;
  }

  .paste-btn:hover {
    background: rgba(255, 255, 255, 0.2);
    border-color: #fff;
  }

  /* Live Auto-Discovery Scanning Banner */
  .discovery-status-bar {
    display: flex;
    align-items: center;
    justify-content: space-between;
    background: rgba(15, 23, 42, 0.6);
    border: 1px solid rgba(255, 255, 255, 0.08);
    border-radius: 8px;
    padding: 6px 10px;
    margin-bottom: 8px;
    font-size: 10px;
    color: var(--text-secondary);
  }

  .live-dot {
    width: 7px; height: 7px;
    background: #10b981;
    border-radius: 50%;
    display: inline-block;
    box-shadow: 0 0 8px #10b981;
    animation: pulseDot 1.4s infinite alternate;
  }
  @keyframes pulseDot {
    0% { transform: scale(0.85); opacity: 0.6; }
    100% { transform: scale(1.2); opacity: 1; }
  }

  .discovered-banner {
    display: none;
    align-items: center;
    justify-content: space-between;
    background: rgba(16, 185, 129, 0.18);
    border: 1px solid rgba(16, 185, 129, 0.5);
    border-radius: 9px;
    padding: 8px 12px;
    margin-bottom: 9px;
    font-size: 11px;
    color: #34d399;
    box-shadow: 0 0 15px rgba(16, 185, 129, 0.25);
  }

  .discovered-banner.show {
    display: flex;
  }

  .quick-connect-btn {
    background: #10b981;
    color: #000;
    border: none;
    border-radius: 6px;
    padding: 5px 11px;
    font-size: 10.5px;
    font-weight: 800;
    cursor: pointer;
    box-shadow: 0 2px 8px rgba(16, 185, 129, 0.4);
    transition: all 0.2s;
  }
  .quick-connect-btn:hover {
    filter: brightness(1.15);
    transform: translateY(-1px);
  }

  /* Toast Notification */
  .toast {
    position: fixed;
    bottom: 22px;
    left: 50%;
    transform: translateX(-50%) translateY(50px);
    background: rgba(15, 23, 42, 0.95);
    border: 1px solid var(--amber-neon);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.6);
    color: #fff;
    padding: 9px 18px;
    border-radius: 20px;
    font-size: 11.5px;
    font-weight: 600;
    display: flex; align-items: center; gap: 8px;
    opacity: 0; pointer-events: none;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
    z-index: 100;
  }

  .toast.show {
    opacity: 1;
    transform: translateX(-50%) translateY(0);
  }

  /* Launch Overlay */
  .launch-overlay {
    position: fixed;
    inset: 0;
    background: rgba(6, 9, 17, 0.96);
    backdrop-filter: blur(20px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 200;
    opacity: 0;
    pointer-events: none;
    transition: all 0.3s cubic-bezier(0.16, 1, 0.3, 1);
  }

  .launch-overlay.active {
    opacity: 1;
    pointer-events: all;
  }

  .spinner {
    width: 44px; height: 44px;
    border: 3.5px solid rgba(255, 255, 255, 0.1);
    border-top-color: var(--amber-neon);
    border-radius: 50%;
    animation: spin 0.75s linear infinite;
    margin-bottom: 14px;
  }
  @keyframes spin { to { transform: rotate(360deg); } }

  .overlay-title {
    font-size: 17px;
    font-weight: 800;
    color: #fff;
    margin-bottom: 5px;
  }

  .overlay-sub {
    font-size: 11.5px;
    color: var(--text-secondary);
  }
</style>
</head>
<body>

<div class="glow-orb-1"></div>
<div class="glow-orb-2"></div>

<div class="hero-header">
  <div class="route66-badge-container">
    <div class="shield-outer">
      <div class="shield-inner">⛽</div>
    </div>
  </div>
  <h1 class="main-title">GAS STATION SIMULATOR</h1>
  <div class="sub-tagline">CO-OP MULTIPLAYER ENGINE • ROUTE 66</div>
</div>

<!-- Creator & GitHub Banner -->
<div class="creator-banner">
  <div class="creator-left">
    <div class="creator-avatar">NK</div>
    <div class="creator-info">
      <h4>Lead Architect & Creator</h4>
      <p>Nithin Kumar (@Nithinkumaru777) ✓</p>
    </div>
  </div>
  <button class="github-btn" onclick="openGitHub()">
    <svg width="12" height="12" viewBox="0 0 24 24" fill="currentColor"><path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/></svg>
    GitHub Repo →
  </button>
</div>

<!-- Player Name -->
<div class="player-name-row">
  <div class="section-title">👤 Your Player Display Name</div>
  <input type="text" id="playerNameInput" class="player-name-input" value="Nithin" placeholder="Enter your display name...">
</div>

<!-- Character Selector -->
<div class="section-title">🎭 Select In-Game Character Model</div>
<div class="char-grid">
  <div class="char-card selected" id="char-biker" onclick="selectCharacter('biker')">
    <div class="char-icon">🏍️</div>
    <div class="char-name">Route 66 Biker</div>
    <div class="char-role">Highway Rider</div>
  </div>
  <div class="char-card" id="char-delivery" onclick="selectCharacter('delivery')">
    <div class="char-icon">⛽</div>
    <div class="char-name">Fuel Specialist</div>
    <div class="char-role">Delivery Pro</div>
  </div>
  <div class="char-card" id="char-worker" onclick="selectCharacter('worker')">
    <div class="char-icon">🔧</div>
    <div class="char-name">Station Worker</div>
    <div class="char-role">Mechanic</div>
  </div>
  <div class="char-card" id="char-party" onclick="selectCharacter('party')">
    <div class="char-icon">👽</div>
    <div class="char-name">Party Cruiser</div>
    <div class="char-role">Alien Vibes</div>
  </div>
</div>

<!-- Options: Host or Join -->
<div class="mode-cards">
  <!-- Option 1: Host -->
  <div class="mode-card">
    <div class="card-header">
      <div class="mode-pill pill-host">Option 1 • Server Mode</div>
      <span style="font-size: 10px; color: var(--amber-neon); font-weight: 700;">UDP 7777</span>
    </div>
    <div class="mode-title">HOST A WORLD</div>
    <div class="mode-desc">Start your Route 66 Gas Station. Automatically copies your IP address to clipboard for your friends.</div>
    <button class="action-btn btn-host" onclick="triggerHostAction()">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><circle cx="12" cy="12" r="10"/><path d="M12 8v8"/><path d="M8 12h8"/></svg>
      START HOST SERVER & ENTER
    </button>
  </div>

  <!-- Option 2: Join -->
  <div class="mode-card">
    <div class="card-header">
      <div class="mode-pill pill-join">Option 2 • Client Mode</div>
      <span style="font-size: 10px; color: var(--cyan-neon); font-weight: 700;">Direct Connect</span>
    </div>
    <div class="mode-title">JOIN A WORLD</div>
    <div class="mode-desc">Connect to your friend's station (Auto-detects live LAN servers or paste friend's IP).</div>

    <!-- Live Auto-Discovery Scanning Banner -->
    <div class="discovery-status-bar" id="scanStatus">
      <div style="display: flex; align-items: center; gap: 6px;">
        <span class="live-dot"></span>
        <span id="scanStatusText">Auto-Scanning Wi-Fi & LAN for active Hosts...</span>
      </div>
      <span style="font-size: 9px; opacity: 0.7;">UDP 7777</span>
    </div>

    <!-- Discovered Host Banner -->
    <div class="discovered-banner" id="discBanner">
      <div>
        <span style="font-weight: 700; color: #fff;">🟢 Station Found:</span>
        <span id="discName" style="margin-left: 4px; font-weight: 600;">Host (192.168.x.x)</span>
      </div>
      <button class="quick-connect-btn" onclick="connectToDiscoveredHost()">⚡ Quick Connect</button>
    </div>

    <div class="ip-input-container">
      <input type="text" id="hostIpInput" class="ip-input" placeholder="192.168.x.x or paste IP...">
      <button class="paste-btn" onclick="pasteFromClipboard(event)">📋 Paste</button>
    </div>
    <button class="action-btn btn-join" onclick="triggerJoinAction(event)">
      <svg width="15" height="15" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M5 12h14"/><path d="m12 5 7 7-7 7"/></svg>
      CONNECT TO STATION & ENTER
    </button>
  </div>
</div>

<div class="toast" id="toastMsg">✓ Notification</div>

<!-- Launching Overlay -->
<div class="launch-overlay" id="launchOverlay">
  <div class="spinner"></div>
  <div class="overlay-title" id="overlayTitle">Starting Multiplayer Session...</div>
  <div class="overlay-sub" id="overlaySubtitle">Connecting to Gas Station Simulator world...</div>
</div>

<script>
  let selectedChar = 'biker';
  let discoveredIp = '';

  function selectCharacter(id) {
    selectedChar = id;
    document.querySelectorAll('.char-card').forEach(c => c.classList.remove('selected'));
    const target = document.getElementById('char-' + id);
    if (target) target.classList.add('selected');
    showToast('CHARACTER SELECTED: ' + id.toUpperCase());
  }

  function showToast(msg) {
    const toast = document.getElementById('toastMsg');
    toast.innerText = msg;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 2500);
  }

  function openGitHub() {
    if (window.pywebview && pywebview.api && pywebview.api.open_github) {
      pywebview.api.open_github();
    } else {
      window.open('https://github.com/Nithinkumaru777/GasStationCoop', '_blank');
    }
  }

  async function pasteFromClipboard(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const text = await navigator.clipboard.readText();
        if (text && text.trim()) {
          document.getElementById('hostIpInput').value = text.trim();
          showToast('PASTED IP: ' + text.trim());
          return;
        }
      }
    } catch (_) {}

    if (window.pywebview && pywebview.api && pywebview.api.read_clipboard) {
      pywebview.api.read_clipboard().then(txt => {
        if (txt && txt.trim()) {
          document.getElementById('hostIpInput').value = txt.trim();
          showToast('PASTED IP: ' + txt.trim());
        } else {
          showToast('Clipboard is empty');
        }
      }).catch(() => {
        showToast('Clipboard paste ready');
      });
    }
  }

  function triggerHostAction() {
    const name = document.getElementById('playerNameInput').value.trim() || 'Nithin';
    if (window.pywebview && pywebview.api) {
      pywebview.api.host_world(selectedChar, name).then(res => {
        showToast('HOST IP COPIED: ' + res.ip);
        document.getElementById('overlayTitle').innerText = 'Starting Co-op Host Server...';
        document.getElementById('overlaySubtitle').innerText = 'Your IP: ' + res.ip + ' (Copied to Clipboard)';
        document.getElementById('launchOverlay').classList.add('active');
      });
    }
  }

  function triggerJoinAction(e) {
    if (e) { e.preventDefault(); e.stopPropagation(); }
    const targetIp = document.getElementById('hostIpInput').value.trim() || '127.0.0.1';
    const name = document.getElementById('playerNameInput').value.trim() || 'Partner';
    if (window.pywebview && pywebview.api) {
      pywebview.api.join_world(targetIp, selectedChar, name).then(res => {
        document.getElementById('overlayTitle').innerText = 'Connecting to Co-op Station...';
        document.getElementById('overlaySubtitle').innerText = 'Target: ' + res.connecting_to + ':7777';
        document.getElementById('launchOverlay').classList.add('active');
      });
    }
  }

  function connectToDiscoveredHost() {
    if (discoveredIp) {
      document.getElementById('hostIpInput').value = discoveredIp;
      triggerJoinAction();
    }
  }

  document.getElementById('hostIpInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      triggerJoinAction(e);
    }
  });

  function pollHostDiscovery() {
    if (window.pywebview && pywebview.api && pywebview.api.check_for_host) {
      pywebview.api.check_for_host().then(res => {
        if (res && res.found) {
          discoveredIp = res.ip;
          document.getElementById('discName').innerText = (res.name || 'Friend') + ' (' + res.ip + ')';
          document.getElementById('discBanner').classList.add('show');
          document.getElementById('scanStatus').style.display = 'none';
          if (!document.getElementById('hostIpInput').value.trim()) {
            document.getElementById('hostIpInput').value = res.ip;
          }
        }
      });
    }
  }

  window.addEventListener('pywebviewready', () => {
    pollHostDiscovery();
    // Continuous polling every 1.5 seconds!
    setInterval(pollHostDiscovery, 1500);
  });
</script>
</body>
</html>
"""

def main():
    api = LauncherApi()
    window = webview.create_window(
        title="Gas Station Simulator Co-op Launcher",
        html=HTML_UI,
        js_api=api,
        width=520,
        height=720,
        resizable=False,
        background_color="#060911"
    )
    api.set_window(window)
    webview.start()

if __name__ == "__main__":
    main()
