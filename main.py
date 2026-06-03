"""
main.py — Entry point for the Music Theory Voice Agent.

Usage:
    python main.py

Requirements:
    pip install -r requirements.txt

Setup:
    Copy .env.example to .env and add your AssemblyAI API key.
    Never commit your .env file to GitHub.
"""

import asyncio
import os
import sys

from dotenv import load_dotenv

from agent import run_agent


def main():
    load_dotenv()

    api_key = os.getenv("ASSEMBLYAI_API_KEY")
    if not api_key:
        print("Error: ASSEMBLYAI_API_KEY is not set.")
        print("Copy .env.example to .env and add your key.")
        sys.exit(1)

    print("=" * 50)
    print("  🎵 Music Theory Voice Agent")
    print("=" * 50)
    print("Press Ctrl+C at any time to quit.\n")

    try:
        asyncio.run(run_agent(api_key))
    except KeyboardInterrupt:
        print("\nGoodbye!")


if __name__ == "__main__":
    main()
