"""Dispara Manual Deploy en Render vía Deploy Hook (Settings → Deploy Hook en el servicio)."""
from __future__ import annotations

import os
import sys
from pathlib import Path
from urllib.request import Request, urlopen

ROOT = Path(__file__).resolve().parents[1]
ENV = ROOT / "push-cloud.env"


def _load_env() -> None:
    if not ENV.is_file():
        return
    for line in ENV.read_text(encoding="utf-8").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            os.environ.setdefault(k.strip(), v.strip().strip('"'))


def main() -> None:
    _load_env()
    hook = (os.getenv("RENDER_DEPLOY_HOOK") or "").strip()
    if not hook:
        print(
            "Falta RENDER_DEPLOY_HOOK en push-cloud.env\n"
            "Render → excalibu-sentinel → Settings → Deploy Hook → copie URL",
            file=sys.stderr,
        )
        sys.exit(1)
    req = Request(hook, data=b"", method="POST")
    with urlopen(req, timeout=120) as r:
        print(r.read().decode() or "Deploy solicitado (Render).")
    print("Espere 3–5 min y pruebe /health/live y login?empresa=grupo-gomez")


if __name__ == "__main__":
    main()
