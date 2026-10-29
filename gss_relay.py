"""Gas Station Simulator Co-op Python Network Relay & State Broker
Features:
  - Minecraft-style LAN Auto-Discovery (zero-configuration, automatic host detection)
  - 60 Hz zero-drop player position & rotation streaming
  - Real-time event broker for shared wallet, trash cleaning, fueling & register locks
Zero third-party dependencies — uses standard Python library only.
"""
import os
import sys
import time
import socket
import threading
import argparse

DEFAULT_PORT = 7777
DIR_A_DEFAULT = r"D:\coop-sandbox\gss\A\GSS2\Binaries\Win64\net"
DIR_B_DEFAULT = r"D:\coop-sandbox\gss\B\GSS2\Binaries\Win64\net"

def get_local_ip():
    """Returns local LAN IP for reference."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"

def atomic_write(filepath, content_bytes):
    """Atomic file write (.tmp + replace) so UE4SS Lua never reads half-written lines."""
    tmp_path = filepath + ".tmp"
    try:
        with open(tmp_path, "wb") as f:
            f.write(content_bytes)
        if os.path.exists(filepath):
            os.replace(tmp_path, filepath)
        else:
            os.rename(tmp_path, filepath)
    except Exception:
        pass

class NetworkRelayHost:
    def __init__(self, netdir, port=DEFAULT_PORT):
        self.netdir = netdir
        self.port = port
        os.makedirs(self.netdir, exist_ok=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.setblocking(False)
        self.client_addr = None
        self.running = True

    def start(self):
        local_ip = get_local_ip()
        print("=" * 60)
        print("  ⛽ GAS STATION SIMULATOR CO-OP RELAY [HOST / SERVER]")
        print("=" * 60)
        print(f"  Listening on:     0.0.0.0:{self.port} (UDP)")
        print(f"  Local IP:         {local_ip}")
        print(f"  LAN Discovery:    ACTIVE (Minecraft-Style Auto-Detect)")
        print(f"  Net Directory:    {self.netdir}")
        print("-" * 60)
        print("  Your friend's game will automatically detect you on LAN!")
        print("  (Or if playing over Internet via Radmin/Tailscale, share your VPN IP)")
        print("=" * 60)
        print("[HOST] Server is live. Waiting for friend to join...\n")

        # Start beacon broadcaster thread (every 1.5 seconds)
        t_beacon = threading.Thread(target=self._beacon_loop, daemon=True)
        t_beacon.start()

        # Start receive thread
        t_recv = threading.Thread(target=self._recv_loop, daemon=True)
        t_recv.start()

        # Send loop (60 Hz)
        local_state_file = os.path.join(self.netdir, "local_player.state")
        events_out_file = os.path.join(self.netdir, "events.out")
        last_mtime = 0
        last_heartbeat = 0

        try:
            while self.running:
                now = time.time()
                if self.client_addr:
                    # Stream player transform
                    if os.path.exists(local_state_file):
                        try:
                            mtime = os.path.getmtime(local_state_file)
                            if mtime != last_mtime or (now - last_heartbeat > 0.05):
                                with open(local_state_file, "rb") as f:
                                    st_bytes = f.read().strip()
                                if st_bytes:
                                    self.sock.sendto(b"POS:" + st_bytes, self.client_addr)
                                last_mtime = mtime
                                last_heartbeat = now
                        except Exception:
                            pass

                    # Stream outgoing events
                    if os.path.exists(events_out_file):
                        try:
                            with open(events_out_file, "r") as f:
                                lines = f.read()
                            os.remove(events_out_file)
                            for line in lines.splitlines():
                                line = line.strip()
                                if line:
                                    self.sock.sendto(b"EVT:" + line.encode("utf-8"), self.client_addr)
                        except Exception:
                            pass

                time.sleep(0.016)
        except KeyboardInterrupt:
            print("\n[HOST] Relay stopped.")

    def _beacon_loop(self):
        """Broadcasts presence beacon so clients can auto-detect on LAN."""
        beacon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        beacon_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        beacon_msg = f"GSS_BEACON:{self.port}".encode("ascii")

        while self.running:
            try:
                beacon_sock.sendto(beacon_msg, ("<broadcast>", self.port))
            except Exception:
                pass
            time.sleep(1.5)

    def _recv_loop(self):
        remote_state_file = os.path.join(self.netdir, "remote_player.state")
        events_in_file = os.path.join(self.netdir, "events.in")

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if not data:
                    continue

                # Handle Minecraft-style LAN discovery probe
                if data == b"GSS_DISCOVER":
                    offer = f"GSS_OFFER:{self.port}".encode("ascii")
                    self.sock.sendto(offer, addr)
                    print(f"[AUTO-DISCOVERY] Responded to discovery probe from {addr[0]}!")
                    continue

                if self.client_addr != addr:
                    self.client_addr = addr
                    print(f"\n[HOST] ✨ >>> FRIEND CONNECTED FROM {addr[0]}:{addr[1]}! <<<")
                    print("[HOST] Co-op state streaming is active!\n")

                if data.startswith(b"PING"):
                    self.sock.sendto(b"PONG", addr)
                elif data.startswith(b"POS:"):
                    pos_bytes = data[4:]
                    atomic_write(remote_state_file, pos_bytes)
                elif data.startswith(b"EVT:"):
                    evt_str = data[4:].decode("utf-8", errors="replace") + "\n"
                    with open(events_in_file, "a") as f:
                        f.write(evt_str)
            except BlockingIOError:
                time.sleep(0.005)
            except Exception:
                pass


class NetworkRelayClient:
    def __init__(self, host_ip, netdir, port=DEFAULT_PORT):
        self.host_addr = (host_ip, port)
        self.netdir = netdir
        os.makedirs(self.netdir, exist_ok=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.running = True
        self.connected = False

    @staticmethod
    def auto_discover_host(timeout=2.5, port=DEFAULT_PORT):
        """Probes local network for active Host server via UDP broadcast."""
        print(f"[AUTO-DETECT] Searching for Gas Station Simulator Host on network...")
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.5)

        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                # Send probe
                s.sendto(b"GSS_DISCOVER", ("<broadcast>", port))
            except Exception:
                pass

            # Listen for reply or beacon
            listen_end = time.time() + 0.5
            while time.time() < listen_end:
                try:
                    data, addr = s.recvfrom(1024)
                    if data.startswith(b"GSS_OFFER:") or data.startswith(b"GSS_BEACON:"):
                        host_ip = addr[0]
                        s.close()
                        return host_ip
                except socket.timeout:
                    break
                except Exception:
                    pass
            time.sleep(0.1)

        s.close()
        return None

    def start(self):
        print("=" * 60)
        print("  ⛽ GAS STATION SIMULATOR CO-OP RELAY [CLIENT / GUEST]")
        print("=" * 60)
        print(f"  Connected to Host:  {self.host_addr[0]}:{self.host_addr[1]} (UDP)")
        print(f"  Net Directory:      {self.netdir}")
        print("=" * 60)
        print(f"[CLIENT] Connecting to host at {self.host_addr[0]}...")

        # Receive thread
        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()

        local_state_file = os.path.join(self.netdir, "local_player.state")
        events_out_file = os.path.join(self.netdir, "events.out")
        last_mtime = 0
        last_ping = 0
        last_heartbeat = 0

        try:
            while self.running:
                now = time.time()
                # Send heartbeat ping every 2s
                if now - last_ping > 2.0:
                    try:
                        self.sock.sendto(b"PING", self.host_addr)
                    except Exception:
                        pass
                    last_ping = now

                # Stream local player position
                if os.path.exists(local_state_file):
                    try:
                        mtime = os.path.getmtime(local_state_file)
                        if mtime != last_mtime or (now - last_heartbeat > 0.05):
                            with open(local_state_file, "rb") as f:
                                st_bytes = f.read().strip()
                            if st_bytes:
                                self.sock.sendto(b"POS:" + st_bytes, self.host_addr)
                            last_mtime = mtime
                            last_heartbeat = now
                    except Exception:
                        pass

                # Stream outgoing events
                if os.path.exists(events_out_file):
                    try:
                        with open(events_out_file, "r") as f:
                            lines = f.read()
                        os.remove(events_out_file)
                        for line in lines.splitlines():
                            line = line.strip()
                            if line:
                                self.sock.sendto(b"EVT:" + line.encode("utf-8"), self.host_addr)
                    except Exception:
                        pass

                time.sleep(0.016)
        except KeyboardInterrupt:
            print("\n[CLIENT] Relay stopped.")

    def _recv_loop(self):
        remote_state_file = os.path.join(self.netdir, "remote_player.state")
        events_in_file = os.path.join(self.netdir, "events.in")

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if not data:
                    continue

                if not self.connected:
                    self.connected = True
                    print(f"\n[CLIENT] ✨ >>> CONNECTED TO HOST ({addr[0]}:{addr[1]})! <<<")
                    print("[CLIENT] Co-op state streaming is active!\n")

                if data == b"PONG":
                    if not self.connected:
                        self.connected = True
                        print(f"\n[CLIENT] ✨ >>> CONNECTED TO HOST! Handshake OK <<<")
                elif data.startswith(b"POS:"):
                    pos_bytes = data[4:]
                    atomic_write(remote_state_file, pos_bytes)
                elif data.startswith(b"EVT:"):
                    evt_str = data[4:].decode("utf-8", errors="replace") + "\n"
                    with open(events_in_file, "a") as f:
                        f.write(evt_str)
            except BlockingIOError:
                time.sleep(0.005)
            except Exception:
                pass


class LocalSandboxBroker:
    def __init__(self, dir_a=DIR_A_DEFAULT, dir_b=DIR_B_DEFAULT):
        self.dir_a = dir_a
        self.dir_b = dir_b
        os.makedirs(self.dir_a, exist_ok=True)
        os.makedirs(self.dir_b, exist_ok=True)
        self.running = True

    def start(self):
        print("Gas Station Simulator Co-op Relay running (Direct Local Sandbox Broker)...")
        file_a_to_b = os.path.join(self.dir_a, "local_player.state")
        file_b_remote = os.path.join(self.dir_b, "remote_player.state")
        file_b_to_a = os.path.join(self.dir_b, "local_player.state")
        file_a_remote = os.path.join(self.dir_a, "remote_player.state")

        events_a = os.path.join(self.dir_a, "events.out")
        events_b_in = os.path.join(self.dir_b, "events.in")
        events_b = os.path.join(self.dir_b, "events.out")
        events_a_in = os.path.join(self.dir_a, "events.in")

        last_a_mtime = 0
        last_b_mtime = 0

        try:
            while self.running:
                try:
                    if os.path.exists(file_a_to_b):
                        mtime = os.path.getmtime(file_a_to_b)
                        if mtime != last_a_mtime:
                            with open(file_a_to_b, "rb") as fa:
                                data = fa.read()
                            atomic_write(file_b_remote, data)
                            last_a_mtime = mtime

                    if os.path.exists(file_b_to_a):
                        mtime = os.path.getmtime(file_b_to_a)
                        if mtime != last_b_mtime:
                            with open(file_b_to_a, "rb") as fb:
                                data = fb.read()
                            atomic_write(file_a_remote, data)
                            last_b_mtime = mtime

                    if os.path.exists(events_a):
                        with open(events_a, "r") as fa:
                            evs = fa.read()
                        os.remove(events_a)
                        with open(events_b_in, "a") as fb:
                            fb.write(evs)

                    if os.path.exists(events_b):
                        with open(events_b, "r") as fb:
                            evs = fb.read()
                        os.remove(events_b)
                        with open(events_a_in, "a") as fa:
                            fa.write(evs)
                except Exception:
                    pass

                time.sleep(0.016)
        except KeyboardInterrupt:
            print("\nRelay stopped.")


def main():
    parser = argparse.ArgumentParser(description="Gas Station Simulator Co-op Network Relay")
    parser.add_argument("--mode", choices=["host", "client", "local", "auto"], default="auto",
                        help="Relay mode: host, client, local (twin sandboxes), or auto (auto-detect host on LAN)")
    parser.add_argument("--connect", default="", help="Host IP to connect to (client mode)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="UDP port (default: 7777)")
    parser.add_argument("--netdir", default="", help="Path to local game 'net' directory")

    args = parser.parse_args()

    # Auto-resolve netdir if not specified
    netdir = args.netdir
    if not netdir:
        if os.path.isdir("net"):
            netdir = os.path.abspath("net")
        elif os.path.isdir(DIR_A_DEFAULT) and args.mode == "host":
            netdir = DIR_A_DEFAULT
        elif os.path.isdir(DIR_B_DEFAULT) and args.mode in ("client", "auto"):
            netdir = DIR_B_DEFAULT
        else:
            netdir = os.path.abspath("net")

    if args.mode == "host":
        relay = NetworkRelayHost(netdir=netdir, port=args.port)
        relay.start()

    elif args.mode in ("client", "auto"):
        target_ip = args.connect.strip()

        # If no IP provided, perform Minecraft-style LAN Auto-Discovery!
        if not target_ip:
            discovered = NetworkRelayClient.auto_discover_host(timeout=2.5, port=args.port)
            if discovered:
                print(f"\n============================================================")
                print(f"  ✨ [AUTO-DETECT SUCCESS] Found Host Server at: {discovered}")
                print(f"  Connecting automatically (Like Minecraft LAN)...")
                print(f"============================================================\n")
                target_ip = discovered
            else:
                print(f"[AUTO-DETECT] No Host found on local LAN within 2.5 seconds.")
                # Check saved IP in host_ip.txt
                saved_ip = ""
                if os.path.exists("host_ip.txt"):
                    try:
                        with open("host_ip.txt", "r") as f:
                            saved_ip = f.read().strip()
                    except Exception:
                        pass

                prompt = f"Enter Host IP [{saved_ip}]: " if saved_ip else "Enter Host IP: "
                user_input = input(prompt).strip()
                target_ip = user_input or saved_ip

                if not target_ip:
                    print("[ERROR] No Host IP provided. Exiting.")
                    sys.exit(1)

        # Save verified IP
        try:
            with open("host_ip.txt", "w") as f:
                f.write(target_ip)
        except Exception:
            pass

        relay = NetworkRelayClient(host_ip=target_ip, netdir=netdir, port=args.port)
        relay.start()

    else:
        broker = LocalSandboxBroker()
        broker.start()


if __name__ == "__main__":
    main()
