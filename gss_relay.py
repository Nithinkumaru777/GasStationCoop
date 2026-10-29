"""Gas Station Simulator Co-op Network Relay & State Broker.
Runs silently in background with ZERO console clutter.
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


def get_server_display_name():
    name = os.getenv("USERNAME") or os.getenv("USER") or "Host"
    return f"{name}'s Gas Station"


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


def write_server_info(netdir, status, server_name, ip, port=DEFAULT_PORT):
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
        self.running = True

    def start(self):
        write_server_info(self.netdir, "HOSTING", self.server_name, "127.0.0.1", self.port)

        t_beacon = threading.Thread(target=self._beacon_loop, daemon=True)
        t_beacon.start()

        t_recv = threading.Thread(target=self._recv_loop, daemon=True)
        t_recv.start()

        local_state_file = os.path.join(self.netdir, "local_player.state")
        events_out_file = os.path.join(self.netdir, "events.out")
        last_mtime = 0
        last_heartbeat = 0

        try:
            while self.running:
                now = time.time()
                if self.client_addr:
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

                if self.client_addr != addr:
                    self.client_addr = addr

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
        try:
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_RCVBUF, 65536)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_SNDBUF, 65536)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_TOS, 0x10)
        except Exception:
            pass
        self.sock.setblocking(False)
        self.running = True
        self.connected = False

    @staticmethod
    def auto_discover_host(timeout=1.5, port=DEFAULT_PORT):
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        s.settimeout(0.3)

        start_time = time.time()
        while time.time() - start_time < timeout:
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
        write_server_info(self.netdir, "CONNECTED", self.server_name, self.host_addr[0], self.host_addr[1])

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
                if now - last_ping > 2.0:
                    try:
                        self.sock.sendto(b"PING", self.host_addr)
                    except Exception:
                        pass
                    last_ping = now

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

                if data == b"PONG":
                    self.connected = True
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
    def __init__(self, netdir, port=DEFAULT_PORT):
        self.netdir = netdir
        self.port = port
        os.makedirs(self.netdir, exist_ok=True)
        self.running = True
        self.discovered_ip = None
        self.discovered_name = None

    def read_role(self):
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
        write_server_info(self.netdir, "SCANNING", "Scanning for games...", "", self.port)
        last_scan_time = 0

        while self.running:
            role = self.read_role()

            if role == "host":
                relay = NetworkRelayHost(netdir=self.netdir, port=self.port)
                relay.start()
                return

            elif role == "guest":
                target_ip = self.discovered_ip or "127.0.0.1"
                for p in ["host_ip.txt", os.path.join(self.netdir, "host_ip.txt")]:
                    if os.path.exists(p):
                        try:
                            with open(p, "r") as f:
                                saved = f.read().strip()
                            if saved:
                                target_ip = saved
                                break
                        except Exception:
                            pass

                relay = NetworkRelayClient(host_ip=target_ip, netdir=self.netdir, port=self.port, server_name=self.discovered_name)
                relay.start()
                return

            now = time.time()
            if now - last_scan_time > 2.0:
                ip, name = NetworkRelayClient.auto_discover_host(timeout=0.4, port=self.port)
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
                        help="Relay mode: host, client, or auto")
    parser.add_argument("--connect", default="", help="Host IP to connect to")
    parser.add_argument("--port", type=int, default=DEFAULT_PORT, help="UDP port")
    parser.add_argument("--netdir", default="net", help="Path to net directory")

    args = parser.parse_args()
    netdir = os.path.abspath(args.netdir)
    os.makedirs(netdir, exist_ok=True)

    if args.mode == "host":
        relay = NetworkRelayHost(netdir=netdir, port=args.port)
        relay.start()

    elif args.mode == "client":
        target_ip = args.connect.strip() or "127.0.0.1"
        relay = NetworkRelayClient(host_ip=target_ip, netdir=netdir, port=args.port)
        relay.start()

    else:
        daemon = DynamicRelayDaemon(netdir=netdir, port=args.port)
        daemon.start()


if __name__ == "__main__":
    main()
