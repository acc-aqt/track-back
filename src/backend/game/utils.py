"""Module for utility functions used in the game."""

import sys


def get_user_input(prompt: str) -> str:
    """Get input from the user with a prompt and handle Keyboard Interrupts."""
    try:
        return input(prompt)
    except KeyboardInterrupt:
        print("\n👋 Game cancelled by user.")
        sys.exit(0)
