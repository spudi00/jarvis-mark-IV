# JARVIS Mark-IV

Voice assistant powered by Ollama (Qwen3.5) with Piper TTS and custom GUI.

## Features

- **Wake word**: Say "Jarvis" to activate (5-second listen mode)
- **AI responses**: Local Ollama model for natural conversation
- **Text-to-speech**: Piper TTS (primary) with espeak fallback
- **Open apps/websites**: "open youtube", "launch firefox", etc.
- **Search**: "search youtube [query]", "search google [query]"
- **File system tools**: read, write, list, find, run commands, sysinfo
- **Animated visualizer**: Yellow on wake, cyan while speaking

## Installation

```bash
# Clone the repo
git clone https://github.com/spudi00/jarvis-mark-IV.git
cd jarvis-mark-IV

# Create virtual environment
python -m venv venv
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt
```

### System Dependencies

- **Ubuntu/Debian**: `sudo apt install portaudio19-dev ffmpeg espeak`
- **Arch/Manjaro**: `sudo pacman -S portaudio ffmpeg espeak`
- **Fedora**: `sudo dnf install portaudio-devel ffmpeg espeak`

### Ollama Setup

Make sure [Ollama](https://github.com/ollama/ollama) is installed and the model is pulled:

```bash
ollama run qwen3.5:2b
```

### Piper TTS Setup

Download a Piper voice model and start the HTTP server:

```bash
# Start Piper TTS server
python -m piper.http_server --port 59125 -m ~/piper-voices/en_US-amy-medium.onnx
```

## Usage

```bash
# Start everything (Piper + GUI)
./start_jarvis.sh

# Or run GUI directly
python jarvis_gui.py
```

## Commands

- "Jarvis" - Activate voice assistant
- "Jarvis open [app/site]" - Open app or website
- "Jarvis search youtube [query]" - Search
- "read [path]" - Read file contents
- "write [content] to [path]" - Write to file
- "ls [path]" - List directory
- "run [command]" - Execute shell command
- "find [pattern]" - Search for files
- "sysinfo" - Show system specs

## Files

- `jarvis_gui.py` - GUI with animated circular visualizer
- `jarvis_assistant.py` - Wake word detection & command handling
- `ollama_speech.py` - AI + TTS module
- `start_jarvis.sh` - Launcher script (starts Piper + GUI)
