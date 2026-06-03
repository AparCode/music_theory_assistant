# 🎵 Music Theory Voice Assistant
# @author: Aparnaa Senthilnathan

A conversational AI voice agent that answers music theory questions and helps you craft chord progressions and melodies — powered by [AssemblyAI's Voice Agent API](https://www.assemblyai.com/docs/voice-agents/voice-agent-api/overview).

## Features

- **Full spoken conversation** — talk naturally, get spoken responses
- **Music theory expertise** — scales, intervals, harmony, counterpoint, modes, and more
- **Chord progression suggestions** — any genre (jazz, pop, blues, classical, metal, etc.)
- **Melody ideas** — construction, development, and phrasing
- **Barge-in support** — interrupt the agent mid-sentence, just like a real conversation

## Setup

### 1. Clone the repo

```bash
git clone https://github.com/your-username/music-theory-agent.git
cd music-theory-agent
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> On Linux you may need `sudo apt install portaudio19-dev` before installing `sounddevice`.
> On macOS: `brew install portaudio`.

### 3. Add your API key

```bash
cp .env.example .env
```

Open `.env` and replace `your_api_key_here` with your AssemblyAI API key.  
Get one free at [assemblyai.com/dashboard/api-keys](https://www.assemblyai.com/dashboard/api-keys).

**Never commit your `.env` file.** It's already in `.gitignore`.

### 4. Run

```bash
python main.py
```

The agent will greet you and you can start speaking.

## Project Structure

```
music-theory-agent/
├── main.py          # Entry point
├── agent.py         # WebSocket connection and event handling
├── audio.py         # Microphone capture and speaker playback
├── requirements.txt
├── .env.example     # API key template (safe to commit)
├── .env             # Your actual key (never commit this)
└── .gitignore
```

## Example Conversations

- *"What's the difference between a major and minor scale?"*
- *"Give me a jazz chord progression in Eb."*
- *"How do I write a melody over a ii-V-I?"*
- *"What modes work well over a dominant chord?"*
- *"Suggest a chord progression for a melancholic indie song."*

## Troubleshooting

| Problem | Fix |
|---|---|
| No audio input | Check your default mic in system settings |
| No audio output | Check your default speaker/headphones |
| `portaudio` error | Install PortAudio (see Setup step 2) |
| `401` / auth error | Double-check your API key in `.env` |

## License

MIT
