#!/usr/bin/env python3
"""
Jarvis Voice Assistant - Simple GUI
"""

import threading
import queue
import logging
import math
import tkinter as tk
import customtkinter as ctk
from jarvis_assistant import JarvisAssistant

BG_DARK = "#0a0a0f"
BG_PANEL = "#0d0d14"
TEXT_CYAN = "#00d4ff"
TEXT_WHITE = "#e0e0e0"
TEXT_GREEN = "#00ff88"
TEXT_DIM = "#4a6a8a"

ctk.set_appearance_mode("dark")


class LogHandler(logging.Handler):
    def __init__(self, log_queue):
        super().__init__()
        self.log_queue = log_queue

    def emit(self, record):
        self.log_queue.put(self.format(record))


class JarvisGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        self.title("J.A.R.V.I.S.")
        self.geometry("400x600")
        self.configure(fg_color=BG_DARK)

        self.log_queue = queue.Queue()
        self.assistant = None
        self.running = False
        self._viz_state = "IDLE"

        self.log_handler = LogHandler(self.log_queue)
        self.log_handler.setFormatter(
            logging.Formatter(
                "%(asctime)s [%(levelname)s] %(message)s", datefmt="%H:%M:%S"
            )
        )

        self._build_ui()
        self._process_log_queue()

    def _build_ui(self):
        self._viz_initialized = False
        self._current_amplitude = 0.5
        self._amplitude_index = 0

        # Title at top center
        title = ctk.CTkLabel(
            self, text="J.A.R.V.I.S.", font=("Arial", 28, "bold"), text_color=TEXT_CYAN
        )
        title.pack(pady=(20, 10))

        # Circular Audio Visualizer
        import random

        self.arc_canvas = tk.Canvas(
            self, width=220, height=220, bg=BG_DARK, highlightthickness=0
        )
        self.arc_canvas.pack(pady=10, anchor="center")

        # Create wobbling circle
        center = 110
        self._viz_time = 0
        self._base_radius = 80
        num_points = 96

        self._viz_points = []
        for i in range(num_points):
            angle = (i / num_points) * 2 * math.pi
            self._viz_points.append(
                {
                    "angle": angle,
                    "base_offset": 0,
                    "wave_offset": random.uniform(0, 2 * math.pi),
                }
            )

        # Create initial circle points
        center = 110
        base_radius = 80
        initial_points = []
        for i in range(96):
            angle = (i / 96) * 2 * math.pi
            x = center + base_radius * math.cos(angle)
            y = center + base_radius * math.sin(angle)
            initial_points.extend([x, y])

        self.vis_circle = self.arc_canvas.create_polygon(
            initial_points, outline=TEXT_DIM, fill="", width=3
        )

        # State label
        self.state_label = ctk.CTkLabel(
            self, text="IDLE", font=("Arial", 14, "bold"), text_color=TEXT_DIM
        )
        self.state_label.pack(pady=(20, 0))

        # Start visualizer animation
        self._viz_initialized = True
        self._animate_visualizer()

        # Log display
        self.log_text = ctk.CTkTextbox(
            self,
            font=("Arial", 11),
            fg_color=BG_PANEL,
            text_color=TEXT_WHITE,
            border_width=0,
            wrap="word",
            width=370,
            height=120,
        )
        self.log_text.pack(padx=10, pady=10)
        self.log_text.configure(state="disabled")

        # Text input
        self.input_entry = ctk.CTkEntry(
            self,
            placeholder_text="Type message...",
            font=("Arial", 12),
            fg_color=BG_PANEL,
            border_color="#333333",
            width=370,
        )
        self.input_entry.pack(padx=10, pady=(0, 10))
        self.input_entry.bind("<Return>", lambda e: self._send_input())

        # Buttons frame at bottom
        btn_frame = ctk.CTkFrame(self, fg_color=BG_DARK)
        btn_frame.pack(pady=(10, 20))

        self.start_btn = ctk.CTkButton(
            btn_frame,
            text="INITIALIZE",
            width=120,
            fg_color="#0066cc",
            command=self._start,
        )
        self.start_btn.pack(side="left", padx=10)

        self.stop_btn = ctk.CTkButton(
            btn_frame,
            text="TERMINATE",
            width=120,
            fg_color="#cc3333",
            state="disabled",
            command=self._stop,
        )
        self.stop_btn.pack(side="left", padx=10)

    def _start(self):
        self.assistant = JarvisAssistant(
            log_handler=self.log_handler, on_speaking_done=self._on_speaking_done
        )
        self.assistant_thread = threading.Thread(target=self.assistant.run, daemon=True)
        self.assistant_thread.start()

        self.running = True
        self._set_state("LISTENING")

        self.start_btn.configure(state="disabled")
        self.stop_btn.configure(state="normal")

    def _stop(self):
        if self.assistant:
            self.assistant.stop()
        self.running = False
        self._set_state("STOPPED")
        self.start_btn.configure(state="normal")
        self.stop_btn.configure(state="disabled")

    def _on_speaking_done(self):
        self._set_state("LISTENING")

    def _set_state(self, state):
        self._viz_state = state
        color = TEXT_CYAN
        if state == "STOPPED":
            color = TEXT_DIM
        elif state == "SPEAKING":
            color = TEXT_GREEN
        elif state == "THINKING":
            color = "#ffaa00"
        self.state_label.configure(text=state, text_color=color)

    def _animate_visualizer(self):
        if not self._viz_initialized:
            print("VIZ: not initialized, rescheduling")
            self.after(50, self._animate_visualizer)
            return

        state_text = self._viz_state
        is_speaking = "SPEAKING" in state_text
        is_wake = "WAKE" in state_text
        center = 110
        base_radius = self._base_radius
        self._viz_time += 0.15

        # Build polygon points
        polygon_points = []

        # Force color based on state
        if is_wake:
            circle_color = "yellow"
        elif is_speaking:
            circle_color = "cyan"
        else:
            circle_color = TEXT_DIM

        for point in self._viz_points:
            angle = point["angle"]
            wave_offset = point["wave_offset"]

            if is_wake:
                # Yellow for wake detected
                wave1 = math.sin(self._viz_time + wave_offset) * 3
                wave2 = math.sin(self._viz_time * 1.7 + wave_offset * 0.7) * 1.5
                wave3 = math.sin(self._viz_time * 2.3 + wave_offset * 1.3) * 0.5
                radius = base_radius + wave1 + wave2 + wave3
                circle_color = "yellow"
            elif is_speaking:
                # Cyan for speaking
                wave1 = math.sin(self._viz_time + wave_offset) * 3
                wave2 = math.sin(self._viz_time * 1.7 + wave_offset * 0.7) * 1.5
                wave3 = math.sin(self._viz_time * 2.3 + wave_offset * 1.3) * 0.5
                radius = base_radius + wave1 + wave2 + wave3
                wave_amplitude = abs(wave1 + wave2 + wave3) / 5
                intensity = int(120 + wave_amplitude * 40)
                circle_color = (
                    f"#{0:02x}{min(255, intensity):02x}{min(255, intensity):02x}"
                )
            else:
                radius = base_radius

            polygon_points.append(
                (center + radius * math.cos(angle), center + radius * math.sin(angle))
            )

        flat_points = []
        for p in polygon_points:
            flat_points.extend(p)

        self.arc_canvas.coords(self.vis_circle, *flat_points)
        self.arc_canvas.itemconfig(self.vis_circle, outline=circle_color)

        self.after(30, self._animate_visualizer)

    def _send_input(self):
        text = self.input_entry.get().strip()
        if text and self.assistant and self.assistant.ai:
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"You: {text}\n")
            self.log_text.configure(state="disabled")

            response = self.assistant.ai.generate_response(text)
            self.log_text.configure(state="normal")
            self.log_text.insert("end", f"JARVIS: {response}\n\n")
            self.log_text.see("end")
            self.log_text.configure(state="disabled")

            self.assistant.ai.speak(response)
        self.input_entry.delete(0, "end")

    def _process_log_queue(self):
        try:
            while True:
                msg = self.log_queue.get_nowait()
                self.log_text.configure(state="normal")
                self.log_text.insert("end", msg + "\n")
                self.log_text.see("end")
                self.log_text.configure(state="disabled")

                if "WAKE WORD" in msg:
                    self._set_state("WAKE")
                    self.after(
                        5000,
                        lambda: self._set_state("LISTENING"),
                    )
                elif "Listening" in msg or "Say 'Jarvis'" in msg:
                    self._set_state("LISTENING")
                elif "JARVIS:" in msg:
                    self._set_state("SPEAKING")
                elif "Processing" in msg:
                    self._set_state("THINKING")
        except queue.Empty:
            pass
        self.after(100, self._process_log_queue)


if __name__ == "__main__":
    app = JarvisGUI()
    app.mainloop()
