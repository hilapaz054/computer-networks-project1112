import socket

HOST = "127.0.0.1"
PORT = 6000

client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
client_socket.connect((HOST, PORT))

message = "Hello from client"
client_socket.send(message.encode())

data = client_socket.recv(1024).decode()
print("Received from server:", data)

client_socket.close()
