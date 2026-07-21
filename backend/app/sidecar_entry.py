from __future__ import annotations

import argparse
import multiprocessing

import uvicorn


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run the Suoyi local FastAPI sidecar.")
    parser.add_argument("--host", default="127.0.0.1", choices=["127.0.0.1", "localhost"])
    parser.add_argument("--port", type=int, default=8765)
    parser.add_argument("--log-level", default="warning", choices=["critical", "error", "warning", "info"])
    return parser.parse_args()


def main() -> int:
    multiprocessing.freeze_support()
    args = parse_args()
    uvicorn.run(
        "backend.app.main:app",
        host=args.host,
        port=args.port,
        log_level=args.log_level,
        access_log=False,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
