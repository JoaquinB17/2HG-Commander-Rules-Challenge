"""Allow `python -m two_headed_giant`."""

from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
