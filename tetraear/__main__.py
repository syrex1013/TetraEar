"""
Package entrypoint.

Running `python -m tetraear` launches the Modern GUI by default.
"""

from __future__ import annotations


def main() -> None:
    """Launch the Modern GUI."""
    from tetraear.ui.modern import main as modern_main

    modern_main()


if __name__ == "__main__":
    main()

