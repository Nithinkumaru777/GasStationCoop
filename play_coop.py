"""Clean, Silent 1-Click Co-op Launcher for Gas Station Simulator.
Runs with ZERO console windows.
Presents two clear options:
1. HOST A WORLD (Start station, copy IP to clipboard, launch game)
2. JOIN A WORLD (Enter friend's IP, launch game, connect from any Wi-Fi)
"""
import os
import sys
import socket
import subprocess

DIR_A = r"D:\coop-sandbox\gss\A\GSS2\Binaries\Win64"
EXE_PATH = os.path.join(DIR_A, "GSS2-Win64-Shipping.exe")
USER_DIR = r"D:\coop-sandbox\gss\userA"

CREATE_NO_WINDOW = 0x08000000

def get_network_ips():
    ips = []
    # 1. Primary LAN IP
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


def launch_game(role, target_ip="127.0.0.1"):
    # 1. Update role.txt
    for path in [
        os.path.join(DIR_A, "role.txt"),
        os.path.join(DIR_A, "net", "role.txt"),
        os.path.join(DIR_A, "Mods", "GasStationCoop", "role.txt")
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
            os.path.join(DIR_A, "host_ip.txt"),
            os.path.join(DIR_A, "net", "host_ip.txt")
        ]:
            try:
                with open(path, "w", encoding="utf-8") as f:
                    f.write(f"{target_ip}\n")
            except Exception:
                pass

    # 3. Launch silent background relay via pythonw
    relay_script = os.path.join(DIR_A, "gss_relay.py")
    if role == "host":
        subprocess.Popen(
            ["pythonw", relay_script, "--mode", "host", "--netdir", os.path.join(DIR_A, "net")],
            cwd=DIR_A,
            creationflags=CREATE_NO_WINDOW
        )
    else:
        subprocess.Popen(
            ["pythonw", relay_script, "--mode", "client", "--connect", target_ip, "--netdir", os.path.join(DIR_A, "net")],
            cwd=DIR_A,
            creationflags=CREATE_NO_WINDOW
        )

    # 4. Launch game windowed
    args = [
        EXE_PATH,
        "-windowed",
        "-ResX=1280",
        "-ResY=720",
        "-nosplash",
        "-saveddirsuffix=_coopA",
        f'-userdir="{USER_DIR}"'
    ]
    subprocess.Popen(args, cwd=DIR_A, creationflags=CREATE_NO_WINDOW)


def main():
    try:
        import tkinter as tk
        from tkinter import simpledialog, messagebox

        root = tk.Tk()
        root.title("Gas Station Simulator Co-op")
        root.geometry("480x320")
        root.resizable(False, False)
        root.attributes("-topmost", True)
        root.configure(bg="#1a1a24")
        root.eval('tk::PlaceWindow . center')

        title_lbl = tk.Label(
            root,
            text="GAS STATION SIMULATOR CO-OP",
            font=("Arial", 14, "bold"),
            fg="#ffb703",
            bg="#1a1a24"
        )
        title_lbl.pack(pady=(18, 4))

        subtitle_lbl = tk.Label(
            root,
            text="Choose your mode to start playing:",
            font=("Arial", 10),
            fg="#b0b0c0",
            bg="#1a1a24"
        )
        subtitle_lbl.pack(pady=(0, 16))

        btn_frame = tk.Frame(root, bg="#1a1a24")
        btn_frame.pack(fill=tk.BOTH, expand=True, padx=30)

        def on_host():
            all_ips = get_network_ips()
            ip_str = "  /  ".join(all_ips)
            # Copy primary IP to clipboard
            root.clipboard_clear()
            root.clipboard_append(all_ips[0])

            # Save my_ip.txt
            with open(os.path.join(DIR_A, "my_ip.txt"), "w", encoding="utf-8") as f:
                f.write("\n".join(all_ips))

            messagebox.showinfo(
                "Host World Ready",
                f"Your Co-op World is starting!\n\n"
                f"Your IP Address:\n>> {ip_str} <<\n\n"
                f"(Copied to clipboard automatically!)\n\n"
                f"Send this IP to your friend so they can join.",
                parent=root
            )
            root.destroy()
            launch_game("host")

        def on_join():
            saved_ip = "127.0.0.1"
            ip_file = os.path.join(DIR_A, "host_ip.txt")
            if os.path.exists(ip_file):
                try:
                    with open(ip_file, "r", encoding="utf-8") as f:
                        saved_ip = f.read().strip() or "127.0.0.1"
                except Exception:
                    pass

            target_ip = simpledialog.askstring(
                "Join Co-op World",
                "Enter your friend's Host IP address:\n\n"
                "* Same Wi-Fi: Local LAN IP (e.g. 192.168.1.15)\n"
                "* Different Wi-Fi: Radmin VPN or Tailscale IP",
                initialvalue=saved_ip,
                parent=root
            )

            if target_ip and target_ip.strip():
                clean_ip = target_ip.strip()
                root.destroy()
                launch_game("guest", clean_ip)

        # Button 1: HOST A WORLD
        host_btn = tk.Button(
            btn_frame,
            text="1. HOST A WORLD\nStart your station & invite friends (Copies your IP)",
            font=("Arial", 10, "bold"),
            bg="#2a9d8f",
            fg="white",
            activebackground="#21867a",
            activeforeground="white",
            cursor="hand2",
            height=3,
            command=on_host
        )
        host_btn.pack(fill=tk.X, pady=(0, 12))

        # Button 2: JOIN A WORLD
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

    except Exception as e:
        pass

if __name__ == "__main__":
    main()
