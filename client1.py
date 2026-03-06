import socket
import threading
import sys

HOST = "127.0.0.1"
PORT = 6000
RECV_CHUNK = 4096


def recv_loop(sock: socket.socket, stop_event: threading.Event) -> None:
    buf = ""
    try:
        while not stop_event.is_set():
            data = sock.recv(RECV_CHUNK)
            if not data:
                print("\n[SERVER CLOSED]")
                stop_event.set()
                return

            buf += data.decode("utf-8", errors="replace")
            while "\n" in buf:
                line, buf = buf.split("\n", 1)
                line = line.rstrip("\r")
                if line:
                    print(line)
    except OSError:
        stop_event.set()


def parse_args():
    host = HOST
    port = PORT
    if len(sys.argv) >= 2:
        host = sys.argv[1]
    if len(sys.argv) >= 3:
        port = int(sys.argv[2])
    return host, port


def main() -> None:
    host, port = parse_args()

    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        sock.connect((host, port))
    except OSError as e:
        print(f"[ERROR] Could not connect to {host}:{port} ({e})")
        return

    stop_event = threading.Event()
    threading.Thread(target=recv_loop, args=(sock, stop_event), daemon=True).start()

    print("Connected.")
    print("Quick start:")
    print("  /login <name>")
    print("  /who")
    print("  /connect <other>")
    print("  /msg hello")
    print("  /quit")

    try:
        while not stop_event.is_set():
            line = input()
            try:
                sock.sendall((line + "\n").encode("utf-8"))
            except (BrokenPipeError, ConnectionResetError, OSError):
                print("[ERROR] Connection lost while sending.")
                stop_event.set()
                break

            if line.strip() == "/quit":
                stop_event.set()
                break

    except KeyboardInterrupt:
        try:
            sock.sendall(b"/quit\n")
        except OSError:
            pass
        stop_event.set()
    finally:
        try:
            sock.close()
        except OSError:
            pass


if __name__ == "__main__":
    main()