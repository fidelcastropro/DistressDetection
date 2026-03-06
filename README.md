# Distress Detection System

A real-time pose detection system that monitors for alerting poses and automatically triggers emergency alerts via SMS, WhatsApp, and phone calls.

## Features

- **Real-time Pose Detection**: Uses MediaPipe to detect alerting poses through webcam
- **Emergency Alerts**: Automatically sends alerts via:
  - WhatsApp messages
  - SMS notifications
  - Phone calls
- **Live Video Feed**: Web-based interface with live camera stream
- **Location Sharing**: Sends Google Maps location link in emergency alerts
- **Public Access**: Uses ngrok to create publicly accessible URLs for emergency contacts

## How It Works

When the pre-defined Alerting pose is detected.It triggers an emergency alert with:
- Live video feed URL
- Current location coordinates
- Audio alarm

The predefined gesture is:

1. Raise both hands above the shoulders  
2. Move both arms inward  
3. Cross the arms in front of the body  

This gesture is intentionally simple so that a person can perform it **even in stressful situations**.

When the system detects this gesture consistently for several frames, it triggers an emergency alert.

## Requirements

```
flask
opencv-python
mediapipe
numpy
pygame
twilio
pyngrok
```

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd DistressDetection
```

2. Install dependencies:
```bash
pip install flask opencv-python mediapipe numpy pygame twilio pyngrok
```

3. Add an alarm sound file named `Alrm.mp3` in the project directory

## Configuration

Edit the following variables in `distressModel.py`:

```python
TWILIO_ACCOUNT_SID = 'your_account_sid'
TWILIO_AUTH_TOKEN = 'your_auth_token'
TWILIO_PHONE_NUMBER = 'your_twilio_phone'
TWILIO_WHATSAPP_NUMBER = 'whatsapp:+14155238886'
RECIPIENT_PHONE = 'recipient_phone_number'
RECIPIENT_WHATSAPP = 'whatsapp:recipient_phone_number'
LATITUDE = your_latitude
LONGITUDE = your_longitude
```

## Usage

1. Run the application:
```bash
python distressModel.py
```

2. Access the web interface at the ngrok URL displayed in the console

3. Click "Start" to begin monitoring

4. The system will automatically detect danger poses and send alerts

## API Endpoints

- `GET /` - Web interface
- `GET /video_feed` - Live video stream
- `POST /camera/start` - Start camera monitoring
- `POST /camera/stop` - Stop camera monitoring
- `GET /live` - Emergency access redirect

## Technical Details

- **Pose Detection**: MediaPipe Pose with 70% confidence threshold
- **Danger Pose Criteria**: Arms raised above eyes with angle > 70°
- **Alert Cooldown**: 30 seconds between alerts
- **Frame Processing**: Multi-threaded for optimal performance

## Security Note

⚠️ **Important**: Remove or replace Twilio credentials before pushing to public repositories. Use environment variables for sensitive data.