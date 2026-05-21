#!/usr/bin/env python3
"""
Ollama AI Speech Module for Jarvis
Uses local Ollama model (Qwen3.5) for AI responses
Uses Piper TTS for voice output
"""

import os
import threading
import random
import io
import pygame
import subprocess
import requests
import ollama

FALLBACK_RESPONSES = {
    "greeting": [
        "At your service, sir.",
        "Greetings, sir. How may I assist you?",
        "JARVIS online and ready, sir.",
        "Good to see you, sir. What can I do for you?",
    ],
    "name": [
        "I am JARVIS, sir. Your personal assistant.",
        "I am JARVIS, at your service, sir.",
        "JARVIS here, sir. How may I help?",
    ],
    "time": [
        "The current time is {time}, sir.",
        "It is {time}, sir.",
        "Sir, the time is now {time}.",
    ],
    "date": [
        "Today is {date}, sir.",
        "The date is {date}, sir.",
    ],
    "affirmative": [
        "Certainly, sir.",
        "Right away, sir.",
        "As you wish, sir.",
        "Indeed, sir.",
        "Very well, sir.",
    ],
    "negative": [
        "I'm afraid not, sir.",
        "Unfortunately not, sir.",
        "Regrettably, that's not possible, sir.",
    ],
    "unknown": [
        "I'm not certain about that, sir.",
        "I don't have information on that matter, sir.",
        "I'm unable to assist with that, sir.",
        "My apologies, sir, but I don't understand.",
    ],
    "weather": [
        "I'm unable to check weather conditions at the moment, sir.",
        "Weather data is currently unavailable, sir.",
    ],
    "reminder": [
        "I'll keep that in mind, sir.",
        "Noted, sir.",
        "I've made a note of that, sir.",
    ],
    "farewell": [
        "Goodbye, sir.",
        "Until next time, sir.",
        "Standing by, sir.",
    ],
}

KEYWORD_PATTERNS = {
    "greeting": [
        "hello",
        "hi",
        "hey",
        "jarvis",
        "good morning",
        "good evening",
        "good afternoon",
    ],
    "name": ["name", "who are you", "what are you"],
    "time": ["time", "clock", "hour"],
    "date": ["date", "day", "today"],
    "affirmative": ["yes", "yeah", "correct", "right", "okay", "ok"],
    "negative": ["no", "nope", "wrong", "incorrect"],
    "weather": ["weather", "temperature", "rain", "sunny", "cold", "hot"],
    "reminder": ["remember", "note", "remind", "don't forget"],
    "farewell": ["bye", "goodbye", "see you", "later", "quit", "exit"],
}


class OllamaSpeech:
    def __init__(self, model="qwen3.5:2b", file_system=None):
        self.model = model
        self.on_speaking_done = None
        self.fs = file_system

        pygame.mixer.init()

        self._speaking = False
        self._should_stop = False
        self._lock = threading.Lock()

        try:
            ollama.list()
            print(f"Ollama connected, using model: {model}")
        except Exception as e:
            print(f"Ollama connection error: {e}")

    def generate_response(self, user_input):
        if not self.fs:
            return "File system not initialized"

        cmd_lower = user_input.lower().strip()

        if cmd_lower.startswith("read ") or cmd_lower.startswith("file "):
            path = (
                user_input.split(maxsplit=1)[1] if len(user_input.split()) > 1 else ""
            )
            return self.fs.read(path)

        if cmd_lower.startswith("write ") or cmd_lower.startswith("save "):
            parts = user_input.split(" to ", 1)
            if len(parts) == 2:
                content, path = parts[0].split(maxsplit=1)[1], parts[1]
            else:
                parts = user_input.split(maxsplit=2)
                content, path = parts[1], parts[2] if len(parts) > 2 else ""
            return self.fs.write(path, content)

        if (
            cmd_lower.startswith("list ")
            or cmd_lower.startswith("ls ")
            or cmd_lower == "list"
            or cmd_lower == "ls"
        ):
            parts = user_input.split(maxsplit=1)
            path = parts[1] if len(parts) > 1 else "."
            return self.fs.list(path)

        if (
            cmd_lower.startswith("run ")
            or cmd_lower.startswith("execute ")
            or cmd_lower.startswith("cmd ")
        ):
            command = (
                user_input.split(maxsplit=1)[1] if len(user_input.split()) > 1 else ""
            )
            return self.fs.run(command)

        if cmd_lower.startswith("find ") or cmd_lower.startswith("search "):
            parts = user_input.split()
            if " in " in user_input:
                pattern, path = user_input.split(" in ", 1)
                pattern = (
                    pattern.split(maxsplit=1)[1] if len(pattern.split()) > 1 else "*"
                )
            else:
                pattern = parts[1] if len(parts) > 1 else "*"
                path = parts[-1] if len(parts) > 2 else "."
            return self.fs.find(pattern, path)

        if cmd_lower.startswith("cd ") or cmd_lower.startswith("change directory "):
            path = (
                user_input.split(maxsplit=1)[1] if len(user_input.split()) > 1 else "~"
            )
            try:
                os.chdir(os.path.expanduser(path))
                return f"Changed directory to {os.getcwd()}"
            except Exception as e:
                return f"Error: {e}"

        if cmd_lower.startswith("pwd"):
            return os.getcwd()

        if cmd_lower.startswith("mkdir ") or cmd_lower.startswith("create folder "):
            path = (
                user_input.split(maxsplit=1)[1] if len(user_input.split()) > 1 else ""
            )
            try:
                os.makedirs(path, exist_ok=True)
                return f"Created folder {path}"
            except Exception as e:
                return f"Error: {e}"

        if cmd_lower.startswith("rm ") or cmd_lower.startswith("delete "):
            path = (
                user_input.split(maxsplit=1)[1] if len(user_input.split()) > 1 else ""
            )
            try:
                if os.path.isdir(path):
                    os.rmdir(path)
                else:
                    os.remove(path)
                return f"Deleted {path}"
            except Exception as e:
                return f"Error: {e}"

        if any(
            kw in cmd_lower
            for kw in [
                "specs",
                "system info",
                "pc specs",
                "hardware",
                "cpu",
                "memory",
                "gpu",
                "disk",
            ]
        ):
            return self.fs.sysinfo()

        with self._lock:
            try:
                response = ollama.generate(
                    model=self.model,
                    prompt=f"User: {user_input}",
                    options={"num_predict": 100, "temperature": 0.6},
                )

                response_text = response.get("response", "").strip()

                if not response_text or len(response_text) < 3:
                    response_text = self._get_fallback_response(user_input)

                return response_text
            except Exception as e:
                print(f"Ollama error: {e}")
                return self._get_fallback_response(user_input)

    def _detect_intent(self, text):
        text_lower = text.lower()
        for intent, patterns in KEYWORD_PATTERNS.items():
            for pattern in patterns:
                if pattern in text_lower:
                    return intent
        return "unknown"

    def _get_fallback_response(self, user_input):
        import datetime

        now = datetime.datetime.now()

        intent = self._detect_intent(user_input)

        if intent == "time":
            time_str = now.strftime("%I:%M %p")
            responses = [r.format(time=time_str) for r in FALLBACK_RESPONSES["time"]]
            return random.choice(responses)
        elif intent == "date":
            date_str = now.strftime("%A, %B %d, %Y")
            responses = [r.format(date=date_str) for r in FALLBACK_RESPONSES["date"]]
            return random.choice(responses)
        elif intent in FALLBACK_RESPONSES:
            return random.choice(FALLBACK_RESPONSES[intent])
        else:
            return random.choice(FALLBACK_RESPONSES["unknown"])

    def speak(self, text, async_mode=True):
        if async_mode:
            thread = threading.Thread(
                target=self._speak_sync, args=(text,), daemon=True
            )
            thread.start()
            return thread
        else:
            return self._speak_sync(text)

    def _speak_piper(self, text):
        PIPER_URL = "http://localhost:59125/"

        try:
            response = requests.post(
                PIPER_URL,
                json={"text": text},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

            audio_file = io.BytesIO(response.content)
            pygame.mixer.music.load(audio_file)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy() and not self._should_stop:
                pygame.time.Clock().tick(10)

            if self._should_stop:
                pygame.mixer.music.stop()

        except requests.exceptions.ConnectionError:
            print(
                f"Piper not running. Start with: python -m piper.http_server --port 59125 -m ~/piper-voices/en_US-amy-medium.onnx"
            )
            self._speak_fallback(text)
        except Exception as e:
            print(f"Piper TTS Error: {e}")
            self._speak_fallback(text)

    def _speak_fallback(self, text):
        try:
            import tempfile

            temp_file = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_file.close()

            subprocess.run(
                ["espeak", "-w", temp_file.name, text],
                capture_output=True,
                timeout=30,
            )

            pygame.mixer.music.load(temp_file.name)
            pygame.mixer.music.play()

            while pygame.mixer.music.get_busy() and not self._should_stop:
                pygame.time.Clock().tick(10)

            if self._should_stop:
                pygame.mixer.music.stop()

            os.unlink(temp_file.name)
        except Exception as e:
            print(f"Fallback TTS Error: {e}")

    def _get_audio_amplitude(self, text):
        try:
            import tempfile
            import numpy as np
            import soundfile as sf

            PIPER_URL = "http://localhost:59125/"

            response = requests.post(
                PIPER_URL,
                json={"text": text},
                headers={"Content-Type": "application/json"},
                timeout=30,
            )
            response.raise_for_status()

            temp_wav = tempfile.NamedTemporaryFile(suffix=".wav", delete=False)
            temp_wav.close()
            with open(temp_wav.name, "wb") as f:
                f.write(response.content)

            data, samplerate = sf.read(temp_wav.name)

            if len(data.shape) > 1:
                data = data.mean(axis=1)

            target_points = 20
            step = max(1, len(data) // target_points)
            amplitudes = []

            for i in range(0, len(data), step):
                chunk = data[i : i + step]
                amplitude = np.abs(chunk).mean() if len(chunk) > 0 else 0
                amplitudes.append(float(amplitude))

            if amplitudes and max(amplitudes) > 0:
                amplitudes = [a / max(amplitudes) for a in amplitudes]
            else:
                amplitudes = [0.5] * 20

            os.unlink(temp_wav.name)

            return amplitudes

        except Exception as e:
            print(f"Audio analysis error: {e}")
            return [0.5] * 20

    def _speak_sync(self, text):
        with self._lock:
            self._speaking = True
            try:
                self._speak_piper(text)
            except Exception as e:
                print(f"TTS Error: {e}")
            finally:
                self._speaking = False
                self._should_stop = False
                if self.on_speaking_done:
                    self.on_speaking_done()

    def stop_speaking(self):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
            pygame.mixer.init()
        except:
            pass
        self._speaking = False
        self._should_stop = True

    def is_speaking(self):
        with self._lock:
            return self._speaking

    def __del__(self):
        try:
            pygame.mixer.music.stop()
            pygame.mixer.quit()
        except:
            pass
