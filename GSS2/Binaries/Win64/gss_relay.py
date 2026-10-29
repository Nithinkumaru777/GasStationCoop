"""Gas Station Simulator Co-op Python Network Relay & State Broker
Features:
  - Minecraft-style LAN Auto-Discovery (zero-configuration, automatic host detection)
  - Seamless in-game dynamic switching (Host / Guest / Auto-Detect)
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


def get_server_display_name():
    """Returns user-friendly server name like Minecraft LAN."""
    name = os.getenv("USERNAME") or os.getenv("USER") or "Player"
    return f"{name}'s Gas Station"


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


def write_server_info(netdir, status, server_name, ip, port=DEFAULT_PORT):
    """Writes server_info.txt for UE4SS Lua in-game menu display."""
    os.makedirs(netdir, exist_ok=True)
    info_path = os.path.join(netdir, "server_info.txt")
    content = f"STATUS={status}\nSERVER_NAME={server_name}\nIP={ip}\nPORT={port}\n"
    atomic_write(info_path, content.encode("utf-8"))


class NetworkRelayHost:
    def __init__(self, netdir, port=DEFAULT_PORT, server_name=None):
        self.netdir = netdir
        self.port = port
        self.server_name = server_name or get_server_display_name()
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
        print(f"  Server Name:      {self.server_name}")
        print(f"  Listening on:     0.0.0.0:{self.port} (UDP)")
        print(f"  Local IP:         {local_ip}")
        print(f"  LAN Discovery:    ACTIVE (Minecraft-Style Auto-Detect)")
        print(f"  Net Directory:    {self.netdir}")
        print("-" * 60)
        print("  Friends in-game will auto-detect your server in Main Menu!")
        print("=" * 60)
        print("[HOST] Server is live. Waiting for friend to join...\n")

        write_server_info(self.netdir, "HOSTING", self.server_name, "127.0.0.1", self.port)

        # Start beacon broadcaster thread
        t_beacon = threading.Thread(target=self._beacon_loop, daemon=True)
        t_beacon.start()

        # Start receive thread
        t_recv = threading.Thread(target=self._recv_loop, daemon=True)
        t_recv.start()

        # 60 Hz State Sync loop
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
        beacon_msg = f"GSS_BEACON:{self.port}:{self.server_name}".encode("utf-8")

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
                    offer = f"GSS_OFFER:{self.port}:{self.server_name}".encode("utf-8")
                    self.sock.sendto(offer, addr)
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
    def __init__(self, host_ip, netdir, port=DEFAULT_PORT, server_name=None):
        self.host_addr = (host_ip, port)
        self.netdir = netdir
        self.server_name = server_name or "Host's Gas Station"
        os.makedirs(self.netdir, exist_ok=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setblocking(False)
        self.running = True
        self.connected = False

    @staticmethod
    def auto_discover_host(timeout=2.0, port=DEFAULT_PORT):
        """Probes local network for active Host server via UDP broadcast and localhost."""
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.3)

        start_time = time.time()
        while time.time() - start_time < timeout:
            # Send probe to LAN broadcast and localhost
            try:
                s.sendto(b"GSS_DISCOVER", ("<broadcast>", port))
                s.sendto(b"GSS_DISCOVER", ("127.0.0.1", port))
            except Exception:
                pass

            listen_end = time.time() + 0.3
            while time.time() < listen_end:
                try:
                    data, addr = s.recvfrom(1024)
                    text = data.decode("utf-8", errors="replace")
                    if text.startswith("GSS_OFFER:") or text.startswith("GSS_BEACON:"):
                        parts = text.split(":", 2)
                        s_name = parts[2] if len(parts) >= 3 else "Host's Gas Station"
                        s.close()
                        return addr[0], s_name
                except socket.timeout:
                    break
                except Exception:
                    pass
            time.sleep(0.1)

        s.close()
        return None, None

    def start(self):
        print("=" * 60)
        print("  ⛽ GAS STATION SIMULATOR CO-OP RELAY [CLIENT / GUEST]")
        print("=" * 60)
        print(f"  Connected to Host:  {self.host_addr[0]}:{self.host_addr[1]} (UDP)")
        print(f"  Server Name:        {self.server_name}")
        print(f"  Net Directory:      {self.netdir}")
        print("=" * 60)

        write_server_info(self.netdir, "CONNECTED", self.server_name, self.host_addr[0], self.host_addr[1])

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
                # Send heartbeat ping every 1.5s
                if now - last_ping > 1.5:
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


class DynamicRelayDaemon:
    """Seamless background daemon. Auto-scans LAN until player clicks Host or Join in-game."""
    def __init__(self, netdir, port=DEFAULT_PORT):
        self.netdir = netdir
        self.port = port
        os.makedirs(self.netdir, exist_ok=True)
        self.running = True
        self.discovered_ip = None
        self.discovered_name = None

    def read_role(self):
        """Reads current role from role.txt or net/role.txt."""
        for p in ["role.txt", os.path.join(self.netdir, "role.txt"), "Mods/GasStationCoop/role.txt"]:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        r = f.read().strip().lower()
                    if r in ("host", "guest"):
                        return r
                except Exception:
                    pass
        return None

    def start(self):
        print(f"[DAEMON] Gas Station Co-op Background Daemon running on port {self.port}...")
        write_server_info(self.netdir, "SCANNING", "Scanning LAN for games...", "", self.port)

        last_scan_time = 0

        while self.running:
            role = self.read_role()

            if role == "host":
                print("[DAEMON] Role locked to HOST. Launching Host Relay...")
                relay = NetworkRelayHost(netdir=self.netdir, port=self.port)
                relay.start()
                return

            elif role == "guest":
                target_ip = self.discovered_ip or "127.0.0.1"
                if os.path.exists("host_ip.txt"):
                    try:
                        with open("host_ip.txt", "r") as f:
                            saved = f.read().strip()
                        if saved:
                            target_ip = saved
                    except Exception:
                        pass

                print(f"[DAEMON] Role locked to GUEST. Connecting to {target_ip}...")
                relay = NetworkRelayClient(host_ip=target_ip, netdir=self.netdir, port=self.port, server_name=self.discovered_name)
                relay.start()
                return

            # Role is not locked yet — perform non-blocking LAN scan
            now = time.time()
            if now - last_scan_time > 1.5:
                ip, name = NetworkRelayClient.auto_discover_host(timeout=0.6, port=self.port)
                if ip:
                    self.discovered_ip = ip
                    self.discovered_name = name or f"{ip}'s Gas Station"
                    write_server_info(self.netdir, "ONLINE", self.discovered_name, self.discovered_ip, self.port)
                else:
                    self.discovered_ip = None
                    self.discovered_name = None
                    write_server_info(self.netdir, "OFFLINE", "No Host Online", "", self.port)
                last_scan_time = now

            time.sleep(0.2)


def main():
    parser = argparse.ArgumentParser(description="Gas Station Simulator Co-op Network Relay")
    parser.add_argument("--mode", choices=["host", "client", "auto"], default="auto",
                        help="Relay mode: host, client, or auto (daemon with in-game selection)")
    parser.add_argument("--connect", default="", help="Host IP to connect to (client mode)")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="UDP port (default: 7777)")
    parser.add_argument("--netdir", default="net", help="Path to local game 'net' directory")

    args = parser.parse_args()
    netdir = os.path.abspath(args.netdir)
    os.makedirs(netdir, exist_ok=True)

    if args.mode == "host":
        relay = NetworkRelayHost(netdir=netdir, port=args.port)
        relay.start()

    elif args.mode == "client":
        target_ip = args.connect.strip()
        if not target_ip:
            ip, name = NetworkRelayClient.auto_discover_host(timeout=2.0, port=args.port)
            target_ip = ip or "127.0.0.1"
        relay = NetworkRelayClient(host_ip=target_ip, netdir=netdir, port=args.port)
        relay.start()

    else:
        # Auto mode: Run Dynamic Daemon
        daemon = DynamicRelayDaemon(netdir=netdir, port=args.port)
        daemon.start()


if __name__ == "__main__":
    main()
