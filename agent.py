"""
agent.py — WebSocket connection and event loop for the music theory voice agent.
Handles the full AssemblyAI Voice Agent API lifecycle:
  session.update → session.ready → audio streaming → reply playback → graceful close
"""

import asyncio
import base64
import json
import os

import websockets

from audio import MicCapture, Speaker

AGENT_URL = "wss://agents.assemblyai.com/v1/ws"

SYSTEM_PROMPT = """You are an expert music theory tutor and creative collaborator.
You have deep knowledge of:
- Music theory fundamentals (scales, intervals, chords, rhythm, harmony, counterpoint)
- Chord progressions in any genre (jazz, classical, pop, blues, R&B, folk, metal, etc.)
- Melody construction and development techniques
- Song structure, composition, and arrangement
- Music history and how theory evolved across styles

When a user asks a theory question, explain it clearly and engagingly, using musical examples where helpful.
When they want chord progressions or melody ideas, be creative and specific — give real chord names, suggest voicings, 
describe the mood or feel, and explain why the choices work musically.
Keep your answers conversational and encouraging. The user is talking to you, so be warm and natural.
Avoid overly long responses — aim to be thorough but concise."""

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
            "polyphony", "monophony", "homophony", "ostinato", "syncopation",
            "enharmonic", "chromatic", "modal", "Dorian", "Phrygian", "Lydian",
            "Mixolydian", "Locrian", "ii-V-I", "circle of fifths",
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


async def run_agent(api_key: str):
    headers = {"Authorization": f"Bearer {api_key}"}
    speaker = Speaker()
    loop = asyncio.get_running_loop()
    mic_queue: asyncio.Queue = asyncio.Queue()
    ready_event = asyncio.Event()
    stop_event = asyncio.Event()

    print("[agent] Connecting to AssemblyAI Voice Agent API...")

    try:
        async with websockets.connect(AGENT_URL, additional_headers=headers) as ws:
            print("[agent] Connected. Sending session configuration...")

            # Send session config immediately (don't wait for session.ready)
            await ws.send(json.dumps({
                "type": "session.update",
                "session": SESSION_CONFIG,
            }))

            # Start mic capture
            mic = MicCapture(mic_queue, loop)

            async def pump_mic():
                """Send mic audio to the agent once session is ready."""
                await ready_event.wait()
                print("[agent] Session ready — microphone is live. Speak now!\n")
                while not stop_event.is_set():
                    try:
                        encoded_chunk = await asyncio.wait_for(mic_queue.get(), timeout=0.5)
                        await ws.send(json.dumps({
                            "type": "input.audio",
                            "audio": encoded_chunk,
                        }))
                    except asyncio.TimeoutError:
                        continue
                    except websockets.ConnectionClosed:
                        break

            async def receive_events():
                """Handle all incoming server events."""
                async for raw in ws:
                    event = json.loads(raw)
                    etype = event.get("type")

                    if etype == "session.ready":
                        session_id = event.get("session_id", "unknown")
                        print(f"[agent] Session ready (id: {session_id})")
                        mic.start()
                        ready_event.set()

                    elif etype == "transcript.user.delta":
                        # Partial user transcript — show in real time
                        print(f"\r[you] {event.get('text', '')}", end="", flush=True)

                    elif etype == "transcript.user":
                        # Final user transcript
                        print(f"\r[you] {event.get('text', '')}")

                    elif etype == "transcript.agent":
                        # What the agent said
                        print(f"[agent] {event.get('text', '')}")

                    elif etype == "reply.audio":
                        # Play back agent audio — data field (not audio field!)
                        pcm_bytes = base64.b64decode(event["data"])
                        speaker.write(pcm_bytes)

                    elif etype == "reply.done":
                        status = event.get("status")
                        if status == "interrupted":
                            # User barged in — flush stale agent audio
                            speaker.flush()

                    elif etype == "error":
                        print(f"\n[error] {event.get('error', event)}")

            mic_task = asyncio.create_task(pump_mic())
            recv_task = asyncio.create_task(receive_events())

            try:
                await asyncio.gather(mic_task, recv_task)
            except (KeyboardInterrupt, asyncio.CancelledError):
                pass
            finally:
                stop_event.set()
                mic.stop()
                mic_task.cancel()
                recv_task.cancel()

    except websockets.InvalidStatusCode as e:
        print(f"[error] WebSocket handshake failed (HTTP {e.status_code}). Check your API key.")
    except Exception as e:
        print(f"[error] Unexpected error: {e}")
    finally:
        speaker.close()
        print("[agent] Session ended.")
