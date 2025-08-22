import cv2
import numpy as np
import requests
from PIL import Image
import io

# Raspberry Pi IP address and port
PI_IP = "192.168.1.100"  # Replace with your Raspberry Pi actual IP
PI_PORT = 5000
URL = f"http://{PI_IP}:{PI_PORT}/video_feed"

def display_video_stream():
    """Display video stream"""
    stream = requests.get(URL, stream=True)
    bytes_data = bytes()
    
    try:
        for chunk in stream.iter_content(chunk_size=1024):
            bytes_data += chunk
            a = bytes_data.find(b'\xff\xd8')  # JPEG start
            b = bytes_data.find(b'\xff\xd9')  # JPEG end
            
            if a != -1 and b != -1:
                jpg = bytes_data[a:b+2]
                bytes_data = bytes_data[b+2:]
                
                # Convert bytes to image
                image = Image.open(io.BytesIO(jpg))
                frame = np.array(image)
                frame = cv2.cvtColor(frame, cv2.COLOR_RGB2BGR)
                
                # Display image
                cv2.imshow('Raspberry Pi Video Stream', frame)
                
                # Press 'q' to quit
                if cv2.waitKey(1) & 0xFF == ord('q'):
                    break
    except KeyboardInterrupt:
        pass
    finally:
        cv2.destroyAllWindows()

if __name__ == '__main__':
    display_video_stream()