#!/usr/bin/env python3
"""
Voice Assistant - Listens for "Jarvis" wake word and responds with AI.
"""

import subprocess
import threading
import time
import logging
import os
import glob as glob_module

import speech_recognition as sr

from ollama_speech import OllamaSpeech

SAMPLE_RATE = 44100

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger("jarvis")

KNOWN_SITES = {
    "youtube": "https://youtube.com",
    "facebook": "https://facebook.com",
    "twitter": "https://twitter.com",
    "instagram": "https://instagram.com",
    "reddit": "https://reddit.com",
    "netflix": "https://netflix.com",
    "twitch": "https://twitch.tv",
    "gmail": "https://gmail.com",
    "google": "https://google.com",
    "github": "https://github.com",
    "amazon": "https://amazon.com",
    "wikipedia": "https://wikipedia.org",
}

KNOWN_APPS = {
    "firefox": "firefox",
    "chrome": "google-chrome",
    "chromium": "chromium",
    "code": "code",
    "vscode": "code",
    "terminal": "x-terminal-emulator",
    "thunar": "thunar",
    "nautilus": "nautilus",
    "discord": "discord",
    "spotify": "spotify",
    "slack": "slack",
    "obs": "obs",
    "vlc": "vlc",
    "gimp": "gimp",
    "inkscape": "inkscape",
    "libreoffice": "libreoffice",
    "steam": "steam",
    "lutris": "lutris",
    "heroic": "heroic",
}


class FileSystem:
    def read(self, path):
        try:
            with open(path, "r") as f:
                content = f.read()
            return f"File content of {path}:\n{content}"
        except Exception as e:
            return f"Error reading {path}: {e}"

    def write(self, path, content):
        try:
            with open(path, "w") as f:
                f.write(content)
            return f"Written to {path}"
        except Exception as e:
            return f"Error writing to {path}: {e}"

    def list(self, path="."):
        try:
            items = os.listdir(path)
            return f"Contents of {path}:\n" + "\n".join(items)
        except Exception as e:
            return f"Error listing {path}: {e}"

    def run(self, command):
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=30,
            )
            output = result.stdout or result.stderr
            return (
                f"Command output:\n{output}"
                if output
                else "Command completed with no output"
            )
        except Exception as e:
            return f"Error running command: {e}"

    def find(self, pattern, path="."):
        try:
            matches = glob_module.glob(
                os.path.join(path, "**", pattern), recursive=True
            )
            if matches:
                return f"Found {len(matches)} matches:\n" + "\n".join(matches[:20])
            return "No matches found"
        except Exception as e:
            return f"Error searching: {e}"

    def sysinfo(self):
        import platform
        import subprocess

        info = []
        info.append(f"OS: {platform.system()} {platform.release()}")
        info.append(f"Kernel: {platform.version()}")
        info.append(f"Machine: {platform.machine()}")

        try:
            result = subprocess.run(["nproc"], capture_output=True, text=True)
            info.append(f"CPU Cores: {result.stdout.strip()}")
        except:
            pass

        try:
            result = subprocess.run(["free", "-h"], capture_output=True, text=True)
            info.append(f"Memory:\n{result.stdout}")
        except:
            pass

        try:
            result = subprocess.run(
                ["lspci", "-v", "-m"], capture_output=True, text=True
            )
            gpu_lines = [
                l
                for l in result.stdout.split("\n")
                if "VGA" in l or "NVIDIA" in l or "AMD" in l or "Radeon" in l
            ]
            if gpu_lines:
                info.append(f"GPU: {gpu_lines[0]}")
        except:
            pass

        try:
            result = subprocess.run(["df", "-h", "/"], capture_output=True, text=True)
            info.append(f"Disk:\n{result.stdout}")
        except:
            pass

        return "\n".join(info)


class JarvisAssistant:
    def __init__(self, log_handler=None, enable_ai=True, on_speaking_done=None):
        if log_handler:
            log.addHandler(log_handler)

        self._state_lock = threading.Lock()
        self._running = False
        self._stop_event = threading.Event()

        self.enable_ai = enable_ai
        self.ai = None
        self.fs = FileSystem()
        if enable_ai:
            try:
                self.ai = OllamaSpeech(model="qwen3.5:2b", file_system=self.fs)
                if on_speaking_done:
                    self.ai.on_speaking_done = on_speaking_done
                log.info("JARVIS AI speech module initialized (Ollama - Qwen3.5:2b)")
            except Exception as e:
                log.error(f"Failed to initialize AI: {e}")
                self.ai = None
                self.enable_ai = False

    def _get_input_device_index(self):
        import pyaudio

        pa = pyaudio.PyAudio()
        for name in ["pipewire", "pulse", "default"]:
            for i in range(pa.get_device_count()):
                info = pa.get_device_info_by_index(i)
                if (
                    name.lower() in info["name"].lower()
                    and info.get("maxInputChannels", 0) > 0
                ):
                    log.info(f"Using input device: {info['name']} (index {i})")
                    return i
        for i in range(pa.get_device_count()):
            info = pa.get_device_info_by_index(i)
            if info.get("maxInputChannels", 0) > 0:
                return i
        raise RuntimeError("No input devices found")

    def _open_anything(self, name):
        name = name.lower().strip()

        if name in KNOWN_APPS:
            app = KNOWN_APPS[name]
            try:
                subprocess.Popen(
                    [app],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
                log.info(f"Launched app: {app}")
                return True
            except Exception as e:
                log.error(f"Failed to launch {app}: {e}")

        if name in KNOWN_SITES:
            url = KNOWN_SITES[name]
            try:
                subprocess.Popen(
                    ["xdg-open", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                log.info(f"Opened: {url}")
                return True
            except Exception as e:
                log.error(f"Failed to open {url}: {e}")

        if "." in name and not name.startswith("http"):
            url = f"https://{name}"
            try:
                subprocess.Popen(
                    ["xdg-open", url],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                log.info(f"Opened: {url}")
                return True
            except Exception as e:
                log.error(f"Failed to open {url}: {e}")

        try:
            subprocess.Popen(
                [name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                start_new_session=True,
            )
            log.info(f"Launched: {name}")
            return True
        except:
            pass

        try:
            result = subprocess.run(
                ["xdg-open", name],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=5,
            )
            if result.returncode == 0:
                log.info(f"Opened: {name}")
                return True
        except Exception as e:
            log.error(f"Failed to open {name}: {e}")

        return False

    def _search(self, site, query):
        if site == "youtube":
            url = f"https://youtube.com/results?search_query={query.replace(' ', '+')}"
        elif site == "google":
            url = f"https://google.com/search?q={query.replace(' ', '+')}"
        elif site == "reddit":
            url = f"https://www.reddit.com/search/?q={query.replace(' ', '+')}"
        else:
            url = f"https://{site}.com/search?q={query.replace(' ', '+')}"

        try:
            subprocess.Popen(
                ["xdg-open", url], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
            )
            log.info(f"Searching {site} for: {query}")
            return True
        except Exception as e:
            log.error(f"Failed to search: {e}")
            return False

    def _listen_for_jarvis(self, device_index):
        recognizer = sr.Recognizer()
        recognizer.energy_threshold = 300
        recognizer.dynamic_energy_threshold = True
        recognizer.pause_threshold = 0.8

        microphone = sr.Microphone(sample_rate=SAMPLE_RATE, device_index=device_index)

        with microphone as source:
            log.info("Calibrating microphone for ambient noise...")
            recognizer.adjust_for_ambient_noise(source, duration=2)
            log.info("Wake word listener started. Say 'Jarvis' to begin.")

        while not self._stop_event.is_set():
            try:
                with microphone as source:
                    audio = recognizer.listen(source, timeout=1, phrase_time_limit=5)

                text = recognizer.recognize_google(audio).lower()
                log.info(f"Heard: '{text}'")

                if "jarvis" in text:
                    if self.enable_ai and self.ai:
                        command = text.replace("jarvis", "").strip().lower()
                        if command:
                            # Has command, process it
                            open_keywords = [
                                "open ",
                                "launch ",
                                "can you open ",
                                "could you open ",
                                "open the ",
                                "start ",
                                "run ",
                            ]
                            is_open_cmd = False
                            for kw in open_keywords:
                                if command.startswith(kw):
                                    is_open_cmd = True
                                    break

                            if is_open_cmd or any(
                                command.startswith(kw)
                                for kw in ["open ", "launch ", "start ", "run "]
                            ):
                                # Handle open command
                                target = command
                                for kw in [
                                    "open ",
                                    "launch ",
                                    "start ",
                                    "run ",
                                    "can you ",
                                    "could you ",
                                    "open the ",
                                    "the ",
                                ]:
                                    target = target.replace(kw, " ", 1)
                                target = target.strip()

                                if "search" in target:
                                    target = target.replace("and", " ")
                                    parts = (
                                        target.replace("search", " ").strip().split()
                                    )
                                    if len(parts) >= 2:
                                        site = (
                                            parts[0]
                                            if parts[0] in KNOWN_SITES
                                            else "youtube"
                                        )
                                        query = (
                                            " ".join(parts[1:])
                                            if parts[0] in KNOWN_SITES
                                            else " ".join(parts)
                                        )
                                        if self._search(site, query):
                                            response = f"Searching {site} for {query}"
                                        else:
                                            response = "Sorry, couldn't perform search"
                                else:
                                    if self._open_anything(target):
                                        response = f"Opening {target}, sir"
                                    else:
                                        response = f"Sorry, I couldn't open {target}"

                                log.info(f"JARVIS: {response}")
                                self.ai.speak(response)
                            else:
                                # AI command
                                log.info(f"Processing command: '{command}'")
                                response = self.ai.generate_response(command)
                                log.info(f"JARVIS: {response}")
                                self.ai.speak(response)
                        else:
                            # Just wake word, enter listen mode for 5 seconds
                            log.info("WAKE WORD DETECTED - Listening for command...")
                            listen_start = time.time()
                            while time.time() - listen_start < 5:
                                try:
                                    with microphone as source:
                                        audio = recognizer.listen(
                                            source, timeout=1, phrase_time_limit=5
                                        )
                                    cmd_text = recognizer.recognize_google(
                                        audio
                                    ).lower()
                                    log.info(f"Heard command: '{cmd_text}'")

                                    # Remove "jarvis" if present, otherwise use entire phrase
                                    cmd = cmd_text.replace("jarvis", "").strip()
                                    if cmd:
                                        # Check for open commands (only direct action verbs)
                                        open_keywords = [
                                            "open ",
                                            "launch ",
                                            "start ",
                                            "run ",
                                        ]
                                        is_open_cmd = any(
                                            cmd.startswith(kw) for kw in open_keywords
                                        )

                                        if is_open_cmd:
                                            target = cmd
                                            for kw in [
                                                "open ",
                                                "launch ",
                                                "start ",
                                                "run ",
                                            ]:
                                                target = target.replace(kw, " ", 1)
                                            target = target.strip()

                                            if "search" in target:
                                                target = target.replace("and", " ")
                                                parts = (
                                                    target.replace("search", " ")
                                                    .strip()
                                                    .split()
                                                )
                                                if len(parts) >= 2:
                                                    site = (
                                                        parts[0]
                                                        if parts[0] in KNOWN_SITES
                                                        else "youtube"
                                                    )
                                                    query = (
                                                        " ".join(parts[1:])
                                                        if parts[0] in KNOWN_SITES
                                                        else " ".join(parts)
                                                    )
                                                    if self._search(site, query):
                                                        response = f"Searching {site} for {query}"
                                                    else:
                                                        response = "Sorry, couldn't perform search"
                                            else:
                                                if self._open_anything(target):
                                                    response = f"Opening {target}"
                                                else:
                                                    response = f"Sorry, I couldn't open {target}"

                                            log.info(f"JARVIS: {response}")
                                            self.ai.speak(response)
                                        else:
                                            # Regular AI command
                                            log.info(f"Processing: '{cmd}'")
                                            response = self.ai.generate_response(cmd)
                                            log.info(f"JARVIS: {response}")
                                            self.ai.speak(response)
                                        break
                                except sr.WaitTimeoutError:
                                    continue
                                except sr.UnknownValueError:
                                    pass
                                except Exception as e:
                                    log.error(f"Listen mode error: {e}")
                                    break
                                except sr.WaitTimeoutError:
                                    continue
                                except sr.UnknownValueError:
                                    pass
                                except Exception as e:
                                    log.error(f"Listen mode error: {e}")
                                    break
                                except sr.WaitTimeoutError:
                                    continue
                                except sr.UnknownValueError:
                                    pass
                                except Exception as e:
                                    log.error(f"Listen mode error: {e}")
                                    break

            except sr.WaitTimeoutError:
                continue
            except sr.UnknownValueError:
                pass
            except sr.RequestError as e:
                log.error(f"Speech recognition service error: {e}")
                time.sleep(2)
            except Exception as e:
                log.error(f"Wake word detection error: {e}")
                time.sleep(1)

    def run(self):
        self._stop_event.clear()
        self._running = True

        log.info("=" * 50)
        log.info("Voice Assistant Ready")
        log.info("Say 'Jarvis' to activate")
        log.info("Say 'Jarvis open [app]' to open")
        log.info("Say 'Jarvis open youtube and search cats' to search")
        log.info(f"AI enabled: {self.enable_ai}")
        log.info("=" * 50)

        device_index = self._get_input_device_index()
        self._listen_for_jarvis(device_index)

    def stop(self):
        self._stop_event.set()
        self._running = False
        if self.enable_ai and self.ai:
            self.ai.stop_speaking()
        log.info("Assistant stopped.")


def main():
    assistant = JarvisAssistant()
    try:
        assistant.run()
    except KeyboardInterrupt:
        log.info("Shutting down...")
        assistant.stop()


if __name__ == "__main__":
    main()
