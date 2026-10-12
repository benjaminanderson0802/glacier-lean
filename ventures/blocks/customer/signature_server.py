"""Serve pending signature pages on localhost only."""
import argparse

from . import create_signature_server


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--data-dir", default=None)
    args = parser.parse_args()
    server = create_signature_server(args.data_dir, host="127.0.0.1", port=args.port)
    print(f"Signature pages available at http://127.0.0.1:{server.server_address[1]}/signature/<request-id>")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
