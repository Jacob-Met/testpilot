#!/usr/bin/env python3
# SPDX-License-Identifier: Apache-2.0
"""Qualify a new static receiver through install, HTTP readback, rollback and reinstall."""
from __future__ import annotations

import argparse
import functools
import hashlib
import http.server
import json
import shutil
import threading
import urllib.error
import urllib.request
from pathlib import Path


def receive(source: Path, target: Path, output: Path) -> dict:
    rollback = target.with_name(target.name + ".rolled-back")
    if target.exists() or rollback.exists() or output.exists():
        raise FileExistsError("receiver, rollback and receipt paths must all be new")
    names = ["index.html", "styles.css", "app.mjs", "source-pin.json", "README.md", "LICENSE", "NOTICE"]
    names += [p.relative_to(source).as_posix() for p in sorted((source / "data").rglob("*")) if p.is_file()]
    payload = {name: (source / name).read_bytes() for name in names}
    manifest = {name: hashlib.sha256(raw).hexdigest() for name, raw in payload.items()}
    output.mkdir(parents=True)

    def install() -> None:
        target.mkdir(parents=True)
        for name, raw in payload.items():
            path = target / name
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(raw)

    class Handler(http.server.SimpleHTTPRequestHandler):
        def log_message(self, format: str, *args) -> None:
            pass

    install()
    server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), functools.partial(Handler, directory=str(target)))
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    base = f"http://127.0.0.1:{server.server_port}"
    receipt = {"source": str(source), "target": str(target), "rollback": str(rollback), "files": manifest,
               "qualification": "new owned static installation, no shared service or user profile", "http": []}
    try:
        for phase in ("installed", "reinstalled"):
            if phase == "reinstalled":
                target.rename(rollback)
                try:
                    urllib.request.urlopen(base + "/index.html", timeout=5)
                except urllib.error.HTTPError as error:
                    if error.code != 404:
                        raise
                    receipt["rollback_http_status"] = error.code
                else:
                    raise AssertionError("rolled-back receiver still serves index.html")
                if target.exists():
                    raise AssertionError("owned receiver remains after rollback")
                install()
            for name, expected in manifest.items():
                with urllib.request.urlopen(base + "/" + name, timeout=5) as response:
                    raw = response.read()
                    if response.status != 200 or hashlib.sha256(raw).hexdigest() != expected:
                        raise AssertionError(f"HTTP readback mismatch: {name}")
                receipt["http"].append({"phase": phase, "path": name, "sha256": expected, "status": 200})
        receipt["completed"] = True
    except BaseException as error:
        receipt["completed"] = False
        receipt["error"] = repr(error)
        raise
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
        (output / "receipt.json").write_text(json.dumps(receipt, indent=2) + "\n")
    return receipt


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("target", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    result = receive(args.source.resolve(), args.target.resolve(), args.output.resolve())
    print(json.dumps({"target": result["target"], "files": len(result["files"]),
                      "http_readbacks": len(result["http"]), "rollback_status": result["rollback_http_status"],
                      "completed": result["completed"]}))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
