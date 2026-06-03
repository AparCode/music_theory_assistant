"""
audio.py — Mic capture and speaker playback for the music theory voice agent.
Audio format: PCM16 mono 24 kHz, matching the Voice Agent API requirement.
"""

import asyncio
import base64
import numpy as np
import sounddevice as sd

SAMPLE_RATE = 24_000
CHANNELS = 1
DTYPE = "int16"
CHUNK_DURATION_MS = 50  # ~50ms chunks
CHUNK_FRAMES = int(SAMPLE_RATE * CHUNK_DURATION_MS / 1000)  # 1200 frames per chunk


class MicCapture:
    """Captures microphone audio and puts base64-encoded PCM16 chunks into a queue."""

    def __init__(self, queue: asyncio.Queue, loop: asyncio.AbstractEventLoop):
        self._queue = queue
        self._loop = loop
        self._stream = None

    def _callback(self, indata, frames, time_info, status):
        if status:
            print(f"[mic] status: {status}")
        # indata shape: (frames, channels) as int16
        raw = bytes(indata)
        encoded = base64.b64encode(raw).decode()
        self._loop.call_soon_threadsafe(self._queue.put_nowait, encoded)

    def start(self):
        self._stream = sd.InputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
            blocksize=CHUNK_FRAMES,
            callback=self._callback,
        )
        self._stream.start()
        print("[mic] Microphone capture started.")

    def stop(self):
        if self._stream:
            self._stream.stop()
            self._stream.close()
            self._stream = None
            print("[mic] Microphone capture stopped.")


class Speaker:
    """Plays back PCM16 audio from the agent."""

    def __init__(self):
        self._stream = sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=CHANNELS,
            dtype=DTYPE,
        )
        self._stream.start()

    def write(self, pcm16_bytes: bytes):
        """Write raw PCM16 bytes to the speaker."""
        audio = np.frombuffer(pcm16_bytes, dtype=np.int16)
        self._stream.write(audio)

    def flush(self):
        """Flush the output buffer — call when the agent is interrupted."""
        self._stream.abort()
        self._stream.start()

    def close(self):
        self._stream.stop()
        self._stream.close()
        print("[speaker] Speaker closed.")
