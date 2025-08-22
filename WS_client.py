import socket
import json
import time
import random
import threading
from datetime import datetime

class SocketStreamClient:
    def __init__(self, host, port):
        self.host = host
        self.port = port
        self.socket = None
        self.running = False
        
    def generate_sample_data(self):
        """生成示例流数据"""
        data_types = [
            # JSON数据
            lambda: json.dumps({
                "type": "sensor_data",
                "timestamp": datetime.now().isoformat(),
                "data": {
                    "temperature": round(random.uniform(20.0, 35.0), 2),
                    "humidity": round(random.uniform(30.0, 80.0), 2),
                    "pressure": round(random.uniform(980.0, 1020.0), 2)
                }
            }),
            # 文本数据
            lambda: "LOG: {0} - Event occurred with value {1}".format(datetime.now().strftime('%H:%M:%S'), random.randint(1, 100)),
            # 纯文本消息
            lambda: "STATUS: System operational at {0}".format(datetime.now().strftime('%Y-%m-%d %H:%M:%S')),
            # 数值流
            lambda: "DATA_STREAM: {0},{1},{2}".format(random.randint(100, 1000), random.randint(50, 200), random.randint(1, 10))
        ]
        
        return random.choice(data_types)()
    
    def send_stream_data(self):
        """持续发送流数据"""
        message_count = 0
        try:
            while self.running and self.socket:
                # 生成数据
                message = self.generate_sample_data()
                
                # 发送数据
                try:
                    self.socket.sendall(message.encode('utf-8') + b'\n')  # 添加换行符
                    message_count += 1
                    print("Sent [{0}]: {1}".format(message_count, message))
                except Exception as e:
                    print("Failed to send message: {0}".format(e))
                    break
                
                # 随机间隔发送
                interval = random.uniform(0.5, 3.0)
                time.sleep(interval)
                
        except Exception as e:
            print("Error in send stream: {0}".format(e))
        finally:
            self.running = False
            
    def connect(self):
        """连接到服务器"""
        print("Connecting to {0}:{1}...".format(self.host, self.port))
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print("Connected successfully!")
            
            self.running = True
            self.send_stream_data()
            
        except Exception as e:
            print("Connection failed: {0}".format(e))
        finally:
            self.close()
            
    def close(self):
        """关闭连接"""
        self.running = False
        if self.socket:
            self.socket.close()
            print("Connection closed")

# 服务器地址和端口
host = "192.168.137.203"
port = 8081

def main():
    
    # 创建客户端实例
    client = SocketStreamClient(host, port)
    
    try:
        # 连接到服务器
        client.connect()
        
    except KeyboardInterrupt:
        print("\nClient stopped by user")
        client.close()
    except Exception as e:
        print("Client error: {0}".format(e))
        client.close()

if __name__ == "__main__":
    print("Socket Stream Client")
    print("=" * 50)
    print("Target server: {0}:{1}".format(host, port))
    print("Press Ctrl+C to stop")
    print("=" * 50)
    
    main()