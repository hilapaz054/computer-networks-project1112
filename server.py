import socket

HOST = "127.0.0.1"
PORT = 6000
MAX_CLIENTS = 5

server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
server_socket.bind((HOST, PORT))
server_socket.listen(MAX_CLIENTS)

print("Server is running and waiting for clients...")

for i in range(MAX_CLIENTS):
	print(f"Waiting for client {i+1}...")
	conn, addr = server_socket.accept()
	print(f"Client {i+1} connected from {addr}")

	data = conn.recv(1024).decode()
	print(f"Received from client {i+1}: {data}")

	response = f"Hello client {i+1}, message received"
	conn.send(response.encode())

	conn.close()
	print(f"Client {i+1} connection closed\n")

server_socket.close()
print("Server closed after serving 5 clients")
