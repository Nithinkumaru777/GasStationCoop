"""Award-Winning In-Game Choice Dialog for Gas Station Simulator Co-op.
Built with Edge Chromium Webview2, High-Contrast Cyber Aesthetic.

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

CACHED_IPS = ["127.0.0.1"]
DISCOVERED_HOST = {"found": False, "ip": "", "name": ""}

def _bg_scan():
    global CACHED_IPS, DISCOVERED_HOST
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
        ds = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        ds.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        ds.settimeout(0.4)
        ds.sendto(b"GSS_DISCOVER", ("<broadcast>", 7777))
        ds.sendto(b"GSS_DISCOVER", ("127.0.0.1", 7777))
        data, addr = ds.recvfrom(1024)
        text = data.decode("utf-8", errors="replace")
        if text.startswith("GSS_OFFER:") or text.startswith("GSS_BEACON:"):
            parts = text.split(":", 2)
            name = parts[2] if len(parts) >= 3 else "Friend's Station"
            DISCOVERED_HOST = {"found": True, "ip": addr[0], "name": name}
        ds.close()
    except Exception:
        pass

threading.Thread(target=_bg_scan, daemon=True).start()

def safe_write_all(filenames, content):
    for fname in filenames:
        for base in [".", "net", "Mods/GasStationCoop"]:
            target = os.path.join(base, fname)
            try:
                d = os.path.dirname(target)
                if d:
                    os.makedirs(d, exist_ok=True)
                with open(target, "w", encoding="utf-8") as f:
                    f.write(content + "\n")
            except Exception:
                pass


class InGameMenuApi:
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

        safe_write_all(["role.txt"], "host")
        safe_write_all(["character.txt"], character)
        safe_write_all(["player_name.txt"], player_name)

        def do_close():
            time.sleep(0.8)
            if self.window:
                self.window.destroy()

        threading.Thread(target=do_close, daemon=True).start()
        return {"status": "ok", "ip": primary}

    def join_world(self, target_ip, character="delivery", player_name="Partner"):
        clean_ip = (target_ip or "").strip()
        if not clean_ip:
            clean_ip = "127.0.0.1"

        safe_write_all(["role.txt"], "guest")
        safe_write_all(["host_ip.txt"], clean_ip)
        safe_write_all(["character.txt"], character)
        safe_write_all(["player_name.txt"], player_name)

        def do_close():
            time.sleep(0.8)
            if self.window:
                self.window.destroy()

        threading.Thread(target=do_close, daemon=True).start()
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
<title>Gas Station Simulator Co-op Dialog</title>
<style>
  :root {
    --bg-base: #060911;
    --card-surface: rgba(15, 23, 42, 0.85);
    --card-border: rgba(255, 255, 255, 0.1);
    --amber-neon: #f59e0b;
    --amber-glow: rgba(245, 158, 11, 0.45);
    --cyan-neon: #06b6d4;
    --cyan-glow: rgba(6, 182, 212, 0.4);
    --text-primary: #f8fafc;
    --text-secondary: #94a3b8;
  }

  * { margin: 0; padding: 0; box-sizing: border-box; }

  body {
    background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #090d18 50%, #04060a 100%);
    font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
    color: var(--text-primary);
    min-height: 100vh;
    overflow-y: auto;
    display: flex; flex-direction: column;
    padding: 18px 20px;
    user-select: none;
    -webkit-user-select: none;
  }

  .hero-header { text-align: center; margin-bottom: 10px; }
  .shield-outer {
    width: 48px; height: 48px; margin: 0 auto 6px auto;
    background: linear-gradient(135deg, #1e293b, #0f172a);
    border: 2px solid var(--amber-neon); border-radius: 14px;
    display: flex; align-items: center; justify-content: center;
    box-shadow: 0 0 20px var(--amber-glow);
    font-size: 22px;
  }
  h1.main-title {
    font-size: 20px; font-weight: 800; letter-spacing: 1.2px;
    background: linear-gradient(180deg, #fff 0%, #cbd5e1 100%);
    -webkit-background-clip: text; -webkit-text-fill-color: transparent;
  }
  .sub-tagline {
    font-size: 9.5px; font-weight: 700; letter-spacing: 2px;
    color: var(--amber-neon); text-transform: uppercase; margin-top: 3px;
  }

  .creator-banner {
    display: flex; align-items: center; justify-content: space-between;
    background: rgba(30, 41, 59, 0.7); border: 1px solid var(--card-border);
    backdrop-filter: blur(12px); border-radius: 10px; padding: 7px 12px;
    margin-bottom: 12px;
  }
  .creator-info h4 { font-size: 10.5px; font-weight: 700; color: #fff; }
  .creator-info p { font-size: 9px; color: var(--amber-neon); font-weight: 600; }
  .github-btn {
    background: rgba(255,255,255,0.08); border: 1px solid rgba(255,255,255,0.16);
    color: #fff; padding: 4px 9px; border-radius: 6px; font-size: 9.5px;
    font-weight: 600; cursor: pointer; text-decoration: none;
  }

  .section-title {
    font-size: 10px; font-weight: 700; letter-spacing: 1.2px;
    text-transform: uppercase; color: #cbd5e1; margin-bottom: 6px;
  }

  .player-name-input {
    width: 100%; background: rgba(15, 23, 42, 0.85);
    border: 1px solid rgba(255, 255, 255, 0.15); border-radius: 8px;
    padding: 8px 12px; color: #fff; font-size: 11.5px; font-weight: 600;
    outline: none; margin-bottom: 10px;
  }
  .player-name-input:focus { border-color: var(--cyan-neon); }

  .char-grid {
    display: grid; grid-template-columns: repeat(4, 1fr); gap: 6px;
    margin-bottom: 12px;
  }
  .char-card {
    background: rgba(15, 23, 42, 0.7); border: 1px solid var(--card-border);
    border-radius: 8px; padding: 8px 4px; text-align: center; cursor: pointer;
    transition: all 0.2s;
  }
  .char-card:hover { border-color: #fff; }
  .char-card.selected {
    border-color: var(--amber-neon); background: rgba(245, 158, 11, 0.12);
    box-shadow: 0 0 14px var(--amber-glow);
  }
  .char-icon { font-size: 18px; margin-bottom: 2px; }
  .char-name { font-size: 9px; font-weight: 700; color: #fff; }

  .mode-cards { display: flex; flex-direction: column; gap: 10px; }
  .mode-card {
    background: var(--card-surface); border: 1px solid var(--card-border);
    border-radius: 12px; padding: 12px 14px;
  }
  .mode-title { font-size: 14.5px; font-weight: 800; color: #fff; margin-bottom: 2px; }
  .mode-desc { font-size: 10px; color: var(--text-secondary); margin-bottom: 8px; }

  .action-btn {
    width: 100%; padding: 10px 14px; border-radius: 8px;
    font-size: 11.5px; font-weight: 700; cursor: pointer; border: none;
    outline: none; transition: all 0.2s;
  }
  .btn-host { background: linear-gradient(135deg, #f59e0b, #d97706); color: #000; font-weight: 800; }
  .btn-join { background: linear-gradient(135deg, #06b6d4, #0284c7); color: #fff; }

  .ip-input-container { display: flex; gap: 6px; margin-bottom: 8px; }
  .ip-input {
    flex: 1; background: rgba(15, 23, 42, 0.95);
    border: 1px solid rgba(255, 255, 255, 0.16); border-radius: 7px;
    padding: 8px 10px; color: #fff; font-size: 12px; font-family: monospace;
    outline: none;
  }
  .paste-btn {
    background: rgba(255, 255, 255, 0.1); border: 1px solid rgba(255, 255, 255, 0.2);
    color: #fff; border-radius: 7px; padding: 0 10px; font-size: 10px;
    font-weight: 700; cursor: pointer;
  }

  .toast {
    position: fixed; bottom: 16px; left: 50%; transform: translateX(-50%) translateY(50px);
    background: #0f172a; border: 1px solid var(--amber-neon);
    color: #fff; padding: 7px 14px; border-radius: 20px; font-size: 10.5px;
    opacity: 0; pointer-events: none; transition: all 0.25s;
  }
  .toast.show { opacity: 1; transform: translateX(-50%) translateY(0); }
</style>
</head>
<body>

<div class="hero-header">
  <div class="shield-outer">⛽</div>
  <h1 class="main-title">GAS STATION SIMULATOR</h1>
  <div class="sub-tagline">CO-OP MULTIPLAYER SELECTION</div>
</div>

<div class="creator-banner">
  <div class="creator-info">
    <h4>Lead Architect: Nithin Kumar (@Nithinkumaru777)</h4>
    <p>Route 66 Co-op Synchronization Layer</p>
  </div>
  <button class="github-btn" onclick="openGitHub()">GitHub Repo →</button>
</div>

<div class="section-title">Your Player Name</div>
<input type="text" id="playerNameInput" class="player-name-input" value="Nithin" placeholder="Display name...">

<div class="section-title">Choose In-Game Character</div>
<div class="char-grid">
  <div class="char-card selected" id="char-biker" onclick="selectCharacter('biker')">
    <div class="char-icon">🏍️</div>
    <div class="char-name">Biker</div>
  </div>
  <div class="char-card" id="char-delivery" onclick="selectCharacter('delivery')">
    <div class="char-icon">⛽</div>
    <div class="char-name">Fuel Pro</div>
  </div>
  <div class="char-card" id="char-worker" onclick="selectCharacter('worker')">
    <div class="char-icon">🔧</div>
    <div class="char-name">Worker</div>
  </div>
  <div class="char-card" id="char-party" onclick="selectCharacter('party')">
    <div class="char-icon">👽</div>
    <div class="char-name">Alien Party</div>
  </div>
</div>

<div class="mode-cards">
  <div class="mode-card">
    <div class="mode-title">1. HOST A WORLD</div>
    <div class="mode-desc">Start hosting the station & automatically copies your IP.</div>
    <button class="action-btn btn-host" onclick="triggerHost()">START HOST SERVER</button>
  </div>

  <div class="mode-card">
    <div class="mode-title">2. JOIN A WORLD</div>
    <div class="mode-desc">Connect to your friend's station via IP address.</div>
    <div class="ip-input-container">
      <input type="text" id="hostIpInput" class="ip-input" placeholder="Friend's IP address...">
      <button class="paste-btn" onclick="pasteClip()">📋 Paste</button>
    </div>
    <button class="action-btn btn-join" onclick="triggerJoin()">CONNECT & ENTER</button>
  </div>
</div>

<div class="toast" id="toastMsg">✓ Notification</div>

<script>
  let selectedChar = 'biker';

  function selectCharacter(id) {
    selectedChar = id;
    document.querySelectorAll('.char-card').forEach(c => c.classList.remove('selected'));
    const t = document.getElementById('char-' + id);
    if (t) t.classList.add('selected');
    showToast('CHARACTER: ' + id.toUpperCase());
  }

  function showToast(msg) {
    const t = document.getElementById('toastMsg');
    t.innerText = msg;
    t.classList.add('show');
    setTimeout(() => t.classList.remove('show'), 2200);
  }

  function openGitHub() {
    if (window.pywebview && pywebview.api) pywebview.api.open_github();
  }

  async function pasteClip() {
    try {
      if (navigator.clipboard && navigator.clipboard.readText) {
        const txt = await navigator.clipboard.readText();
        if (txt && txt.trim()) {
          document.getElementById('hostIpInput').value = txt.trim();
          showToast('PASTED IP: ' + txt.trim());
          return;
        }
      }
    } catch (_) {}

    if (window.pywebview && pywebview.api && pywebview.api.read_clipboard) {
      pywebview.api.read_clipboard().then(txt => {
        if (txt && txt.trim()) {
          document.getElementById('hostIpInput').value = txt.trim();
          showToast('PASTED IP: ' + txt.trim());
        }
      });
    }
  }

  function triggerHost() {
    const name = document.getElementById('playerNameInput').value.trim() || 'Nithin';
    if (window.pywebview && pywebview.api) {
      pywebview.api.host_world(selectedChar, name).then(res => {
        showToast('HOST IP COPIED: ' + res.ip);
      });
    }
  }

  function triggerJoin() {
    const ip = document.getElementById('hostIpInput').value.trim() || '127.0.0.1';
    const name = document.getElementById('playerNameInput').value.trim() || 'Partner';
    if (window.pywebview && pywebview.api) {
      pywebview.api.join_world(ip, selectedChar, name).then(res => {
        showToast('CONNECTING TO: ' + res.connecting_to);
      });
    }
  }
</script>
</body>
</html>
"""

def main():
    api = InGameMenuApi()
    window = webview.create_window(
        title="Gas Station Simulator Co-op Dialog",
        html=HTML_UI,
        js_api=api,
        width=460,
        height=620,
        resizable=False,
        background_color="#060911"
    )
    api.set_window(window)
    webview.start()

if __name__ == "__main__":
    main()
