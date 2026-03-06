# Computer Networks – Client Server Project
# Author: Karin Sidi, Hila Paz Cagnart

## Description
This project implements a simple TCP client-server communication system in Python.  
The server listens on port 6000 and handles multiple clients concurrently using threads.

## Files
- server1.py – TCP server implementation  
- client1.py – TCP client implementation  
- part2_tcp_port6000.pcapng – Wireshark capture of the TCP communication  

## How to Run
1. Run server1.py  
2. Run client1.py multiple times (up to 5 clients)  
3. Capture traffic using Wireshark on the loopback interf

Server runs on localhost (127.0.0.1) on port 6000 using TCP sockets.