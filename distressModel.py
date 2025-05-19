from flask import Flask, jsonify, Response, request
import threading
import cv2
import mediapipe as mp
import numpy as np
import pygame as pg
import time
from queue import Queue
from twilio.rest import Client
from pyngrok import ngrok

app = Flask(__name__)

# Initialize pygame for audio
pg.init()
sound = pg.mixer.Sound('Alrm.mp3')  # Ensure this file is in the same directory

# Twilio Config - REPLACE WITH YOUR ACTUAL CREDENTIALS
TWILIO_ACCOUNT_SID = 'AC29603b4663b6775d4d9860fdea00c939'
TWILIO_AUTH_TOKEN = '0ad658de36c3b0366460af3191ba67be'
TWILIO_PHONE_NUMBER = '+15392861122'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'
RECIPIENT_PHONE = '+919842517108'
RECIPIENT_WHATSAPP = 'whatsapp:+919842517108'
client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)

# Hardcoded location (you can replace with live GPS data)
LATITUDE = 12.9716  # Example: Bangalore
LONGITUDE = 77.5946

# Camera control
camera_active = False
last_alert_time = 0
ALERT_COOLDOWN = 30  # seconds

# MediaPipe Setup
poseModel = mp.solutions.pose
draw = mp.solutions.drawing_utils
poseDetector = poseModel.Pose(
    model_complexity=1,
    static_image_mode=False,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.7
)

# Frame buffer and lock
frame_buffer = Queue(maxsize=2)
camera_lock = threading.Lock()

# Set up ngrok tunnel
public_url = ngrok.connect(5000).public_url
print(f" * Public URL: {public_url}")
SERVER_URL = public_url

def calculateAngle(a, b, c, d):
    a = np.array(a)
    b = np.array(b)
    c = np.array(c)
    d = np.array(d)
    angle = np.arctan2(c[1]-d[1], c[0]-d[0]) - np.arctan2(a[1]-b[1], a[0]-b[0])
    return np.abs(np.degrees(angle))

def trigger_emergency():
    global last_alert_time

    location_link = f"https://www.google.com/maps/search/?api=1&query={LATITUDE},{LONGITUDE}"

    try:
        current_time = time.time()
        if current_time - last_alert_time > ALERT_COOLDOWN:
            # WhatsApp message
            whatsapp_msg = client.messages.create(
                body=f"🚨 EMERGENCY! Danger pose detected!\n"
                     f"View live feed: {SERVER_URL}/video_feed\n"
                     f"Live location: {location_link}",
                from_=TWILIO_WHATSAPP_NUMBER,
                to=RECIPIENT_WHATSAPP
            )

            # SMS message
            sms_msg = client.messages.create(
                body=f"🚨 EMERGENCY! Danger pose detected!\n"
                     f"View live: {SERVER_URL}/live\n"
                     f"Location: {location_link}",
                from_=TWILIO_PHONE_NUMBER,
                to=RECIPIENT_PHONE
            )

            # Phone call
            call = client.calls.create(
                twiml='<Response><Say>Emergency! Danger pose detected. Check your WhatsApp or SMS for live feed and location link.</Say></Response>',
                to=RECIPIENT_PHONE,
                from_=TWILIO_PHONE_NUMBER
            )

            last_alert_time = current_time
            print(f"Alerts sent! WhatsApp: {whatsapp_msg.sid}, SMS: {sms_msg.sid}, Call: {call.sid}")
    except Exception as e:
        print(f"Alert failed: {str(e)}")

def camera_capture_thread():
    cap = cv2.VideoCapture(0)  # Change to 0 if needed

    while True:
        with camera_lock:
            if not camera_active:
                time.sleep(0.1)
                continue

            ret, frame = cap.read()
            if not ret:
                print("Webcam read error - retrying...")
                time.sleep(1)
                continue

            frame = cv2.flip(frame, 1)

            if frame_buffer.full():
                frame_buffer.get()
            frame_buffer.put(frame)

camera_thread = threading.Thread(
    target=camera_capture_thread,
    daemon=True
)
camera_thread.start()

def generate_frames():
    count = 0
    stage = 'no'
    fps_update_interval = 2
    last_processed_time = time.time()
    frame_count = 0

    while True:
        if not camera_active:
            time.sleep(0.1)
            continue

        try:
            frame = frame_buffer.get(timeout=1.0)

            current_time = time.time()
            frame_count += 1
            if current_time - last_processed_time > fps_update_interval:
                fps = frame_count / (current_time - last_processed_time)
                frame_count = 0
                last_processed_time = current_time

            frameRGB = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
            processed = poseDetector.process(frameRGB)

            if processed.pose_landmarks:
                landmarks = processed.pose_landmarks.landmark
                try:
                    leftElbow = [landmarks[poseModel.PoseLandmark.LEFT_ELBOW.value].x,
                                 landmarks[poseModel.PoseLandmark.LEFT_ELBOW.value].y]
                    leftWrist = [landmarks[poseModel.PoseLandmark.LEFT_WRIST.value].x,
                                 landmarks[poseModel.PoseLandmark.LEFT_WRIST.value].y]
                    rightElbow = [landmarks[poseModel.PoseLandmark.RIGHT_ELBOW.value].x,
                                  landmarks[poseModel.PoseLandmark.RIGHT_ELBOW.value].y]
                    rightWrist = [landmarks[poseModel.PoseLandmark.RIGHT_WRIST.value].x,
                                  landmarks[poseModel.PoseLandmark.RIGHT_WRIST.value].y]
                    leftEye = [landmarks[poseModel.PoseLandmark.LEFT_EYE_INNER.value].x,
                               landmarks[poseModel.PoseLandmark.LEFT_EYE_INNER.value].y]
                    rightEye = [landmarks[poseModel.PoseLandmark.RIGHT_EYE_INNER.value].x,
                                landmarks[poseModel.PoseLandmark.RIGHT_EYE_INNER.value].y]

                    angle = calculateAngle(leftElbow, leftWrist, rightElbow, rightWrist)

                    if angle < 50:
                        stage = 'safe'
                    elif angle > 70 and stage == 'safe' and leftEye[1] > leftWrist[1] and rightEye[1] > rightWrist[1]:
                        count += 1
                        if count > 40:
                            stage = 'Danger'
                            sound.play()
                            threading.Thread(target=trigger_emergency).start()
                            count = 0

                    draw.draw_landmarks(frame, processed.pose_landmarks, poseModel.POSE_CONNECTIONS)
                    cv2.putText(frame, f"Status: {stage}", (10, 30),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, f"Count: {count}", (10, 60),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
                    cv2.putText(frame, f"FPS: {fps:.1f}", (10, 90),
                                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 1)

                except (AttributeError, IndexError) as e:
                    print(f"Landmark detection error: {str(e)}")

            ret, buffer = cv2.imencode('.jpg', frame)
            if not ret:
                continue

            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + buffer.tobytes() + b'\r\n')

        except Exception as e:
            print(f"Stream error: {str(e)}")
            time.sleep(0.1)

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                    mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/camera/<action>', methods=['POST'])
def camera_control(action):
    global camera_active

    if action == 'start' and not camera_active:
        camera_active = True
        return jsonify({"status": "Camera started", "stream_url": f"{SERVER_URL}/video_feed"})
    elif action == 'stop' and camera_active:
        camera_active = False
        return jsonify({"status": "Camera stopped"})
    return jsonify({"status": "Invalid request"})

@app.route('/live')
def live_view():
    global camera_active
    if not camera_active:
        camera_active = True
    return """
    <html>
    <head>
        <meta http-equiv="refresh" content="0; url=/" />
        <title>Emergency Live Feed</title>
    </head>
    <body>
        <p>Redirecting to live feed...</p>
    </body>
    </html>
    """

@app.route('/')
def home():
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>Pose Detection</title>
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <style>
            body { font-family: Arial, sans-serif; max-width: 800px; margin: 0 auto; padding: 20px; text-align: center; }
            .camera-container { background: #f5f5f5; border-radius: 8px; padding: 20px; margin-top: 20px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }
            .camera-feed { width: 100%; max-width: 640px; border-radius: 4px; background: #000; }
            .controls { margin: 20px 0; }
            button { padding: 10px 20px; font-size: 16px; margin: 0 10px; border: none; border-radius: 4px; cursor: pointer; }
            #startBtn { background: #4CAF50; color: white; }
            #stopBtn { background: #f44336; color: white; }
            button:disabled { background: #cccccc; cursor: not-allowed; }
            .status { padding: 10px; margin-top: 10px; border-radius: 4px; font-weight: bold; }
            .offline { background: #ffebee; color: #c62828; }
            .online { background: #e8f5e9; color: #2e7d32; }
            h1 { color: #333; }
        </style>
    </head>
    <body>
        <h1>Pose Detection System</h1>
        <p>Monitoring for danger poses</p>
        <div class="camera-container">
            <img src="/video_feed" class="camera-feed" width="640" height="480">
            <div class="controls">
                <button id="startBtn" onclick="controlCamera('start')">Start</button>
                <button id="stopBtn" onclick="controlCamera('stop')" disabled>Stop</button>
            </div>
            <div class="status offline" id="status">Status: Offline</div>
        </div>
        <script>
        function controlCamera(action) {
            const startBtn = document.getElementById('startBtn');
            const stopBtn = document.getElementById('stopBtn');
            const statusDiv = document.getElementById('status');
            if (action === 'start') {
                startBtn.disabled = true;
                stopBtn.disabled = false;
                statusDiv.textContent = "Status: Connecting...";
                statusDiv.className = "status";
            } else {
                startBtn.disabled = false;
                stopBtn.disabled = true;
                statusDiv.textContent = "Status: Offline";
                statusDiv.className = "status offline";
            }
            fetch(/camera/${action}, {method: 'POST'})
                .then(res => res.json())
                .then(data => {
                    if (action === 'start') {
                        statusDiv.textContent = "Status: Active";
                        statusDiv.className = "status online";
                    }
                })
                .catch(err => {
                    console.error('Error:', err);
                    startBtn.disabled = false;
                    stopBtn.disabled = true;
                    statusDiv.textContent = "Status: Error";
                    statusDiv.className = "status offline";
                });
        }
        </script>
    </body>
    </html>
    """

if __name__ == '_main_':
    app.run(host='0.0.0.0', port=5000, threaded=True)