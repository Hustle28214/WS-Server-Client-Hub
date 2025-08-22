#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Simple WebSocket Client
Implements basic WebSocket client functionality
Python 2/3 compatible version
"""

import socket
import threading
import hashlib
import base64
import struct
import time
import random
import string
import sys

# Python 2/3 compatibility
if sys.version_info[0] == 3:
    unicode = str
    raw_input = input
else:
    unicode = unicode
    raw_input = raw_input

class SimpleWebSocketClient:
    def __init__(self, host='192.168.137.203', port=8081):
        self.host = host
        self.port = port
        self.socket = None
        self.connected = False
        self.running = False
        
    def generate_websocket_key(self):
        """Generate WebSocket handshake key"""
        key_bytes = ''.join(random.choice(string.ascii_letters + string.digits) for _ in range(16))
        return base64.b64encode(key_bytes.encode('utf-8')).decode('utf-8')
    
    def create_handshake_request(self, websocket_key):
        """Create WebSocket handshake request"""
        request = (
            "GET / HTTP/1.1\r\n"
            "Host: {}:{}\r\n"
            "Upgrade: websocket\r\n"
            "Connection: Upgrade\r\n"
            "Sec-WebSocket-Key: {}\r\n"
            "Sec-WebSocket-Version: 13\r\n"
            "\r\n"
        ).format(self.host, self.port, websocket_key)
        return request
    
    def verify_handshake_response(self, response, websocket_key):
        """Verify WebSocket handshake response"""
        try:
            lines = response.split('\r\n')
            
            # Check status line
            if not lines[0].startswith('HTTP/1.1 101'):
                print("Handshake failed: Invalid status code")
                return False
            
            # Find Accept header
            accept_key = None
            for line in lines:
                if line.startswith('Sec-WebSocket-Accept:'):
                    accept_key = line.split(': ')[1]
                    break
            
            if not accept_key:
                print("Handshake failed: No Accept key found")
                return False
            
            # Verify Accept key
            magic_string = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
            combined = websocket_key + magic_string
            expected_accept = base64.b64encode(hashlib.sha1(combined.encode('utf-8')).digest()).decode('utf-8')
            
            if accept_key != expected_accept:
                print("Handshake failed: Invalid Accept key")
                return False
            
            return True
            
        except Exception as e:
            print("Handshake verification error: {}".format(str(e)))
            return False
    
    def create_frame(self, message, opcode=1):
        """Create WebSocket frame"""
        try:
            if isinstance(message, unicode):
                payload = message.encode('utf-8')
            elif isinstance(message, str):
                if sys.version_info[0] == 3:
                    payload = message.encode('utf-8')
                else:
                    payload = message
            else:
                payload = str(message).encode('utf-8') if sys.version_info[0] == 3 else str(message)
            
            payload_length = len(payload)
            
            # First byte: FIN=1, opcode
            first_byte = 0x80 | opcode
            
            # Generate mask
            mask = struct.pack('!I', random.randint(0, 0xFFFFFFFF))
            
            # Create frame header
            if payload_length < 126:
                header = struct.pack('!BB', first_byte, 0x80 | payload_length)
            elif payload_length < 65536:
                header = struct.pack('!BBH', first_byte, 0x80 | 126, payload_length)
            else:
                header = struct.pack('!BBQ', first_byte, 0x80 | 127, payload_length)
            
            # Mask payload
            masked_payload = bytearray()
            for i in range(len(payload)):
                if sys.version_info[0] == 3:
                    payload_byte = payload[i] if isinstance(payload, (bytes, bytearray)) else ord(payload[i])
                    mask_byte = mask[i % 4] if isinstance(mask, (bytes, bytearray)) else ord(mask[i % 4])
                else:
                    payload_byte = ord(payload[i]) if isinstance(payload[i], str) else payload[i]
                    mask_byte = ord(mask[i % 4]) if isinstance(mask[i % 4], str) else mask[i % 4]
                masked_payload.append(payload_byte ^ mask_byte)
            
            return header + mask + bytes(masked_payload)
            
        except Exception as e:
            print("Frame creation error: {}".format(str(e)))
            return None
    
    def decode_frame(self, data):
        """Decode WebSocket frame"""
        if len(data) < 2:
            return None
        
        # First byte
        if sys.version_info[0] == 3:
            first_byte = data[0] if isinstance(data, (bytes, bytearray)) else ord(data[0])
        else:
            first_byte = ord(data[0]) if isinstance(data[0], str) else data[0]
        fin = (first_byte >> 7) & 1
        opcode = first_byte & 0x0f
        
        # Second byte
        if sys.version_info[0] == 3:
            second_byte = data[1] if isinstance(data, (bytes, bytearray)) else ord(data[1])
        else:
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
        
        # Check data length
        if len(data) < header_length + payload_length:
            return None
        
        # Extract payload
        payload = data[header_length:header_length + payload_length]
        
        return {
            'fin': fin,
            'opcode': opcode,
            'payload': payload,
            'payload_length': payload_length
        }
    
    def connect(self):
        """Connect to WebSocket server"""
        try:
            print("Connecting to WebSocket server {}:{}".format(self.host, self.port))
            
            # Create socket
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(10)
            self.socket.connect((self.host, self.port))
            
            # Perform handshake
            websocket_key = self.generate_websocket_key()
            handshake_request = self.create_handshake_request(websocket_key)
            
            print("Sending handshake request...")
            self.socket.send(handshake_request.encode('utf-8'))
            
            # Receive handshake response
            response = self.socket.recv(1024).decode('utf-8')
            print("Received handshake response:")
            print(response)
            
            # Verify handshake
            if self.verify_handshake_response(response, websocket_key):
                print("WebSocket connection established successfully!")
                self.connected = True
                self.running = True
                return True
            else:
                print("Handshake verification failed")
                self.socket.close()
                return False
                
        except Exception as e:
            print("Connection error: {}".format(str(e)))
            if self.socket:
                self.socket.close()
            return False
    
    def send_message(self, message):
        """Send text message to server"""
        if not self.connected:
            print("Not connected to server")
            return False
        
        try:
            frame = self.create_frame(message, opcode=1)  # Text frame
            if frame:
                self.socket.send(frame)
                print("Message sent: {}".format(message))
                return True
            else:
                print("Failed to create message frame")
                return False
                
        except Exception as e:
            print("Send message error: {}".format(str(e)))
            return False
    
    def receive_messages(self):
        """Receive messages from server (runs in separate thread)"""
        while self.running and self.connected:
            try:
                data = self.socket.recv(1024)
                if not data:
                    print("Server closed connection")
                    break
                
                frame = self.decode_frame(data)
                if frame:
                    if frame['opcode'] == 1:  # Text frame
                        message = frame['payload'].decode('utf-8')
                        print("Received from server: {}".format(message))
                    elif frame['opcode'] == 2:  # Binary frame
                        print("Received binary data: {} bytes".format(len(frame['payload'])))
                    elif frame['opcode'] == 8:  # Close frame
                        print("Server requested connection close")
                        break
                    elif frame['opcode'] == 9:  # Ping frame
                        print("Received Ping from server")
                    elif frame['opcode'] == 10:  # Pong frame
                        print("Received Pong from server")
                
            except socket.timeout:
                continue
            except Exception as e:
                print("Receive error: {}".format(str(e)))
                break
        
        self.connected = False
    
    def disconnect(self):
        """Disconnect from server"""
        print("Disconnecting from server...")
        self.running = False
        self.connected = False
        
        if self.socket:
            try:
                # Send close frame
                close_frame = self.create_frame("", opcode=8)
                if close_frame:
                    self.socket.send(close_frame)
                self.socket.close()
            except:
                pass
        
        print("Disconnected")
    
    def interactive_mode(self):
        """Interactive mode for user input"""
        if not self.connect():
            return
        
        # Start receive thread
        receive_thread = threading.Thread(target=self.receive_messages)
        receive_thread.daemon = True
        receive_thread.start()
        
        print("\n=== WebSocket Client Interactive Mode ===")
        print("Commands:")
        print("  Type message and press Enter to send")
        print("  Type 'quit' or 'exit' to disconnect")
        print("  Type 'help' to show this help")
        print("=========================================\n")
        
        try:
            while self.connected:
                try:
                    user_input = raw_input("Enter message: ").strip()
                    
                    if user_input.lower() in ['quit', 'exit']:
                        break
                    elif user_input.lower() == 'help':
                        print("Commands:")
                        print("  Type message and press Enter to send")
                        print("  Type 'quit' or 'exit' to disconnect")
                        print("  Type 'help' to show this help")
                        continue
                    elif user_input:
                        self.send_message(user_input)
                    
                except KeyboardInterrupt:
                    print("\nReceived interrupt signal")
                    break
                except EOFError:
                    print("\nInput ended")
                    break
                    
        finally:
            self.disconnect()

def main():
    """Main function"""
    print("Simple WebSocket Client")
    print("Connecting to 192.168.137.203:8081")
    
    client = SimpleWebSocketClient('192.168.137.203', 8081)
    
    try:
        client.interactive_mode()
    except Exception as e:
        print("Client error: {}".format(str(e)))
        client.disconnect()

if __name__ == '__main__':
    main()