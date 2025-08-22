#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple WebSocket Server
Implements message receiving and printing to terminal
Python 2.7 compatible version
"""

import socket
import threading
import hashlib
import base64
import struct
import time

class SimpleWebSocketServer:
    def __init__(self, host='0.0.0.0', port=8081):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
        self.clients = []
        
    def generate_accept_key(self, websocket_key):
        """Generate WebSocket handshake response Accept key"""
        magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
        combined = websocket_key + magic_string
        sha1_hash = hashlib.sha1(combined.encode('utf-8')).digest()
        return base64.b64encode(sha1_hash).decode('utf-8')
    
    def perform_handshake(self, client_socket):
        """Perform WebSocket handshake"""
        try:
            request = client_socket.recv(1024).decode('utf-8')
            print("Received handshake request:")
            print(request)
            
            # Parse WebSocket Key
            lines = request.split('\r\n')
            websocket_key = None
            for line in lines:
                if line.startswith('Sec-WebSocket-Key:'):
                    websocket_key = line.split(': ')[1]
                    break
            
            if not websocket_key:
                print("WebSocket Key not found")
                return False
            
            # Generate response
            accept_key = self.generate_accept_key(websocket_key)
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Accept: {}\r\n"
                "\r\n"
            ).format(accept_key)
            
            client_socket.send(response.encode('utf-8'))
            print("Handshake completed successfully")
            return True
            
        except Exception as e:
            print("Handshake failed: {}".format(str(e)))
            return False
    
    def decode_frame(self, data):
        """Decode WebSocket frame"""
        if len(data) < 2:
            return None
        
        # First byte
        first_byte = ord(data[0]) if isinstance(data[0], str) else data[0]
        fin = (first_byte >> 7) & 1
        opcode = first_byte & 0x0f
        
        # Second byte
        second_byte = ord(data[1]) if isinstance(data[1], str) else data[1]
        masked = (second_byte >> 7) & 1
        payload_length = second_byte & 0x7f
        
        # Calculate header length
        header_length = 2
        if payload_length == 126:
            if len(data) < 4:
                return None
            payload_length = struct.unpack('>H', data[2:4])[0]
            header_length = 4
        elif payload_length == 127:
            if len(data) < 10:
                return None
            payload_length = struct.unpack('>Q', data[2:10])[0]
            header_length = 10
        
        # Mask
        if masked:
            if len(data) < header_length + 4:
                return None
            mask = data[header_length:header_length + 4]
            header_length += 4
        
        # Check data length
        if len(data) < header_length + payload_length:
            return None
        
        # Extract payload
        payload = data[header_length:header_length + payload_length]
        
        # Unmask
        if masked:
            decoded_payload = bytearray()
            for i in range(len(payload)):
                mask_byte = ord(mask[i % 4]) if isinstance(mask[i % 4], str) else mask[i % 4]
                payload_byte = ord(payload[i]) if isinstance(payload[i], str) else payload[i]
                decoded_payload.append(payload_byte ^ mask_byte)
            payload = bytes(decoded_payload)
        
        return {
            'fin': fin,
            'opcode': opcode,
            'payload': payload,
            'payload_length': payload_length
        }
    
    def handle_client(self, client_socket, client_address):
        """Handle client connection"""
        print("New client connected: {}".format(client_address))
        
        try:
            # Perform handshake
            if not self.perform_handshake(client_socket):
                client_socket.close()
                return
            
            self.clients.append(client_socket)
            
            # Message receiving loop
            while self.running:
                try:
                    data = client_socket.recv(1024)
                    if not data:
                        break
                    
                    # Decode WebSocket frame
                    frame = self.decode_frame(data)
                    if frame:
                        if frame['opcode'] == 1:  # Text frame
                            message = frame['payload'].decode('utf-8')
                            print("Received message from {}: {}".format(client_address, message))
                        elif frame['opcode'] == 2:  # Binary frame
                            print("Received binary message from {}: {} bytes".format(client_address, len(frame['payload'])))
                        elif frame['opcode'] == 8:  # Close frame
                            print("Client {} requested connection close".format(client_address))
                            break
                        elif frame['opcode'] == 9:  # Ping frame
                            print("Received Ping from {}".format(client_address))
                        elif frame['opcode'] == 10:  # Pong frame
                            print("Received Pong from {}".format(client_address))
                    
                except socket.timeout:
                    continue
                except Exception as e:
                    print("Error processing message from client {}: {}".format(client_address, str(e)))
                    break
        
        except Exception as e:
            print("Client {} connection error: {}".format(client_address, str(e)))
        
        finally:
            if client_socket in self.clients:
                self.clients.remove(client_socket)
            client_socket.close()
            print("Client {} disconnected".format(client_address))
    
    def start_server(self):
        """Start server"""
        try:
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            self.running = True
            
            print("WebSocket server started successfully")
            print("Listening on: {}:{}".format(self.host, self.port))
            print("Waiting for client connections...")
            
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.error as e:
                    if self.running:
                        print("Error accepting connection: {}".format(str(e)))
                    break
        
        except Exception as e:
            print("Error starting server: {}".format(str(e)))
        
        finally:
            self.stop_server()
    
    def stop_server(self):
        """Stop server"""
        print("Stopping server...")
        self.running = False
        
        # Close all client connections
        for client in self.clients[:]:
            try:
                client.close()
            except:
                pass
        self.clients.clear()
        
        # Close server socket
        if self.server_socket:
            try:
                self.server_socket.close()
            except:
                pass
        
        print("Server stopped")

def main():
    """Main function"""
    server = SimpleWebSocketServer('localhost', 8081)
    
    try:
        server.start_server()
    except KeyboardInterrupt:
        print("\nReceived interrupt signal")
        server.stop_server()
    except Exception as e:
        print("Server runtime error: {}".format(str(e)))
        server.stop_server()

if __name__ == '__main__':
    main()