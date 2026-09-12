#!/usr/bin/env python3
"""Start Sprout with: python3 run.py [--port 8000]."""

import argparse

from farm.server import create_server


def main():
    parser = argparse.ArgumentParser(description="Sprout — program your farm")
    parser.add_argument("--port", type=int, default=8000, help="local port (default: 8000)")
    args = parser.parse_args()
    if not 1 <= args.port <= 65535:
        parser.error("port must be between 1 and 65535")
    try:
        server = create_server(args.port)
    except OSError as exc:
        parser.exit(1, f"Could not start Sprout: {exc}\nTry another port: python3 run.py --port 8080\n")
    print(f"\n  SPROUT · program your farm\n  Open http://127.0.0.1:{args.port}\n  Press Ctrl+C to stop.\n", flush=True)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nFarm closed. Your progress is saved in your browser.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
