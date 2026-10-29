"""Award-Winning, Next-Gen Co-op Launcher for Gas Station Simulator.
Built with Edge Chromium Webview2, High-Contrast Cyber/Desert Aesthetic,
Smooth CSS3 Keyframe Animations, Staggered Reveals, Auto-Discovery & Pure Win32 Clipboard.

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

def find_game_directory():
    # 1. Current script folder
    cur_dir = os.path.dirname(os.path.abspath(__file__))
    if os.path.exists(os.path.join(cur_dir, "GSS2-Win64-Shipping.exe")):
        return cur_dir

    # 2. Subfolder GSS2/Binaries/Win64
    sub = os.path.join(cur_dir, "GSS2", "Binaries", "Win64")
    if os.path.exists(os.path.join(sub, "GSS2-Win64-Shipping.exe")):
        return sub

    # 3. Sandboxes (if on dev PC)
    for p in [r"D:\coop-sandbox\gss\A\GSS2\Binaries\Win64", r"D:\coop-sandbox\gss\B\GSS2\Binaries\Win64"]:
        if os.path.exists(os.path.join(p, "GSS2-Win64-Shipping.exe")):
            return p

    # 4. Steam common installs
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

CREATE_NO_WINDOW = 0x08000000

# -------------------------------------------------------------
# Pure Win32 Zero-Latency Clipboard (No Tkinter, No Deadlocks)
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
        h = kernel32.GlobalAlloc(0x0042, len(data))  # GMEM_MOVEABLE | GMEM_ZEROINIT
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

def get_network_ips():
    ips = []
    # 1. Primary LAN IP (fastest socket connect, 0ms)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith("127."):
            ips.append(primary)
    except Exception:
        pass

    # 2. Virtual adapters (Radmin VPN, Tailscale)
    try:
        out = subprocess.check_output("ipconfig", text=True, stderr=subprocess.DEVNULL, creationflags=CREATE_NO_WINDOW)
        for line in out.splitlines():
            if "IPv4" in line:
                val = line.split(":")[-1].strip()
                if val and val not in ips and not val.startswith("127."):
                    ips.append(val)
    except Exception:
        pass

    return ips if ips else ["127.0.0.1"]


def scan_for_local_host(timeout=0.6):
    """Fast auto-discovery of local hosts on port 7777."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(timeout)
        s.sendto(b"GSS_DISCOVER", ("<broadcast>", 7777))
        s.sendto(b"GSS_DISCOVER", ("127.0.0.1", 7777))
        start = time.time()
        while time.time() - start < timeout:
            try:
                data, addr = s.recvfrom(1024)
                text = data.decode("utf-8", errors="replace")
                if text.startswith("GSS_OFFER:") or text.startswith("GSS_BEACON:"):
                    parts = text.split(":", 2)
                    name = parts[2] if len(parts) >= 3 else "Friend's Station"
                    s.close()
                    return {"found": True, "ip": addr[0], "name": name}
            except socket.timeout:
                break
            except Exception:
                pass
        s.close()
    except Exception:
        pass
    return {"found": False, "ip": "", "name": ""}


def ensure_optimal_game_settings(game_dir, w, h):
    """Enforces high-performance 180Hz Borderless Mode at 2560x1600 native display."""
    ini_paths = []
    if "coop-sandbox" in game_dir:
        ini_paths.append(r"D:\coop-sandbox\gss\userA\Saved__coopA\Config\WindowsNoEditor\GameUserSettings.ini")
    
    appdata = os.getenv("LOCALAPPDATA")
    if appdata:
        ini_paths.append(os.path.join(appdata, "GSS2", "Saved", "Config", "WindowsNoEditor", "GameUserSettings.ini"))

    for ini_path in ini_paths:
        try:
            os.makedirs(os.path.dirname(ini_path), exist_ok=True)
            content = f"""[/Script/Engine.GameUserSettings]
FullscreenMode=1
LastConfirmedFullscreenMode=1
PreferredFullscreenMode=1
ResolutionSizeX={w}
ResolutionSizeY={h}
LastUserConfirmedResolutionSizeX={w}
LastUserConfirmedResolutionSizeY={h}
DesiredScreenWidth={w}
DesiredScreenHeight={h}
LastUserConfirmedDesiredScreenWidth={w}
LastUserConfirmedDesiredScreenHeight={h}
FrameRateLimit=180.000000
bUseVSync=False
bUseDynamicResolution=False
Version=5
AudioQualityLevel=0
LastConfirmedAudioQualityLevel=0
bUseDesiredScreenHeight=False
Brightness=2.200000
MonitorIndex=0
ScalabilityOverall=3
SSGI=1
InvertLookX=False
InvertLookY=False
CameraSpeedMultiplierX=1.000000
CameraSpeedMultiplierY=1.000000
Rumble=False
ToogleSprintMode=False
ToggleInspectMode=False
BenchmarkAlreadyRan=1.000000

[ScalabilityGroups]
sg.ResolutionQuality=100.000000
sg.ViewDistanceQuality=3
sg.AntiAliasingQuality=3
sg.ShadowQuality=2
sg.PostProcessQuality=2
sg.TextureQuality=3
sg.EffectsQuality=2
sg.FoliageQuality=2
sg.ShadingQuality=3

[/Script/Engine.RendererSettings]
MotionBlurEnabled=False
LensFlaresEnabled=True
SSREnabled=True
BloomEnabled=True
AntiAliasingMethod=2
AmbientOcclusionEnabled=True

[DefaultInputBindingsVersion]
DefaultInputBindingsVersion=1.0.0.5
"""
            with open(ini_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception:
            pass

def ensure_starter_saves(game_dir):
    """Guarantees that a valid Starter Save exists on both Host and Guest machines,
    so ContinueButton is always enabled and the guest loads straight into the gas station."""
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


def launch_game_process(role, target_ip="127.0.0.1"):
    game_dir = find_game_directory()
    exe_path = os.path.join(game_dir, "GSS2-Win64-Shipping.exe")
    scr_w, scr_h = get_screen_metrics()
    ensure_optimal_game_settings(game_dir, scr_w, scr_h)
    ensure_starter_saves(game_dir)

    # 1. Update role.txt
    for path in [
        os.path.join(game_dir, "role.txt"),
        os.path.join(game_dir, "net", "role.txt"),
        os.path.join(game_dir, "Mods", "GasStationCoop", "role.txt")
    ]:
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
            with open(path, "w", encoding="utf-8") as f:
                f.write(f"{role}\n")
        except Exception:
            pass

    # 2. If client, update host_ip.txt
    if role == "guest":
        for path in [
            os.path.join(game_dir, "host_ip.txt"),
            os.path.join(game_dir, "net", "host_ip.txt")
        ]:
            try:
                os.makedirs(os.path.dirname(path), exist_ok=True)
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"{target_ip}\n")
            except Exception:
                pass

    # 3. Launch silent background relay via pythonw
    relay_script = os.path.join(game_dir, "gss_relay.py")
    if not os.path.exists(relay_script):
        cur_dir = os.path.dirname(os.path.abspath(__file__))
        alt_relay = os.path.join(cur_dir, "gss_relay.py")
        if os.path.exists(alt_relay):
            import shutil
            shutil.copy2(alt_relay, relay_script)

    if os.path.exists(relay_script):
        if role == "host":
            subprocess.Popen(
                ["pythonw", relay_script, "--mode", "host", "--netdir", os.path.join(game_dir, "net")],
                cwd=game_dir,
                creationflags=CREATE_NO_WINDOW
            )
        else:
            subprocess.Popen(
                ["pythonw", relay_script, "--mode", "client", "--connect", target_ip, "--netdir", os.path.join(game_dir, "net")],
                cwd=game_dir,
                creationflags=CREATE_NO_WINDOW
            )

    # 4. Launch game in native Borderless mode (2560x1600 @ 180Hz)
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
        ips = get_network_ips()
        return {
            "primary_ip": ips[0] if ips else "127.0.0.1",
            "all_ips": ips
        }

    def check_for_host(self):
        return scan_for_local_host(timeout=0.5)

    def copy_to_clipboard(self, text):
        return win32_set_clipboard_text(text)

    def read_clipboard(self):
        return win32_get_clipboard_text()

    def host_world(self):
        ips = get_network_ips()
        primary = ips[0]
        win32_set_clipboard_text(primary)

        try:
            game_dir = find_game_directory()
            with open(os.path.join(game_dir, "my_ip.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(ips))
        except Exception:
            pass

        def do_launch():
            time.sleep(1.2)
            launch_game_process("host")
            time.sleep(1.0)
            if self.window:
                self.window.destroy()

        threading.Thread(target=do_launch, daemon=True).start()
        return {"status": "ok", "ip": primary, "all_ips": ips}

    def join_world(self, target_ip):
        clean_ip = (target_ip or "").strip()
        if not clean_ip:
            clean_ip = "127.0.0.1"

        def do_launch():
            time.sleep(1.0)
            launch_game_process("guest", clean_ip)
            time.sleep(1.0)
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
    padding: 22px 24px 20px 24px;
    position: relative;
    user-select: none;
    -webkit-user-select: none;
  }

  /* Custom Slim Modern Scrollbar */
  ::-webkit-scrollbar { width: 6px; }
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
    margin-bottom: 8px;
    position: relative;
  }

  .shield-outer {
    width: 58px; height: 58px;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 2px solid var(--amber-neon);
    border-radius: 18px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 25px var(--amber-glow), inset 0 1px 1px rgba(255, 255, 255, 0.3);
    animation: pulseBadge 3.5s infinite alternate ease-in-out;
  }
  @keyframes pulseBadge {
    0% { box-shadow: 0 0 15px var(--amber-glow); transform: scale(1); }
    100% { box-shadow: 0 0 32px var(--amber-glow); transform: scale(1.04); }
  }
  .shield-outer svg {
    width: 32px; height: 32px; fill: var(--amber-neon);
  }

  .title-glitch {
    font-size: 22px;
    font-weight: 900;
    letter-spacing: 1.5px;
    line-height: 1.15;
    text-transform: uppercase;
    background: linear-gradient(90deg, #ffffff 0%, #fbbf24 40%, #ffffff 80%);
    background-size: 200% auto;
    -webkit-background-clip: text;
    -webkit-text-fill-color: transparent;
    animation: shimmerText 5s linear infinite;
  }
  @keyframes shimmerText {
    0% { background-position: 0% center; }
    100% { background-position: 200% center; }
  }

  .subtitle-pill {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    margin-top: 4px;
    padding: 3px 12px;
    background: rgba(6, 182, 212, 0.12);
    border: 1px solid rgba(6, 182, 212, 0.35);
    border-radius: 20px;
    font-size: 10px;
    font-weight: 800;
    letter-spacing: 1.5px;
    color: #38bdf8;
    text-transform: uppercase;
  }
  .pulse-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #38bdf8; box-shadow: 0 0 8px #38bdf8;
    animation: blinkDot 1.6s infinite alternate;
  }
  @keyframes blinkDot {
    0% { opacity: 0.3; } 100% { opacity: 1; }
  }

  /* Developer Card (NITHIN KUMAR) */
  .dev-attribution-card {
    position: relative;
    z-index: 2;
    background: rgba(15, 23, 42, 0.72);
    backdrop-filter: blur(12px);
    border: 1px solid rgba(255, 255, 255, 0.1);
    border-radius: 14px;
    padding: 10px 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 12px;
    box-shadow: 0 8px 24px rgba(0, 0, 0, 0.4);
    transition: all 0.3s ease;
  }
  .dev-attribution-card:hover {
    border-color: rgba(245, 158, 11, 0.4);
    box-shadow: 0 8px 28px rgba(245, 158, 11, 0.15);
  }
  .dev-info-left {
    display: flex;
    align-items: center;
    gap: 10px;
  }
  .dev-avatar {
    width: 36px; height: 36px;
    border-radius: 10px;
    background: linear-gradient(135deg, #f59e0b, #d97706);
    color: #000;
    font-size: 13px;
    font-weight: 900;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 14px var(--amber-glow);
  }
  .dev-texts {
    display: flex;
    flex-direction: column;
    text-align: left;
  }
  .dev-role-label {
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
    color: var(--amber-neon);
    text-transform: uppercase;
  }
  .dev-author-name {
    font-size: 13px;
    font-weight: 800;
    color: #fff;
    display: flex;
    align-items: center;
    gap: 4px;
  }
  .dev-handle {
    font-size: 11px;
    font-weight: 500;
    color: #94a3b8;
  }
  .verified-badge {
    width: 14px; height: 14px; fill: #10b981;
  }
  .btn-github-link {
    background: rgba(255, 255, 255, 0.08);
    border: 1px solid rgba(255, 255, 255, 0.15);
    border-radius: 8px;
    padding: 6px 12px;
    font-size: 11px;
    font-weight: 700;
    color: #f1f5f9;
    cursor: pointer;
    display: flex;
    align-items: center;
    gap: 6px;
    transition: all 0.25s ease;
  }
  .btn-github-link:hover {
    background: #ffffff;
    color: #0f172a;
    border-color: #ffffff;
    box-shadow: 0 0 15px rgba(255, 255, 255, 0.4);
    transform: translateY(-1px);
  }
  .btn-github-link svg {
    width: 14px; height: 14px; fill: currentColor;
  }

  /* Auto-Discovery Banner */
  .auto-discovery-banner {
    display: none;
    position: relative;
    z-index: 2;
    background: rgba(16, 185, 129, 0.15);
    border: 1px solid var(--emerald-neon);
    border-radius: 12px;
    padding: 10px 14px;
    margin-bottom: 12px;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 0 20px rgba(16, 185, 129, 0.25);
    cursor: pointer;
    animation: pulseBorder 2s infinite alternate ease-in-out;
  }
  @keyframes pulseBorder {
    0% { border-color: rgba(16, 185, 129, 0.5); }
    100% { border-color: rgba(16, 185, 129, 1); }
  }
  .auto-discovery-banner.show { display: flex; }
  .disc-info { text-align: left; }
  .disc-title { font-size: 12px; font-weight: 800; color: #34d399; }
  .disc-sub { font-size: 11px; color: #cbd5e1; }
  .btn-quick-join {
    background: #10b981;
    color: #000;
    font-size: 11px;
    font-weight: 800;
    padding: 6px 12px;
    border: none;
    border-radius: 8px;
    cursor: pointer;
    transition: all 0.2s;
  }
  .btn-quick-join:hover {
    background: #34d399;
    box-shadow: 0 0 12px #34d399;
  }

  /* Action Cards */
  .cards-wrapper {
    display: flex;
    flex-direction: column;
    gap: 12px;
    position: relative;
    z-index: 2;
  }

  .action-card {
    background: var(--card-surface);
    backdrop-filter: blur(14px);
    border: 1px solid var(--card-border);
    border-radius: 16px;
    padding: 15px 18px;
    cursor: pointer;
    position: relative;
    overflow: hidden;
    transition: all 0.28s cubic-bezier(0.16, 1, 0.3, 1);
    box-shadow: 0 10px 30px rgba(0, 0, 0, 0.35);
  }
  .action-card::before {
    content: '';
    position: absolute;
    top: 0; left: 0; right: 0; height: 1px;
    background: linear-gradient(90deg, transparent, rgba(255, 255, 255, 0.2), transparent);
    opacity: 0;
    transition: opacity 0.3s ease;
  }
  .action-card:hover {
    transform: translateY(-3px) scale(1.008);
    border-color: var(--card-hover-border);
    box-shadow: 0 18px 40px rgba(0, 0, 0, 0.5);
  }
  .action-card:hover::before { opacity: 1; }
  .action-card:active { transform: scale(0.985); }

  .action-card.host-card {
    border-left: 4px solid var(--emerald-neon);
  }
  .action-card.host-card:hover {
    box-shadow: 0 18px 45px rgba(16, 185, 129, 0.2);
    border-color: rgba(16, 185, 129, 0.6);
  }

  .action-card.join-card {
    border-left: 4px solid var(--cyan-neon);
  }
  .action-card.join-card:hover {
    box-shadow: 0 18px 45px rgba(6, 182, 212, 0.2);
    border-color: rgba(6, 182, 212, 0.6);
  }

  .card-header-row {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 6px;
  }
  .card-badge {
    font-size: 9px;
    font-weight: 800;
    letter-spacing: 1px;
    padding: 3px 8px;
    border-radius: 6px;
    text-transform: uppercase;
  }
  .host-badge {
    background: rgba(16, 185, 129, 0.15);
    color: #34d399;
    border: 1px solid rgba(16, 185, 129, 0.3);
  }
  .join-badge {
    background: rgba(6, 182, 212, 0.15);
    color: #38bdf8;
    border: 1px solid rgba(6, 182, 212, 0.3);
  }

  .card-action-icon {
    width: 28px; height: 28px;
    border-radius: 8px;
    background: rgba(255, 255, 255, 0.05);
    display: flex; align-items: center; justify-content: center;
    font-size: 13px; font-weight: 900;
    transition: transform 0.25s ease;
  }
  .action-card:hover .card-action-icon {
    transform: translateX(3px);
    background: rgba(255, 255, 255, 0.15);
  }

  .card-main-title {
    font-size: 17px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 4px;
    display: flex;
    align-items: center;
    gap: 8px;
  }
  .card-desc {
    font-size: 12px;
    color: var(--text-secondary);
    line-height: 1.4;
    margin-bottom: 10px;
  }

  .pills-row {
    display: flex;
    flex-wrap: wrap;
    gap: 6px;
  }
  .spec-pill {
    font-size: 10px;
    font-weight: 600;
    background: rgba(0, 0, 0, 0.35);
    border: 1px solid rgba(255, 255, 255, 0.07);
    border-radius: 6px;
    padding: 2px 7px;
    color: #cbd5e1;
  }

  /* Join Drawer (Full Height & Never Clipped) */
  .join-drawer {
    display: none;
    background: rgba(11, 17, 30, 0.96);
    border: 1px solid rgba(6, 182, 212, 0.35);
    border-radius: 14px;
    padding: 16px 18px;
    margin-top: -4px;
    margin-bottom: 8px;
    animation: drawerSlide 0.25s cubic-bezier(0.16, 1, 0.3, 1) forwards;
  }
  @keyframes drawerSlide {
    0% { opacity: 0; transform: translateY(-8px); }
    100% { opacity: 1; transform: translateY(0); }
  }
  .join-drawer.active { display: block; }

  .drawer-label {
    font-size: 12px;
    font-weight: 800;
    color: #38bdf8;
    margin-bottom: 8px;
    display: flex;
    align-items: center;
    gap: 6px;
  }
  .ip-input-box {
    display: flex;
    gap: 8px;
    margin-bottom: 12px;
  }
  .ip-input {
    flex: 1;
    background: rgba(0, 0, 0, 0.65);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 10px;
    padding: 11px 14px;
    color: #38bdf8;
    font-family: Consolas, "Courier New", monospace;
    font-size: 14px;
    font-weight: 700;
    letter-spacing: 0.5px;
    outline: none;
    user-select: text !important;
    -webkit-user-select: text !important;
    transition: all 0.25s ease;
  }
  .ip-input:focus {
    border-color: var(--cyan-neon);
    box-shadow: 0 0 14px var(--cyan-glow);
    background: rgba(0, 0, 0, 0.8);
  }
  .btn-paste {
    background: rgba(255, 255, 255, 0.1);
    border: 1px solid rgba(255, 255, 255, 0.2);
    border-radius: 10px;
    padding: 0 16px;
    font-size: 12px;
    font-weight: 800;
    color: #f1f5f9;
    cursor: pointer;
    transition: all 0.2s ease;
  }
  .btn-paste:hover {
    background: rgba(255, 255, 255, 0.22);
    box-shadow: 0 0 10px rgba(255, 255, 255, 0.3);
  }
  .btn-connect-launch {
    width: 100%;
    background: linear-gradient(135deg, #0284c7, #06b6d4);
    border: none;
    border-radius: 10px;
    padding: 12px;
    color: #fff;
    font-size: 13px;
    font-weight: 900;
    letter-spacing: 0.8px;
    text-transform: uppercase;
    cursor: pointer;
    box-shadow: 0 4px 18px rgba(6, 182, 212, 0.4);
    transition: all 0.25s ease;
    display: flex; align-items: center; justify-content: center; gap: 8px;
  }
  .btn-connect-launch:hover {
    filter: brightness(1.15);
    box-shadow: 0 6px 25px rgba(6, 182, 212, 0.6);
    transform: translateY(-1px);
  }

  .footer-bar {
    margin-top: 14px;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding-top: 10px;
    border-top: 1px solid rgba(255, 255, 255, 0.08);
    position: relative;
    z-index: 2;
  }
  .network-pill {
    display: flex;
    align-items: center;
    gap: 6px;
    font-size: 11px;
    font-weight: 600;
    color: #94a3b8;
  }
  .net-dot {
    width: 6px; height: 6px; border-radius: 50%;
    background: #10b981; box-shadow: 0 0 6px #10b981;
  }
  .version-tag {
    font-size: 10px;
    font-weight: 700;
    color: #64748b;
    letter-spacing: 0.5px;
  }

  .toast-alert {
    position: fixed;
    bottom: 24px;
    left: 50%;
    transform: translateX(-50%) translateY(70px);
    background: rgba(15, 23, 42, 0.96);
    backdrop-filter: blur(14px);
    border: 1px solid var(--emerald-neon);
    border-radius: 30px;
    padding: 10px 22px;
    display: flex;
    align-items: center;
    gap: 10px;
    box-shadow: 0 10px 30px var(--emerald-glow);
    z-index: 99;
    opacity: 0;
    pointer-events: none;
    transition: all 0.4s cubic-bezier(0.16, 1, 0.3, 1);
  }
  .toast-alert.show {
    transform: translateX(-50%) translateY(0);
    opacity: 1;
    pointer-events: auto;
  }
  .toast-icon {
    width: 18px; height: 18px; fill: var(--emerald-neon);
  }
  .toast-text {
    font-size: 12px;
    font-weight: 700;
    color: #ffffff;
  }

  .launch-overlay {
    position: fixed;
    inset: 0;
    background: rgba(4, 6, 12, 0.95);
    backdrop-filter: blur(16px);
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    z-index: 100;
    opacity: 0;
    pointer-events: none;
    transition: opacity 0.35s ease;
  }
  .launch-overlay.active {
    opacity: 1;
    pointer-events: auto;
  }
  .radar-spinner {
    width: 60px; height: 60px;
    border: 3px solid rgba(245, 158, 11, 0.2);
    border-top: 3px solid var(--amber-neon);
    border-radius: 50%;
    animation: spinRadar 1s linear infinite;
    margin-bottom: 18px;
    box-shadow: 0 0 25px var(--amber-glow);
  }
  @keyframes spinRadar {
    0% { transform: rotate(0deg); }
    100% { transform: rotate(360deg); }
  }
  .overlay-title {
    font-size: 18px;
    font-weight: 800;
    color: #ffffff;
    margin-bottom: 6px;
  }
  .overlay-subtitle {
    font-size: 12px;
    color: #94a3b8;
  }
</style>
</head>
<body>

  <div class="glow-orb-1"></div>
  <div class="glow-orb-2"></div>

  <div class="hero-header">
    <div class="route66-badge-container">
      <div class="shield-outer">
        <svg viewBox="0 0 24 24">
          <path d="M12 2L3 6v6c0 5.55 3.84 10.74 9 12 5.16-1.26 9-6.45 9-12V6l-9-4zm-1 14.5l-3.5-3.5 1.41-1.41L11 13.67l5.59-5.59L18 9.5 11 16.5z"/>
        </svg>
      </div>
    </div>
    <h1 class="title-glitch">Gas Station Co-Op</h1>
    <div class="subtitle-pill">
      <div class="pulse-dot"></div>
      <span>Multiplayer Engine &bull; Route 66</span>
    </div>
  </div>

  <!-- Developer Attribution (NITHIN KUMAR) -->
  <div class="dev-attribution-card">
    <div class="dev-info-left">
      <div class="dev-avatar">NK</div>
      <div class="dev-texts">
        <span class="dev-role-label">Lead Architect & Creator</span>
        <div class="dev-author-name">
          Nithin Kumar
          <span class="dev-handle">@Nithinkumaru777</span>
          <svg class="verified-badge" viewBox="0 0 24 24">
            <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm-2 15l-5-5 1.41-1.41L10 14.17l7.59-7.59L19 8l-9 9z"/>
          </svg>
        </div>
      </div>
    </div>
    <button class="btn-github-link" onclick="openGitHub()">
      <svg viewBox="0 0 24 24">
        <path d="M12 0C5.37 0 0 5.37 0 12c0 5.31 3.435 9.795 8.205 11.385.6.105.825-.255.825-.57 0-.285-.015-1.23-.015-2.235-3.015.555-3.795-.735-4.035-1.41-.135-.345-.72-1.41-1.23-1.695-.42-.225-1.02-.78-.015-.795.945-.015 1.62.87 1.845 1.23 1.08 1.815 2.805 1.305 3.495.99.105-.78.42-1.305.765-1.605-2.67-.3-5.46-1.335-5.46-5.925 0-1.305.465-2.385 1.23-3.225-.12-.3-.54-1.53.12-3.18 0 0 1.005-.315 3.3 1.23.96-.27 1.98-.405 3-.405s2.04.135 3 .405c2.295-1.56 3.3-1.23 3.3-1.23.66 1.65.24 2.88.12 3.18.765.84 1.23 1.905 1.23 3.225 0 4.605-2.805 5.625-5.475 5.925.435.375.81 1.095.81 2.22 0 1.605-.015 2.895-.015 3.3 0 .315.225.69.825.57A12.02 12.02 0 0024 12c0-6.63-5.37-12-12-12z"/>
      </svg>
      GitHub Repo &rarr;
    </button>
  </div>

  <!-- Auto-Discovered Host Banner -->
  <div class="auto-discovery-banner" id="discBanner" onclick="connectToDiscoveredHost()">
    <div class="disc-info">
      <div class="disc-title">&#128994; Friend's Station Detected on Network:</div>
      <div class="disc-sub" id="discName">Host: Loading...</div>
    </div>
    <button class="btn-quick-join">AUTO-JOIN &rarr;</button>
  </div>

  <div class="cards-wrapper">

    <!-- Option 1: HOST -->
    <div class="action-card host-card" onclick="triggerHostAction()">
      <div class="card-header-row">
        <span class="card-badge host-badge">Option 1 &bull; Server Mode</span>
        <div class="card-action-icon">&rarr;</div>
      </div>
      <div class="card-main-title">
        <span>HOST A WORLD</span>
      </div>
      <div class="card-desc">
        Start your station & host multiplayer session. Automatically detects and copies your IP address for friends.
      </div>
      <div class="pills-row">
        <span class="spec-pill">&#9889; Auto-Copies IP</span>
        <span class="spec-pill">&#127760; Port 7777</span>
        <span class="spec-pill">&#128187; LAN / Wi-Fi / VPN</span>
      </div>
    </div>

    <!-- Option 2: JOIN -->
    <div class="action-card join-card" onclick="toggleJoinDrawer()">
      <div class="card-header-row">
        <span class="card-badge join-badge">Option 2 &bull; Client Mode</span>
        <div class="card-action-icon" id="joinChevron">&#9662;</div>
      </div>
      <div class="card-main-title">
        <span>JOIN A WORLD</span>
      </div>
      <div class="card-desc">
        Connect to a friend's hosted station from any Wi-Fi, LAN, or Radmin / Tailscale VPN network.
      </div>
      <div class="pills-row">
        <span class="spec-pill">&#128101; 2-Player Co-op</span>
        <span class="spec-pill">&#128279; Direct Connect</span>
        <span class="spec-pill">&#9889; Instant Handshake</span>
      </div>
    </div>

    <!-- Join Drawer -->
    <div class="join-drawer" id="joinDrawer">
      <div class="drawer-label">
        <svg style="width:14px;height:14px;fill:currentColor;" viewBox="0 0 24 24">
          <path d="M12 2C8.13 2 5 5.13 5 9c0 5.25 7 13 7 13s7-7.75 7-13c0-3.87-3.13-7-7-7zm0 9.5c-1.38 0-2.5-1.12-2.5-2.5s1.12-2.5 2.5-2.5 2.5 1.12 2.5 2.5-1.12 2.5-2.5 2.5z"/>
        </svg>
        Target Friend's Host IP Address:
      </div>
      <div class="ip-input-box">
        <input type="text" class="ip-input" id="hostIpInput" value="127.0.0.1" placeholder="e.g. 192.168.1.13" spellcheck="false" autocomplete="off">
        <button class="btn-paste" onclick="pasteFromClipboard(event)">PASTE</button>
      </div>
      <button class="btn-connect-launch" onclick="triggerJoinAction(event)">
        CONNECT TO STATION NOW &rarr;
      </button>
    </div>

  </div>

  <div class="footer-bar">
    <div class="network-pill">
      <div class="net-dot"></div>
      <span id="networkStatusText">Network: 127.0.0.1 (Ready)</span>
    </div>
    <div class="version-tag">GasStationCoop v1.0.0 Pro</div>
  </div>

  <div class="toast-alert" id="toastAlert">
    <svg class="toast-icon" viewBox="0 0 24 24">
      <path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41z"/>
    </svg>
    <span class="toast-text" id="toastMessage">IP Address Copied to Clipboard!</span>
  </div>

  <div class="launch-overlay" id="launchOverlay">
    <div class="radar-spinner"></div>
    <div class="overlay-title" id="overlayTitle">Initializing Co-op World...</div>
    <div class="overlay-subtitle" id="overlaySubtitle">Please wait while station connects</div>
  </div>

<script>
  let drawerOpen = false;
  let discoveredIp = null;

  function toggleJoinDrawer() {
    drawerOpen = !drawerOpen;
    const drawer = document.getElementById('joinDrawer');
    drawer.classList.toggle('active', drawerOpen);
    document.getElementById('joinChevron').innerHTML = drawerOpen ? '&#9652;' : '&#9662;';
    if (drawerOpen) {
      setTimeout(() => {
        const inp = document.getElementById('hostIpInput');
        inp.focus();
        inp.select();
        drawer.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
      }, 100);
    }
  }

  function showToast(msg) {
    const toast = document.getElementById('toastAlert');
    document.getElementById('toastMessage').innerText = msg;
    toast.classList.add('show');
    setTimeout(() => {
      toast.classList.remove('show');
    }, 3200);
  }

  function openGitHub() {
    if (window.pywebview && pywebview.api) {
      pywebview.api.open_github();
    } else {
      window.open('https://github.com/Nithinkumaru777/GasStationCoop', '_blank');
    }
  }

  function pasteFromClipboard(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    if (window.pywebview && pywebview.api && pywebview.api.read_clipboard) {
      pywebview.api.read_clipboard().then(txt => {
        if (txt && txt.trim()) {
          const clean = txt.trim();
          document.getElementById('hostIpInput').value = clean;
          showToast('PASTED IP: ' + clean);
        } else {
          showToast('Clipboard is empty or contains no text');
        }
      }).catch(() => {
        showToast('Could not read clipboard');
      });
    }
  }

  function triggerHostAction() {
    if (window.pywebview && pywebview.api) {
      pywebview.api.host_world().then(res => {
        showToast('HOST IP COPIED: ' + res.ip + ' (Ready to share!)');
        setTimeout(() => {
          document.getElementById('overlayTitle').innerText = 'Starting Co-op Host Server...';
          document.getElementById('overlaySubtitle').innerText = 'Your Host IP: ' + res.ip + ' (Copied to Clipboard)';
          document.getElementById('launchOverlay').classList.add('active');
        }, 500);
      });
    }
  }

  function triggerJoinAction(e) {
    if (e) {
      e.preventDefault();
      e.stopPropagation();
    }
    const targetIp = document.getElementById('hostIpInput').value.trim() || '127.0.0.1';
    if (window.pywebview && pywebview.api) {
      pywebview.api.join_world(targetIp).then(res => {
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

  // Allow pressing Enter key to immediately connect!
  document.getElementById('hostIpInput').addEventListener('keydown', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      triggerJoinAction(e);
    }
  });

  window.addEventListener('pywebviewready', () => {
    if (pywebview.api && pywebview.api.get_network_info) {
      pywebview.api.get_network_info().then(info => {
        if (info && info.primary_ip) {
          document.getElementById('networkStatusText').innerText = 'Network: ' + info.primary_ip + ' (Ready)';
        }
      });
    }

    // Auto-Discovery probe
    if (pywebview.api && pywebview.api.check_for_host) {
      pywebview.api.check_for_host().then(res => {
        if (res && res.found) {
          discoveredIp = res.ip;
          document.getElementById('discName').innerText = (res.name || 'Friend') + ' (' + res.ip + ')';
          document.getElementById('discBanner').classList.add('show');
          document.getElementById('hostIpInput').value = res.ip;
        }
      });
    }
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
        width=540,
        height=730,
        resizable=False,
        background_color="#060911"
    )
    api.set_window(window)
    webview.start()

if __name__ == "__main__":
    main()
