"""Gas Station Simulator Co-op Network Relay & State Broker.
Runs silently in background with ZERO console clutter.
Handles UDP state replication, peer handshake, character selection sync, and heartbeat.

Lead Architect & Creator: Nithin Kumar (@Nithinkumaru777)
Repository: https://github.com/Nithinkumaru777/GasStationCoop
"""
import os
import sys
import time
import socket
import threading
import argparse

DEFAULT_PORT = 7777

def is_port_in_use(port=DEFAULT_PORT):
    """Check if relay is already running on this port to prevent duplicate instances."""
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("0.0.0.0", port))
        s.close()
        return False
    except Exception:
        return True


def get_local_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        ip = s.getsockname()[0]
        s.close()
        return ip
    except Exception:
        return "127.0.0.1"


def get_profile(netdir, default_name="Player", default_char="biker"):
    name = default_name
    char = default_char
    try:
        np = os.path.join(netdir, "player_name.txt")
        if os.path.exists(np):
            with open(np, "r", encoding="utf-8") as f:
                c = f.read().strip()
                if c:
                    name = c
        cp = os.path.join(netdir, "character.txt")
        if os.path.exists(cp):
            with open(cp, "r", encoding="utf-8") as f:
                c = f.read().strip().lower()
                if c:
                    char = c
    except Exception:
        pass
    return name, char


def atomic_write(filepath, content_bytes):
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


def write_peer_state(netdir, connected, role, ip, name, char_id):
    os.makedirs(netdir, exist_ok=True)
    state_file = os.path.join(netdir, "peer.state")
    content = (
        f"CONNECTED={'1' if connected else '0'}\n"
        f"ROLE={role}\n"
        f"IP={ip}\n"
        f"NAME={name}\n"
        f"CHAR={char_id}\n"
        f"TIMESTAMP={time.time():.2f}\n"
    )
    atomic_write(state_file, content.encode("utf-8"))

    if connected and char_id:
        atomic_write(os.path.join(netdir, "remote_character.txt"), char_id.encode("utf-8"))
    if connected and name:
        atomic_write(os.path.join(netdir, "remote_name.txt"), name.encode("utf-8"))


class NetworkRelayHost:
    def __init__(self, netdir, port=DEFAULT_PORT, server_name=None):
        self.netdir = netdir
        self.port = port
        self.server_name = server_name or (os.getenv("USERNAME") or "Nithin")
        os.makedirs(self.netdir, exist_ok=True)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x10)
        except Exception:
            pass
        self.sock.bind(("0.0.0.0", self.port))
        self.sock.setblocking(False)
        self.client_addr = None
        self.peer_name = "Partner"
        self.peer_char = "delivery"
        self.last_peer_packet = 0
        self.running = True

    def start(self):
        local_name, local_char = get_profile(self.netdir, default_name="Nithin", default_char="biker")
        write_peer_state(self.netdir, False, "guest", "", "", "")

        t_beacon = threading.Thread(target=self._beacon_loop, daemon=True)
        t_beacon.start()

        t_recv = threading.Thread(target=self._recv_loop, daemon=True)
        t_recv.start()

        local_state_file = os.path.join(self.netdir, "local_player.state")
        events_out_file = os.path.join(self.netdir, "events.out")
        last_mtime = 0
        last_heartbeat = 0
        last_profile_sync = 0

        try:
            while self.running:
                now = time.time()
                is_connected = self.client_addr is not None and (now - self.last_peer_packet < 5.0)

                # Periodic profile check and sync
                if now - last_profile_sync > 1.0:
                    local_name, local_char = get_profile(self.netdir, default_name="Nithin", default_char="biker")
                    if self.client_addr:
                        sync_pkt = f"CHAR:{local_char}:{local_name}".encode("utf-8")
                        try:
                            self.sock.sendto(sync_pkt, self.client_addr)
                        except Exception:
                            pass
                    last_profile_sync = now

                # Stream local player position at 20 Hz
                if is_connected:
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

                    # Stream game interaction events
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
        except Exception:
            pass

    def _beacon_loop(self):
        beacon_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        beacon_sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        beacon_msg = f"GSS_BEACON:{self.port}:{self.server_name}".encode("utf-8")

        while self.running:
            try:
                beacon_sock.sendto(beacon_msg, ("<broadcast>", self.port))
            except Exception:
                pass
            time.sleep(2.0)

    def _recv_loop(self):
        remote_state_file = os.path.join(self.netdir, "remote_player.state")
        events_in_file = os.path.join(self.netdir, "events.in")

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if not data:
                    continue

                if data == b"GSS_DISCOVER":
                    offer = f"GSS_OFFER:{self.port}:{self.server_name}".encode("utf-8")
                    self.sock.sendto(offer, addr)
                    continue

                self.client_addr = addr
                self.last_peer_packet = time.time()

                if data.startswith(b"HELLO:"):
                    # Handshake: HELLO:name:char
                    parts = data.decode("utf-8", errors="replace").split(":", 2)
                    if len(parts) >= 2 and parts[1]:
                        self.peer_name = parts[1]
                    if len(parts) >= 3 and parts[2]:
                        self.peer_char = parts[2]
                    write_peer_state(self.netdir, True, "guest", addr[0], self.peer_name, self.peer_char)

                    # Reply with WELCOME:host_name:host_char
                    loc_name, loc_char = get_profile(self.netdir, default_name="Nithin", default_char="biker")
                    resp = f"WELCOME:{loc_name}:{loc_char}".encode("utf-8")
                    self.sock.sendto(resp, addr)

                elif data.startswith(b"CHAR:"):
                    parts = data.decode("utf-8", errors="replace").split(":", 2)
                    if len(parts) >= 2 and parts[1]:
                        self.peer_char = parts[1]
                    if len(parts) >= 3 and parts[2]:
                        self.peer_name = parts[2]
                    write_peer_state(self.netdir, True, "guest", addr[0], self.peer_name, self.peer_char)

                elif data.startswith(b"PING"):
                    self.sock.sendto(b"PONG", addr)
                    write_peer_state(self.netdir, True, "guest", addr[0], self.peer_name, self.peer_char)

                elif data.startswith(b"POS:"):
                    pos_bytes = data[4:]
                    atomic_write(remote_state_file, pos_bytes)
                    write_peer_state(self.netdir, True, "guest", addr[0], self.peer_name, self.peer_char)

                elif data.startswith(b"EVT:"):
                    evt_str = data[4:].decode("utf-8", errors="replace") + "\n"
                    with open(events_in_file, "a") as f:
                        f.write(evt_str)
                    write_peer_state(self.netdir, True, "guest", addr[0], self.peer_name, self.peer_char)

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
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x10)
        except Exception:
            pass
        self.sock.setblocking(False)
        self.running = True
        self.connected = False
        self.peer_name = "Nithin [HOST]"
        self.peer_char = "biker"
        self.last_peer_packet = 0

    def start(self):
        local_name, local_char = get_profile(self.netdir, default_name="Partner", default_char="delivery")
        write_peer_state(self.netdir, False, "host", self.host_addr[0], self.peer_name, self.peer_char)

        t = threading.Thread(target=self._recv_loop, daemon=True)
        t.start()

        local_state_file = os.path.join(self.netdir, "local_player.state")
        events_out_file = os.path.join(self.netdir, "events.out")
        last_mtime = 0
        last_ping = 0
        last_heartbeat = 0
        last_hello = 0

        try:
            while self.running:
                now = time.time()

                # Send Handshake HELLO periodically until confirmed connected
                if not self.connected or (now - last_hello > 2.0):
                    local_name, local_char = get_profile(self.netdir, default_name="Partner", default_char="delivery")
                    hello_pkt = f"HELLO:{local_name}:{local_char}".encode("utf-8")
                    try:
                        self.sock.sendto(hello_pkt, self.host_addr)
                    except Exception:
                        pass
                    last_hello = now

                # Heartbeat PING
                if now - last_ping > 1.5:
                    try:
                        self.sock.sendto(b"PING", self.host_addr)
                    except Exception:
                        pass
                    last_ping = now

                # Check if host timed out
                if self.connected and (now - self.last_peer_packet > 5.0):
                    self.connected = False
                    write_peer_state(self.netdir, False, "host", self.host_addr[0], self.peer_name, self.peer_char)

                # Stream local player position at 20 Hz
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

                # Stream game interaction events
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
        except Exception:
            pass

    def _recv_loop(self):
        remote_state_file = os.path.join(self.netdir, "remote_player.state")
        events_in_file = os.path.join(self.netdir, "events.in")

        while self.running:
            try:
                data, addr = self.sock.recvfrom(4096)
                if not data:
                    continue

                self.connected = True
                self.last_peer_packet = time.time()

                if data.startswith(b"WELCOME:"):
                    # WELCOME:host_name:host_char
                    parts = data.decode("utf-8", errors="replace").split(":", 2)
                    if len(parts) >= 2 and parts[1]:
                        self.peer_name = parts[1]
                    if len(parts) >= 3 and parts[2]:
                        self.peer_char = parts[2]
                    write_peer_state(self.netdir, True, "host", addr[0], self.peer_name, self.peer_char)

                elif data.startswith(b"CHAR:"):
                    parts = data.decode("utf-8", errors="replace").split(":", 2)
                    if len(parts) >= 2 and parts[1]:
                        self.peer_char = parts[1]
                    if len(parts) >= 3 and parts[2]:
                        self.peer_name = parts[2]
                    write_peer_state(self.netdir, True, "host", addr[0], self.peer_name, self.peer_char)

                elif data == b"PONG":
                    write_peer_state(self.netdir, True, "host", addr[0], self.peer_name, self.peer_char)

                elif data.startswith(b"POS:"):
                    pos_bytes = data[4:]
                    atomic_write(remote_state_file, pos_bytes)
                    write_peer_state(self.netdir, True, "host", addr[0], self.peer_name, self.peer_char)

                elif data.startswith(b"EVT:"):
                    evt_str = data[4:].decode("utf-8", errors="replace") + "\n"
                    with open(events_in_file, "a") as f:
                        f.write(evt_str)
                    write_peer_state(self.netdir, True, "host", addr[0], self.peer_name, self.peer_char)

            except BlockingIOError:
                time.sleep(0.005)
            except Exception:
                pass


def main():
    parser = argparse.ArgumentParser(description="Gas Station Simulator Co-op Network Relay")
    parser.add_argument("--mode", choices=["host", "client", "auto"], default="auto")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--connect", type=str, default="127.0.0.1")
    parser.add_argument("--netdir", type=str, default="net")
    args = parser.parse_args()

    # PID file locking to prevent duplicate background relays
    pid_file = os.path.join(args.netdir, "relay.pid")
    os.makedirs(args.netdir, exist_ok=True)
    try:
        if os.path.exists(pid_file):
            with open(pid_file, "r") as f:
                old_pid = int(f.read().strip())
            if old_pid != os.getpid():
                try:
                    import psutil
                    p = psutil.Process(old_pid)
                    if "python" in p.name().lower():
                        p.terminate()
                except Exception:
                    pass
    except Exception:
        pass

    try:
        with open(pid_file, "w") as f:
            f.write(str(os.getpid()))
    except Exception:
        pass

    if args.mode == "host":
        relay = NetworkRelayHost(netdir=args.netdir, port=args.port)
        relay.start()
    elif args.mode == "client":
        relay = NetworkRelayClient(host_ip=args.connect, netdir=args.netdir, port=args.port)
        relay.start()
    else:
        # Auto detect based on role.txt
        role = "host"
        for p in ["role.txt", os.path.join(args.netdir, "role.txt")]:
            if os.path.exists(p):
                try:
                    with open(p, "r") as f:
                        c = f.read().strip().lower()
                        if c in ("host", "guest"):
                            role = c
                            break
                except Exception:
                    pass
        if role == "guest":
            target_ip = "127.0.0.1"
            for p in ["host_ip.txt", os.path.join(args.netdir, "host_ip.txt")]:
                if os.path.exists(p):
                    try:
                        with open(p, "r") as f:
                            saved = f.read().strip()
                        if saved:
                            target_ip = saved
                            break
                    except Exception:
                        pass
            relay = NetworkRelayClient(host_ip=target_ip, netdir=args.netdir, port=args.port)
            relay.start()
        else:
            relay = NetworkRelayHost(netdir=args.netdir, port=args.port)
            relay.start()

if __name__ == "__main__":
    main()
