import json
import socket
import YB_Pcb_Car  #导入亚博智能专用的底层库文件
import time

# 定义一个car对象
car = YB_Pcb_Car.YB_Pcb_Car()

# 全局socket连接
sock = None

def connect_to_server():
    global sock
    if sock is None:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.connect(('localhost', 8080))
            print("Connected to WebSocket server on port 8080")
        except Exception as e:
            print("Failed to connect to server: {}".format(e))
            sock = None
    return sock is not None

def read_json():
    global sock
    if not connect_to_server():
        return None
    
    try:
        # 发送简单的请求消息
        message = "get_data"
        sock.send(message.encode('utf-8'))
        
        # 接收响应数据
        data = sock.recv(1024)
        if data:
            json_str = data.decode('utf-8')
            json_data = json.loads(json_str)
            return json_data
        else:
            return None
    except Exception as e:
        print("Error reading data: {}".format(e))
        # 重置连接
        if sock:
            sock.close()
            sock = None
        return None

def read_cord_x():
    json_data = read_json()
    if json_data:
        cord_x = json_data["x"]
        return cord_x
    return None

def read_cord_y():
    json_data = read_json()
    if json_data:
        cord_y = json_data["y"]
        return cord_y
    return None

def read_type():
    json_data = read_json()
    if json_data:
        type = json_data["type"]
        return type
    return None

def close_connection():
    global sock
    if sock:
        try:
            sock.close()
            print("Connection closed")
        except Exception as e:
            print("Error closing connection: {}".format(e))
        finally:
            sock = None

