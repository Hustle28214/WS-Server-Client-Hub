import socket
import threading
import logging
import time
import hashlib
import base64
import struct
from datetime import datetime

# WebSocket protocol constants
WS_MAGIC_STRING = "258EAFA5-E914-47DA-95CA-C5AB0DC85B11"
WS_OPCODE_CONTINUATION = 0x0
WS_OPCODE_TEXT = 0x1
WS_OPCODE_BINARY = 0x2
WS_OPCODE_CLOSE = 0x8
WS_OPCODE_PING = 0x9
WS_OPCODE_PONG = 0xa

# Python 2.7 compatible logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("WebSocket_Server")

# File handler for logging
file_handler = logging.FileHandler('websocket_server.log')
file_handler.setLevel(logging.INFO)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)

connected_clients = set()
client_lock = threading.Lock()

def create_websocket_accept_key(websocket_key):
    """Create WebSocket accept key for handshake"""
    accept_key = websocket_key + WS_MAGIC_STRING
    sha1_hash = hashlib.sha1(accept_key.encode('utf-8')).digest()
    return base64.b64encode(sha1_hash).decode('utf-8')

def parse_websocket_frame(data):
    """Parse WebSocket frame and return payload"""
    if len(data) < 2:
        return None, None
    
    # First byte: FIN (1 bit) + RSV (3 bits) + Opcode (4 bits)
    first_byte = ord(data[0]) if isinstance(data[0], str) else data[0]
    fin = (first_byte >> 7) & 1
    opcode = first_byte & 0x0f
    
    # Second byte: MASK (1 bit) + Payload length (7 bits)
    second_byte = ord(data[1]) if isinstance(data[1], str) else data[1]
    masked = (second_byte >> 7) & 1
    payload_length = second_byte & 0x7f
    
    offset = 2
    
    # Extended payload length
    if payload_length == 126:
        if len(data) < offset + 2:
            return None, None
        payload_length = struct.unpack('>H', data[offset:offset+2])[0]
        offset += 2
    elif payload_length == 127:
        if len(data) < offset + 8:
            return None, None
        payload_length = struct.unpack('>Q', data[offset:offset+8])[0]
        offset += 8
    
    # Masking key
    if masked:
        if len(data) < offset + 4:
            return None, None
        masking_key = data[offset:offset+4]
        offset += 4
    else:
        masking_key = None
    
    # Payload data
    if len(data) < offset + payload_length:
        return None, None
    
    payload = data[offset:offset+payload_length]
    
    # Unmask payload if masked
    if masked and masking_key:
        unmasked_payload = bytearray()
        for i in range(len(payload)):
            mask_byte = ord(masking_key[i % 4]) if isinstance(masking_key[i % 4], str) else masking_key[i % 4]
            payload_byte = ord(payload[i]) if isinstance(payload[i], str) else payload[i]
            unmasked_payload.append(payload_byte ^ mask_byte)
        payload = bytes(unmasked_payload)
    
    return opcode, payload

def create_websocket_frame(opcode, payload):
    """Create WebSocket frame for sending data"""
    frame = bytearray()
    
    # First byte: FIN=1, RSV=000, Opcode
    frame.append(0x80 | opcode)
    
    # Payload length
    payload_length = len(payload)
    if payload_length < 126:
        frame.append(payload_length)
    elif payload_length < 65536:
        frame.append(126)
        frame.extend(struct.pack('>H', payload_length))
    else:
        frame.append(127)
        frame.extend(struct.pack('>Q', payload_length))
    
    # Payload data
    frame.extend(payload)
    
    return bytes(frame)

class WebSocketServer:
    def __init__(self, host='0.0.0.0', port=8080):
        self.host = host
        self.port = port
        self.server_socket = None
        self.running = False
    
    def perform_websocket_handshake(self, client_socket):
        """Perform WebSocket handshake"""
        try:
            # Receive HTTP request
            request = client_socket.recv(4096).decode('utf-8')
            logger.info("Received handshake request: {0}".format(request[:200]))
            
            # Parse WebSocket key from headers
            websocket_key = None
            for line in request.split('\r\n'):
                if line.lower().startswith('sec-websocket-key:'):
                    websocket_key = line.split(':', 1)[1].strip()
                    break
            
            if not websocket_key:
                logger.error("No WebSocket key found in handshake")
                return False
            
            # Create accept key
            accept_key = create_websocket_accept_key(websocket_key)
            
            # Send handshake response
            response = (
                "HTTP/1.1 101 Switching Protocols\r\n"
                "Upgrade: websocket\r\n"
                "Connection: Upgrade\r\n"
                "Sec-WebSocket-Accept: {0}\r\n"
                "\r\n"
            ).format(accept_key)
            
            client_socket.send(response.encode('utf-8'))
            logger.info("WebSocket handshake completed successfully")
            return True
            
        except Exception as e:
            logger.error("WebSocket handshake failed: {0}".format(e))
            return False
    
    def register_client(self, client_socket, client_address):
        """Register new client"""
        with client_lock:
            connected_clients.add(client_socket)
            client_info = "{0}:{1}".format(client_address[0], client_address[1])
            logger.info("Client connected: {0}".format(client_info))
            logger.info("Current connections: {0}".format(len(connected_clients)))
    
    def unregister_client(self, client_socket, client_address):
        """Unregister client"""
        with client_lock:
            connected_clients.discard(client_socket)
            client_info = "{0}:{1}".format(client_address[0], client_address[1])
            logger.info("Client disconnected: {0}".format(client_info))
            logger.info("Current connections: {0}".format(len(connected_clients)))
    
    def send_pong(self, client_socket, payload=b''):
        """Send pong frame in response to ping"""
        try:
            pong_frame = create_websocket_frame(WS_OPCODE_PONG, payload)
            client_socket.send(pong_frame)
            logger.info("Sent pong response")
        except Exception as e:
            logger.error("Error sending pong: {0}".format(e))
    
    def handle_client(self, client_socket, client_address):
        """Handle WebSocket client connection"""
        try:
            # Perform WebSocket handshake
            if not self.perform_websocket_handshake(client_socket):
                logger.error("WebSocket handshake failed for client {0}:{1}".format(client_address[0], client_address[1]))
                client_socket.close()
                return
            
            # Register client after successful handshake
            self.register_client(client_socket, client_address)
            
            # Handle WebSocket frames
            while self.running:
                try:
                    # Receive data from client
                    data = client_socket.recv(4096)
                    if not data:
                        break
                    
                    # Parse WebSocket frame
                    opcode, payload = parse_websocket_frame(data)
                    
                    if opcode is None:
                        logger.warning("Invalid WebSocket frame received")
                        continue
                    
                    # Handle different frame types
                    if opcode == WS_OPCODE_TEXT:
                        # Text message - print stream message directly
                        try:
                            message = payload.decode('utf-8')
                            print("Received stream message: {0}".format(message))
                            logger.info("Stream message: {0}".format(message))
                        except UnicodeDecodeError:
                            logger.error("Failed to decode text message")
                    
                    elif opcode == WS_OPCODE_BINARY:
                        # Binary message - print as hex
                        hex_data = ' '.join('{:02x}'.format(ord(b) if isinstance(b, str) else b) for b in payload)
                        print("Received binary stream: {0}".format(hex_data))
                        logger.info("Binary stream: {0}".format(hex_data))
                    
                    elif opcode == WS_OPCODE_PING:
                        # Respond to ping with pong
                        self.send_pong(client_socket, payload)
                    
                    elif opcode == WS_OPCODE_PONG:
                        # Pong received
                        logger.info("Pong received")
                    
                    elif opcode == WS_OPCODE_CLOSE:
                        # Close connection
                        logger.info("Close frame received")
                        break
                    
                    else:
                        logger.warning("Unknown opcode received: {0}".format(opcode))
                        
                except socket.error as e:
                    logger.info("Client connection closed: {0}".format(e))
                    break
                except Exception as e:
                    logger.error("Error processing WebSocket frame: {0}".format(e))
                    break
                    
        except Exception as e:
            logger.error("Error in WebSocket client handling: {0}".format(e))
        finally:
            self.unregister_client(client_socket, client_address)
            try:
                client_socket.close()
            except:
                pass
    
    def start_server(self):
        """Start WebSocket server"""
        try:
            logger.info("Starting WebSocket server {0}:{1}".format(self.host, self.port))
            
            # Create socket
            self.server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            
            # Bind and listen
            self.server_socket.bind((self.host, self.port))
            self.server_socket.listen(5)
            
            self.running = True
            logger.info("WebSocket server started, listening on {0}:{1}".format(self.host, self.port))
            
            # Accept connections
            while self.running:
                try:
                    client_socket, client_address = self.server_socket.accept()
                    # Handle each client in a separate thread
                    client_thread = threading.Thread(
                        target=self.handle_client,
                        args=(client_socket, client_address)
                    )
                    client_thread.daemon = True
                    client_thread.start()
                except socket.error as e:
                    if self.running:
                        logger.error("Error accepting connection: {0}".format(e))
                    break
                except Exception as e:
                    logger.error("Error in server loop: {0}".format(e))
                    break
            
        except Exception as e:
            logger.error("Error starting server: {0}".format(e))
            raise
    
    def stop_server(self):
        """Stop WebSocket server"""
        if self.server_socket:
            logger.info("Stopping WebSocket server...")
            self.running = False
            try:
                self.server_socket.close()
            except:
                pass
            logger.info("WebSocket server stopped")


def main():
    """Main function"""
    server = WebSocketServer(host='0.0.0.0', port=8080)
    try:
        server.start_server()
    except KeyboardInterrupt:
        logger.info("Received interrupt signal, shutting down server...")
        server.stop_server()
    except Exception as e:
        logger.error("Error during server runtime: {0}".format(e))
        server.stop_server()


if __name__ == "__main__":
    logger.info("Starting WebSocket server...")
    main()




