import socket
import threading
from typing import Dict, Optional, Set, Tuple

HOST = "127.0.0.1"
PORT = 6000
MAX_CLIENTS = 50
RECV_CHUNK = 4096

clients: Dict[str, socket.socket] = {}

links: Dict[str, Set[str]] = {}

lock = threading.Lock()


def send_line(conn: socket.socket, text: str) -> bool:
    """Send a single newline-terminated line. Returns False on failure."""
    try:
        conn.sendall((text + "\n").encode("utf-8"))
        return True
    except (BrokenPipeError, ConnectionResetError, OSError):
        return False


def recv_lines(conn: socket.socket, buffer: str) -> Tuple[Optional[list[str]], str]:
    """
    Read bytes and return complete lines (without newline).
    Returns (None, buffer) if connection is closed.
    """
    data = conn.recv(RECV_CHUNK)
    if not data:
        return None, buffer

    buffer += data.decode("utf-8", errors="replace")

    lines: list[str] = []
    while "\n" in buffer:
        line, buffer = buffer.split("\n", 1)
        line = line.rstrip("\r").strip()
        lines.append(line)

    return lines, buffer


def remove_user(username: str) -> None:
    """Remove user from clients + links and close socket (best-effort)."""
    with lock:
        sock = clients.pop(username, None)

       
        peers = links.pop(username, set())
        for p in list(peers):
            if p in links:
                links[p].discard(username)
                if not links[p]:
                    links.pop(p, None)

    if sock:
        try:
            sock.close()
        except OSError:
            pass


def get_socket(username: str) -> Optional[socket.socket]:
    with lock:
        return clients.get(username)


def is_online(username: str) -> bool:
    with lock:
        return username in clients


def list_online() -> str:
    with lock:
        names = sorted(clients.keys())
    return ", ".join(names) if names else "(none)"


def link_users(a: str, b: str) -> None:
    """Create a chat link (both directions)."""
    with lock:
        links.setdefault(a, set()).add(b)
        links.setdefault(b, set()).add(a)


def unlink_users(a: str, b: str) -> None:
    """Remove a chat link (both directions)."""
    with lock:
        if a in links:
            links[a].discard(b)
            if not links[a]:
                links.pop(a, None)
        if b in links:
            links[b].discard(a)
            if not links[b]:
                links.pop(b, None)


def get_linked_peers(username: str) -> Set[str]:
    with lock:
        return set(links.get(username, set()))


def handle_client(conn: socket.socket, addr: Tuple[str, int]) -> None:
    username: Optional[str] = None
    buffer = ""

    send_line(conn, "WELCOME")
    send_line(conn, "Commands:")
    send_line(conn, "  /login <name>")
    send_line(conn, "  /connect <user>        (open chat with user)")
    send_line(conn, "  /msg <text>            (send to all connected peers)")
    send_line(conn, "  /dm <user> <text>      (send to one user)")
    send_line(conn, "  /disconnect <user>     (close chat with user)")
    send_line(conn, "  /who                   (list online users)")
    send_line(conn, "  /quit")

    try:
        while True:
            lines, buffer = recv_lines(conn, buffer)
            if lines is None:
                break  

            for line in lines:
                if not line:
                    continue

                
                if username is None:
                    if line.startswith("/login "):
                        candidate = line.split(" ", 1)[1].strip()
                        if not candidate:
                            send_line(conn, "ERR empty username")
                            continue

                        with lock:
                            if candidate in clients:
                                send_line(conn, "ERR username taken")
                                continue
                            clients[candidate] = conn
                            links.setdefault(candidate, set())
                            username = candidate

                        send_line(conn, f"OK logged in as {username}")
                        continue

                    send_line(conn, "ERR please login first: /login <name>")
                    continue

                
                if line == "/quit":
                    send_line(conn, "BYE")
                    return

                if line == "/who":
                    send_line(conn, f"ONLINE: {list_online()}")
                    continue

                if line.startswith("/connect "):
                    target = line.split(" ", 1)[1].strip()
                    if not target:
                        send_line(conn, "ERR usage: /connect <user>")
                        continue
                    if target == username:
                        send_line(conn, "ERR cannot connect to yourself")
                        continue

                    target_conn = get_socket(target)
                    if not target_conn:
                        send_line(conn, f"ERR user '{target}' not online")
                        continue

                    link_users(username, target)
                    send_line(conn, f"OK chat opened with {target}")
                    send_line(target_conn, f"INFO {username} opened a chat with you. Use /connect {username} to reply.")
                    continue

                if line.startswith("/disconnect "):
                    target = line.split(" ", 1)[1].strip()
                    if not target:
                        send_line(conn, "ERR usage: /disconnect <user>")
                        continue

                    peers = get_linked_peers(username)
                    if target not in peers:
                        send_line(conn, f"ERR no active chat with {target}")
                        continue

                    unlink_users(username, target)
                    send_line(conn, f"OK chat closed with {target}")

                    target_conn = get_socket(target)
                    if target_conn:
                        send_line(target_conn, f"INFO {username} closed the chat with you.")
                    continue

                if line.startswith("/dm "):
                    parts = line.split(" ", 2)
                    if len(parts) < 3:
                        send_line(conn, "ERR usage: /dm <user> <text>")
                        continue
                    target = parts[1].strip()
                    msg = parts[2].strip()
                    if not msg:
                        send_line(conn, "ERR empty message")
                        continue

                    target_conn = get_socket(target)
                    if not target_conn:
                        send_line(conn, f"ERR user '{target}' not online")
                        continue

                    ok1 = send_line(target_conn, f"[DM] {username}: {msg}")
                    ok2 = send_line(conn, f"[DM] to {target}: {msg}")

                    if not ok1:
                        remove_user(target)
                        send_line(conn, f"ERR user '{target}' disconnected")
                    if not ok2:
                        return
                    continue

                if line.startswith("/msg "):
                    msg = line.split(" ", 1)[1].strip()
                    if not msg:
                        send_line(conn, "ERR usage: /msg <text>")
                        continue

                    peers = get_linked_peers(username)
                    if not peers:
                        send_line(conn, "ERR no active chat. Use /connect <user> first")
                        continue

                    dead: list[str] = []
                    for p in peers:
                        p_conn = get_socket(p)
                        if not p_conn:
                            dead.append(p)
                            continue
                        ok = send_line(p_conn, f"[{username}] {msg}")
                        if not ok:
                            dead.append(p)

                    
                    for p in dead:
                        unlink_users(username, p)
                        if is_online(p):
                            remove_user(p)

                    send_line(conn, f"[you -> {', '.join(sorted(peers))}] {msg}")
                    continue

                send_line(conn, "ERR unknown command")

    except (ConnectionResetError, BrokenPipeError, OSError):
        pass
    finally:
        if username:
            remove_user(username)
        else:
            try:
                conn.close()
            except OSError:
                pass
        print(f"[DISCONNECT] {addr} user={username}")


def main() -> None:
    server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    server.bind((HOST, PORT))
    server.listen(MAX_CLIENTS)

    print(f"[LISTENING] {HOST}:{PORT}")

    while True:
        conn, addr = server.accept()
        print(f"[CONNECT] {addr}")
        threading.Thread(target=handle_client, args=(conn, addr), daemon=True).start()


if __name__ == "__main__":
    main()