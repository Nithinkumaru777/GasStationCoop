"""2-Option In-Game Choice Dialog for Gas Station Simulator Co-op.
Presents two distinct choices:
1. HOST A WORLD (Start server, get IP for friends)
2. JOIN A WORLD (Connect to friend via IP from different Wi-Fi or LAN)
"""
import os
import sys
import socket
import subprocess

CREATE_NO_WINDOW = 0x08000000

def get_network_ips():
    ips = []
    # 1. Primary outbound LAN IP
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        primary = s.getsockname()[0]
        s.close()
        if primary and not primary.startswith("127."):
            ips.append(primary)
    except Exception:
        pass

    # 2. Radmin VPN / Tailscale / virtual adapter IPs via ipconfig
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


def run_coop_menu():
    try:
        import tkinter as tk
        from tkinter import ttk, messagebox, simpledialog

        root = tk.Tk()
        root.title("Gas Station Simulator Co-op")
        root.geometry("460x280")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#1e1e24")

        # Center on screen
        root.eval('tk::PlaceWindow . center')

        title_lbl = tk.Label(root, text="GAS STATION CO-OP", font=("Arial", 15, "bold"), fg="#ffb703", bg="#1e1e24")
        title_lbl.pack(pady=(15, 4))

        subtitle_lbl = tk.Label(root, text="Choose how you want to play:", font=("Arial", 10), fg="#e0e0e0", bg="#1e1e24")
        subtitle_lbl.pack(pady=(0, 15))

        btn_frame = tk.Frame(root, bg="#1e1e24")
        btn_frame.pack(fill=tk.BOTH, expand=True, padx=25)

        chosen_action = [None]

        def on_host():
            chosen_action[0] = "host"
            all_ips = get_network_ips()
            ip_str = "  /  ".join(all_ips)
            # Copy first IP to clipboard
            root.clipboard_clear()
            root.clipboard_append(all_ips[0])
            with open("role.txt", "w", encoding="utf-8") as f:
                f.write("host\n")
            with open("net/role.txt", "w", encoding="utf-8") as f:
                f.write("host\n")
            with open("my_ip.txt", "w", encoding="utf-8") as f:
                f.write("\n".join(all_ips))
            messagebox.showinfo(
                "Host World Started!",
                f"Your Co-op World is starting!\n\n"
                f"Your IP Address:\n>> {ip_str} <<\n\n"
                f"The IP has been COPIED to your clipboard!\n"
                f"Send it to your friend so they can join from any Wi-Fi.",
                parent=root
            )
            root.destroy()

        def on_join():
            saved_ip = "127.0.0.1"
            if os.path.exists("host_ip.txt"):
                try:
                    with open("host_ip.txt", "r", encoding="utf-8") as f:
                        saved_ip = f.read().strip() or "127.0.0.1"
                except Exception:
                    pass

            target_ip = simpledialog.askstring(
                "Join Co-op World",
                "Enter your friend's Host IP address:\n\n"
                "* Same Wi-Fi: Local LAN IP (e.g. 192.168.1.x)\n"
                "* Different Wi-Fi: Radmin VPN or Tailscale IP",
                initialvalue=saved_ip,
                parent=root
            )

            if target_ip and target_ip.strip():
                clean_ip = target_ip.strip()
                with open("role.txt", "w", encoding="utf-8") as f:
                    f.write("guest\n")
                with open("net/role.txt", "w", encoding="utf-8") as f:
                    f.write("guest\n")
                with open("host_ip.txt", "w", encoding="utf-8") as f:
                    f.write(clean_ip)
                with open("net/host_ip.txt", "w", encoding="utf-8") as f:
                    f.write(clean_ip)
                chosen_action[0] = f"join:{clean_ip}"
                root.destroy()

        # Option 1: HOST A WORLD Button
        host_btn = tk.Button(
            btn_frame,
            text="1. HOST A WORLD\nStart your station & invite friends",
            font=("Arial", 10, "bold"),
            bg="#2a9d8f",
            fg="white",
            activebackground="#21867a",
            activeforeground="white",
            cursor="hand2",
            height=3,
            command=on_host
        )
        host_btn.pack(fill=tk.X, pady=(0, 10))

        # Option 2: JOIN A WORLD Button
        join_btn = tk.Button(
            btn_frame,
            text="2. JOIN A WORLD\nConnect to friend via IP (Any Wi-Fi / LAN)",
            font=("Arial", 10, "bold"),
            bg="#e76f51",
            fg="white",
            activebackground="#cf583b",
            activeforeground="white",
            cursor="hand2",
            height=3,
            command=on_join
        )
        join_btn.pack(fill=tk.X)

        root.mainloop()
        return chosen_action[0]

    except Exception as e:
        return None

if __name__ == "__main__":
    action = run_coop_menu()
