"""
gui.py — Dark DAW-style GUI for the Music Theory Voice Agent.
Uses only tkinter (built into Python — no extra install needed).

Run with:
    python gui.py
"""

import asyncio
import base64
import json
import os
import random
import threading
import tkinter as tk
from tkinter import font as tkfont
from tkinter import scrolledtext

from dotenv import load_dotenv

from audio import MicCapture, Speaker

# ── Colours ──────────────────────────────────────────────────────────────────
BG        = "#0d0d0f"
BG_PANEL  = "#111114"
BG_CARD   = "#18181c"
BORDER    = "#1e1e24"
GOLD      = "#c8a96e"
GOLD_DIM  = "#7a6040"
BLUE_DIM  = "#4a6a8a"
TEXT      = "#cccccc"
TEXT_DIM  = "#555555"
TEXT_MUTE = "#333333"
GREEN     = "#2ecc71"
RED       = "#e74c3c"

AGENT_URL = "wss://agents.assemblyai.com/v1/ws"

SYSTEM_PROMPT = """You are an expert music theory tutor and creative collaborator.
You have deep knowledge of scales, intervals, chords, harmony, counterpoint, chord progressions
in any genre (jazz, classical, pop, blues, R&B, folk, metal), melody construction, song structure,
and music history. Keep answers conversational, warm, and concise — the user is talking to you."""

GREETING = "Hey there! I'm your music theory assistant. Ask me anything — scales, chords, progressions, melodies — I'm here to help you create."

SESSION_CONFIG = {
    "system_prompt": SYSTEM_PROMPT,
    "greeting": GREETING,
    "input": {
        "format": {"encoding": "audio/pcm"},
        "keyterms": [
            "chord progression", "diatonic", "modulation", "pentatonic",
            "arpeggio", "cadence", "tritone", "diminished", "augmented",
            "dominant", "subdominant", "tonic", "leading tone", "counterpoint",
            "Dorian", "Phrygian", "Lydian", "Mixolydian", "Locrian",
            "ii-V-I", "circle of fifths",
        ],
        "turn_detection": {
            "vad_threshold": 0.5,
            "min_silence": 200,
            "max_silence": 1000,
            "interrupt_response": True,
        },
    },
    "output": {
        "voice": "james",
        "format": {"encoding": "audio/pcm"},
    },
}


# ── GUI ───────────────────────────────────────────────────────────────────────

class MusicAgentGUI:
    def __init__(self, root: tk.Tk, api_key: str):
        self.root = root
        self.api_key = api_key
        self.recording = False
        self.ws = None
        self.speaker = None
        self.mic = None
        self.loop = None
        self.agent_thread = None
        self.stop_event = threading.Event()

        self._build_ui()
        self._animate_bars()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self.root.title("Music Theory Agent")
        self.root.configure(bg=BG)
        self.root.geometry("860x620")
        self.root.resizable(True, True)

        mono = tkfont.Font(family="Courier", size=9)
        sans_sm = tkfont.Font(family="Helvetica", size=11)
        sans_md = tkfont.Font(family="Helvetica", size=13)
        sans_lg = tkfont.Font(family="Helvetica", size=15, weight="bold")

        # ── Title bar ──────────────────────────────────────────────────────
        titlebar = tk.Frame(self.root, bg=BG_PANEL, height=38)
        titlebar.pack(fill=tk.X)
        titlebar.pack_propagate(False)

        # Traffic lights
        tl_frame = tk.Frame(titlebar, bg=BG_PANEL)
        tl_frame.pack(side=tk.LEFT, padx=12, pady=10)
        for color in ("#ff5f57", "#febc2e", "#28c840"):
            c = tk.Canvas(tl_frame, width=12, height=12, bg=BG_PANEL, highlightthickness=0)
            c.pack(side=tk.LEFT, padx=3)
            c.create_oval(1, 1, 11, 11, fill=color, outline="")

        tk.Label(titlebar, text="MUSIC THEORY AGENT", bg=BG_PANEL,
                 fg=TEXT_DIM, font=mono).pack(side=tk.LEFT, padx=8)

        # Status indicator (right side)
        status_frame = tk.Frame(titlebar, bg=BG_PANEL)
        status_frame.pack(side=tk.RIGHT, padx=14)

        self.status_label = tk.Label(status_frame, text="idle", bg=BG_PANEL,
                                     fg=TEXT_MUTE, font=mono)
        self.status_label.pack(side=tk.RIGHT, padx=(6, 0))

        self.status_dot = tk.Canvas(status_frame, width=8, height=8,
                                    bg=BG_PANEL, highlightthickness=0)
        self.status_dot.pack(side=tk.RIGHT)
        self._dot_id = self.status_dot.create_oval(1, 1, 7, 7, fill="#333", outline="")

        # ── Body ──────────────────────────────────────────────────────────
        body = tk.Frame(self.root, bg=BG)
        body.pack(fill=tk.BOTH, expand=True)

        # Sidebar
        sidebar = tk.Frame(body, bg=BG_PANEL, width=180)
        sidebar.pack(side=tk.LEFT, fill=tk.Y)
        sidebar.pack_propagate(False)

        self._sidebar_section(sidebar, "SESSION")
        self._sidebar_item(sidebar, "♩  Conversation", active=True)
        self._sidebar_item(sidebar, "♪  Progressions")
        self._sidebar_item(sidebar, "✎  Notes")
        self._sidebar_section(sidebar, "VOICE")
        self._sidebar_item(sidebar, "⊕  Settings")
        self._sidebar_item(sidebar, "◉  Audio")

        # Meta info at bottom of sidebar
        meta = tk.Frame(sidebar, bg=BG_PANEL)
        meta.pack(side=tk.BOTTOM, fill=tk.X, padx=14, pady=12)
        for line in ("voice: james", "region: us", "model: claude"):
            tk.Label(meta, text=line, bg=BG_PANEL, fg=TEXT_MUTE,
                     font=mono, anchor="w").pack(fill=tk.X)

        # Main content area
        content = tk.Frame(body, bg=BG)
        content.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)

        # Chat area
        chat_frame = tk.Frame(content, bg=BG)
        chat_frame.pack(fill=tk.BOTH, expand=True, padx=0, pady=0)

        self.chat = scrolledtext.ScrolledText(
            chat_frame,
            bg=BG, fg=TEXT,
            font=("Helvetica", 13),
            relief=tk.FLAT,
            highlightthickness=0,
            borderwidth=0,
            wrap=tk.WORD,
            padx=20, pady=16,
            spacing3=8,
            cursor="arrow",
            state=tk.DISABLED,
        )
        self.chat.pack(fill=tk.BOTH, expand=True)

        # Tag styles
        self.chat.tag_config("agent_tag", foreground=GOLD,
                             font=("Courier", 9))
        self.chat.tag_config("agent_text", foreground="#bbbbbb",
                             font=("Helvetica", 13), lmargin1=0, lmargin2=0)
        self.chat.tag_config("user_tag", foreground=BLUE_DIM,
                             font=("Courier", 9))
        self.chat.tag_config("user_text", foreground="#afc8e0",
                             font=("Helvetica", 13))
        self.chat.tag_config("spacer", font=("Helvetica", 6))

        # Bottom panel
        bottom = tk.Frame(content, bg=BG_PANEL, height=110)
        bottom.pack(fill=tk.X)
        bottom.pack_propagate(False)

        sep = tk.Frame(bottom, bg=BORDER, height=1)
        sep.pack(fill=tk.X)

        # Visualizer bars
        viz_frame = tk.Frame(bottom, bg=BG_PANEL, height=32)
        viz_frame.pack(fill=tk.X, padx=16, pady=(10, 0))
        viz_frame.pack_propagate(False)

        self.viz_canvas = tk.Canvas(viz_frame, bg=BG_PANEL, highlightthickness=0, height=28)
        self.viz_canvas.pack(fill=tk.X, expand=True)
        self.bar_ids = []
        self._bars_ready = False

        # Controls row
        controls = tk.Frame(bottom, bg=BG_PANEL)
        controls.pack(fill=tk.X, padx=14, pady=8)

        # Mic button
        self.mic_btn = tk.Button(
            controls, text="⏺", width=3, height=1,
            bg="#1a1611", fg=GOLD,
            activebackground=GOLD, activeforeground="#111",
            relief=tk.FLAT, bd=0,
            font=("Helvetica", 16),
            cursor="hand2",
            command=self._toggle_mic,
        )
        self.mic_btn.pack(side=tk.LEFT, padx=(0, 10))

        # Text input
        self.text_var = tk.StringVar()
        self.text_input = tk.Entry(
            controls,
            textvariable=self.text_var,
            bg="#0d0d0f", fg=TEXT,
            insertbackground=GOLD,
            relief=tk.FLAT,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=GOLD_DIM,
            font=("Helvetica", 13),
        )
        self.text_input.pack(side=tk.LEFT, fill=tk.X, expand=True, ipady=7, padx=(0, 8))
        self.text_input.bind("<Return>", lambda e: self._send_text())
        self.text_input.insert(0, "")
        self.text_input.config(fg=TEXT_DIM)
        self._placeholder = "Ask about scales, chords, progressions..."
        self.text_input.insert(0, self._placeholder)
        self.text_input.bind("<FocusIn>", self._clear_placeholder)
        self.text_input.bind("<FocusOut>", self._restore_placeholder)

        send_btn = tk.Button(
            controls, text="→", width=3,
            bg=BG_PANEL, fg=GOLD,
            activebackground="#1a1611",
            relief=tk.FLAT, bd=0,
            font=("Helvetica", 15),
            cursor="hand2",
            command=self._send_text,
        )
        send_btn.pack(side=tk.LEFT)

        # Voice label
        tk.Label(controls, text="◈ james", bg=BG_PANEL,
                 fg=GOLD_DIM, font=("Courier", 10)).pack(side=tk.LEFT, padx=10)

        # Post initial greeting after short delay
        self.root.after(400, lambda: self._add_message("agent", GREETING))

    def _sidebar_section(self, parent, text):
        tk.Label(parent, text=text, bg=BG_PANEL, fg=TEXT_MUTE,
                 font=("Courier", 8), anchor="w",
                 pady=4, padx=14).pack(fill=tk.X)

    def _sidebar_item(self, parent, text, active=False):
        fg = GOLD if active else TEXT_DIM
        frame = tk.Frame(parent, bg=BG_PANEL if not active else "#18181c")
        frame.pack(fill=tk.X)
        if active:
            accent = tk.Frame(frame, bg=GOLD, width=2)
            accent.pack(side=tk.LEFT, fill=tk.Y)
        tk.Label(frame, text=text, bg=frame["bg"], fg=fg,
                 font=("Helvetica", 12), anchor="w",
                 padx=14 if not active else 12,
                 pady=7).pack(fill=tk.X, side=tk.LEFT)

    # ── Visualizer ────────────────────────────────────────────────────────────

    def _init_bars(self):
        self.viz_canvas.update_idletasks()
        w = self.viz_canvas.winfo_width()
        if w < 10:
            return
        self.bar_ids.clear()
        n_bars = max(1, w // 8)
        bar_w = max(2, w // n_bars - 2)
        for i in range(n_bars):
            x = i * (bar_w + 2) + 1
            bar_id = self.viz_canvas.create_rectangle(
                x, 26, x + bar_w, 28,
                fill="#1e1e24", outline="",
            )
            self.bar_ids.append(bar_id)
        self._bars_ready = True

    def _animate_bars(self):
        if not self._bars_ready:
            self._init_bars()
        if self._bars_ready:
            for bar_id in self.bar_ids:
                if self.recording:
                    h = random.randint(4, 26)
                    color = GOLD if h > 14 else "#2a2a30"
                else:
                    h = 4
                    color = "#1e1e24"
                coords = self.viz_canvas.coords(bar_id)
                if coords:
                    self.viz_canvas.coords(bar_id, coords[0], 28 - h, coords[2], 28)
                    self.viz_canvas.itemconfig(bar_id, fill=color)
        self.root.after(80, self._animate_bars)

    # ── Status dot ────────────────────────────────────────────────────────────

    def _set_status(self, state: str):
        """state: idle | listening | speaking | connected"""
        colors = {
            "idle": "#333333",
            "connected": GREEN,
            "listening": GOLD,
            "speaking": "#6e9ec8",
        }
        color = colors.get(state, "#333")
        self.status_dot.itemconfig(self._dot_id, fill=color)
        self.status_label.config(text=state)

    # ── Chat ─────────────────────────────────────────────────────────────────

    def _add_message(self, role: str, text: str):
        self.chat.config(state=tk.NORMAL)
        if role == "agent":
            self.chat.insert(tk.END, "agent\n", "agent_tag")
            self.chat.insert(tk.END, text + "\n", "agent_text")
        else:
            self.chat.insert(tk.END, "you\n", "user_tag")
            self.chat.insert(tk.END, text + "\n", "user_text")
        self.chat.insert(tk.END, "\n", "spacer")
        self.chat.config(state=tk.DISABLED)
        self.chat.see(tk.END)

    def _append_agent_partial(self, text: str):
        """Update the last agent message in place (for streaming partials)."""
        # For simplicity, just print partials to console; finals go to chat.
        pass

    # ── Input helpers ─────────────────────────────────────────────────────────

    def _clear_placeholder(self, _event=None):
        if self.text_input.get() == self._placeholder:
            self.text_input.delete(0, tk.END)
            self.text_input.config(fg=TEXT)

    def _restore_placeholder(self, _event=None):
        if not self.text_input.get():
            self.text_input.insert(0, self._placeholder)
            self.text_input.config(fg=TEXT_DIM)

    def _send_text(self):
        text = self.text_var.get().strip()
        if not text or text == self._placeholder:
            return
        self.text_input.delete(0, tk.END)
        self.text_input.config(fg=TEXT)
        self._add_message("user", text)
        # In a full implementation, send text to the agent via the WebSocket.
        # For now, the voice path handles full duplex conversation.

    # ── Mic & agent lifecycle ─────────────────────────────────────────────────

    def _toggle_mic(self):
        if not self.recording:
            self._start_session()
        else:
            self._stop_session()

    def _start_session(self):
        self.recording = True
        self.mic_btn.config(text="⏹", bg=GOLD, fg="#111")
        self._set_status("listening")
        self.stop_event.clear()
        self.agent_thread = threading.Thread(target=self._run_agent_thread, daemon=True)
        self.agent_thread.start()

    def _stop_session(self):
        self.recording = False
        self.stop_event.set()
        self.mic_btn.config(text="⏺", bg="#1a1611", fg=GOLD)
        self._set_status("idle")
        if self.mic:
            self.mic.stop()
        if self.speaker:
            self.speaker.close()
            self.speaker = None

    def _run_agent_thread(self):
        """Run the async agent loop in a background thread."""
        self.loop = asyncio.new_event_loop()
        asyncio.set_event_loop(self.loop)
        try:
            self.loop.run_until_complete(self._agent_loop())
        finally:
            self.loop.close()

    async def _agent_loop(self):
        import websockets

        headers = {"Authorization": f"Bearer {self.api_key}"}
        self.speaker = Speaker()
        mic_queue: asyncio.Queue = asyncio.Queue()
        ready_event = asyncio.Event()

        self.mic = MicCapture(mic_queue, self.loop)

        try:
            async with websockets.connect(AGENT_URL, additional_headers=headers) as ws:
                self.ws = ws
                await ws.send(json.dumps({
                    "type": "session.update",
                    "session": SESSION_CONFIG,
                }))

                async def pump_mic():
                    await ready_event.wait()
                    while not self.stop_event.is_set():
                        try:
                            chunk = await asyncio.wait_for(mic_queue.get(), timeout=0.5)
                            await ws.send(json.dumps({
                                "type": "input.audio",
                                "audio": chunk,
                            }))
                        except asyncio.TimeoutError:
                            continue
                        except websockets.ConnectionClosed:
                            break

                async def recv_events():
                    async for raw in ws:
                        if self.stop_event.is_set():
                            break
                        event = json.loads(raw)
                        etype = event.get("type")

                        if etype == "session.ready":
                            self.mic.start()
                            ready_event.set()
                            self.root.after(0, lambda: self._set_status("listening"))

                        elif etype == "transcript.user":
                            text = event.get("text", "")
                            if text:
                                self.root.after(0, lambda t=text: self._add_message("user", t))

                        elif etype == "transcript.agent":
                            text = event.get("text", "")
                            if text:
                                self.root.after(0, lambda t=text: self._add_message("agent", t))
                                self.root.after(0, lambda: self._set_status("speaking"))

                        elif etype == "reply.audio":
                            pcm = base64.b64decode(event["data"])
                            if self.speaker:
                                self.speaker.write(pcm)

                        elif etype == "reply.done":
                            self.root.after(0, lambda: self._set_status("listening"))
                            if event.get("status") == "interrupted" and self.speaker:
                                self.speaker.flush()

                        elif etype == "error":
                            err = event.get("error", str(event))
                            self.root.after(0, lambda e=err: self._add_message("agent", f"[error] {e}"))

                mic_task = asyncio.create_task(pump_mic())
                recv_task = asyncio.create_task(recv_events())

                done, pending = await asyncio.wait(
                    [mic_task, recv_task],
                    return_when=asyncio.FIRST_COMPLETED,
                )
                for t in pending:
                    t.cancel()

        except Exception as e:
            self.root.after(0, lambda err=str(e): self._add_message("agent", f"[connection error] {err}"))
        finally:
            self.mic.stop()
            if self.speaker:
                self.speaker.close()
                self.speaker = None
            self.root.after(0, lambda: self._set_status("idle"))


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    load_dotenv()
    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("Error: ASSEMBLYAI_API_KEY not set. Copy .env.example to .env and add your key.")
        return

    root = tk.Tk()
    root.configure(bg=BG)

    try:
        root.tk.call("tk", "scaling", 1.5)
    except Exception:
        pass

    app = MusicAgentGUI(root, api_key)
    root.mainloop()


if __name__ == "__main__":
    main()
