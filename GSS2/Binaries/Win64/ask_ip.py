"""Quick non-blocking IP input dialog for Gas Station Co-op.
Allows joining from different Wi-Fi networks (Radmin VPN, Tailscale, Public IP, or LAN).
"""
import os
import sys

def prompt_ip():
    saved_ip = "127.0.0.1"
    ip_file = "host_ip.txt"
    if os.path.exists(ip_file):
        try:
            with open(ip_file, "r") as f:
                content = f.read().strip()
                if content:
                    saved_ip = content
        except Exception:
            pass

    # Check server_info.txt for auto-detected IP fallback
    if saved_ip == "127.0.0.1" and os.path.exists("net/server_info.txt"):
        try:
            with open("net/server_info.txt", "r") as f:
                for line in f:
                    if line.startswith("IP=") and len(line.strip()) > 3:
                        found_ip = line.split("=", 1)[1].strip()
                        if found_ip:
                            saved_ip = found_ip
        except Exception:
            pass

    try:
        import tkinter as tk
        from tkinter import simpledialog

        root = tk.Tk()
        root.withdraw()
        root.attributes("-topmost", True)

        prompt_msg = (
            "Enter Friend's Host IP Address:\n\n"
            "• Same Wi-Fi: Use local IP (e.g. 192.168.1.x)\n"
            "• Different Wi-Fi: Use Radmin VPN IP (e.g. 26.x.x.x) or Tailscale IP"
        )
        user_ip = simpledialog.askstring("Join Gas Station Co-op World", prompt_msg, initialvalue=saved_ip, parent=root)
        root.destroy()

        if user_ip and user_ip.strip():
            final_ip = user_ip.strip()
            with open(ip_file, "w") as f:
                f.write(final_ip)
            with open("net/host_ip.txt", "w") as f:
                f.write(final_ip)
            print(f"[IP_PROMPT] Saved Host IP: {final_ip}")
            return final_ip
        else:
            print(f"[IP_PROMPT] Cancelled; keeping {saved_ip}")
            return saved_ip
    except Exception as e:
        print(f"[IP_PROMPT] Error: {e}")
        return saved_ip

if __name__ == "__main__":
    prompt_ip()
