#!/bin/bash

cd /home/sudha/programing/mark-IV

# Activate virtualenv
source venv/bin/activate

# Start Piper TTS server if not running
if ! curl -s -X POST http://localhost:59125/ -H "Content-Type: application/json" -d '{"text":"test"}' > /dev/null 2>&1; then
    echo "Starting Piper TTS server..."
    nohup python -m piper.http_server --port 59125 -m ~/piper-voices/en_US-amy-medium.onnx > /tmp/piper.log 2>&1 &
    sleep 3
fi

# Start Jarvis GUI
echo "Starting Jarvis..."
python jarvis_gui.py
