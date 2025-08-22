import cv2
import threading
from flask import Flask, Response, render_template
import time

app = Flask(__name__)

# Global variables
frame = None
lock = threading.Lock()
camera_running = False

def bgr8_to_jpeg(value, quality=75):
    """Convert BGR8 format image to JPEG format"""
    return bytes(cv2.imencode('.jpg', value, [cv2.IMWRITE_JPEG_QUALITY, quality])[1])

def camera_thread():
    """Camera capture thread"""
    global frame, camera_running
    
    # Open camera
    cap = cv2.VideoCapture(0)
    
    # Set camera parameters
    cap.set(3, 600)       # Width
    cap.set(4, 500)       # Height
    cap.set(5, 30)        # Frame rate
    cap.set(cv2.CAP_PROP_FOURCC, cv2.VideoWriter.fourcc('M', 'J', 'P', 'G'))
    cap.set(cv2.CAP_PROP_BRIGHTNESS, 64)   # Brightness
    cap.set(cv2.CAP_PROP_CONTRAST, 50)     # Contrast
    cap.set(cv2.CAP_PROP_EXPOSURE, 156)    # Exposure
    
    camera_running = True
    print("Camera thread started")
    
    while camera_running:
        ret, img = cap.read()
        if ret:
            with lock:
                frame = img.copy()
        time.sleep(0.033)  # ~30fps
    
    cap.release()
    print("Camera thread stopped")

def generate_frames():
    """Generate video stream frames"""
    global frame
    while True:
        with lock:
            if frame is not None:
                jpeg_data = bgr8_to_jpeg(frame)
                yield (b'--frame\r\n'
                       b'Content-Type: image/jpeg\r\n\r\n' + jpeg_data + b'\r\n')
        time.sleep(0.033)

@app.route('/')
def index():
    """Video stream homepage"""
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Video stream route"""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

if __name__ == '__main__':
    # Create templates directory and file
    import os
    if not os.path.exists('templates'):
        os.makedirs('templates')
    
    # Create HTML template
    with open('templates/index.html', 'w') as f:
        f.write('''
    <!DOCTYPE html>
    <html>
    <head>
        <title>Raspberry Pi Video Stream</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                text-align: center;
                background-color: #f0f0f0;
            }
            h1 { color: #333; }
            .container {
                margin: 20px auto;
                max-width: 800px;
            }
            .video-container {
                background-color: #000;
                padding: 10px;
                border-radius: 8px;
                box-shadow: 0 4px 8px rgba(0,0,0,0.1);
            }
        </style>
    </head>
    <body>
        <div class="container">
            <h1>Raspberry Pi Camera Live Stream</h1>
            <div class="video-container">
                <img src="{{ url_for('video_feed') }}" width="640" height="480">
            </div>
            <p>Access this page from PC browser to view live video stream</p>
        </div>
    </body>
    </html>
    ''')
    
    # Start camera thread
    cam_thread = threading.Thread(target=camera_thread)
    cam_thread.daemon = True
    cam_thread.start()
    
    # Wait for camera initialization
    time.sleep(2)
    
    # Start Flask server
    print("Starting video streaming server...")
    print("Access from PC browser: http://<RaspberryPi_IP>:5000")
    try:
        app.run(host='0.0.0.0', port=5000, threaded=True)
    except KeyboardInterrupt:
        print("Shutting down server...")
    finally:
        camera_running = False
        cam_thread.join()
        print("Server stopped")