"""Genera PDF del informe comercial Excalibu Sentinel."""
from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
HTML = ROOT / "web" / "marketing" / "informe.html"
OUT_DIR = ROOT / "docs" / "marketing"
OUT_PDF = OUT_DIR / "INFORME-EXCALIBU-SENTINEL.pdf"


def _edge_paths() -> list[Path]:
    candidates = [
        Path(r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Microsoft\Edge\Application\msedge.exe"),
        Path(r"C:\Program Files\Google\Chrome\Application\chrome.exe"),
        Path(r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe"),
    ]
    return [p for p in candidates if p.exists()]


def main() -> int:
    if not HTML.exists():
        print("No existe:", HTML)
        return 1

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    uri = HTML.resolve().as_uri()

    for browser in _edge_paths():
        cmd = [
            str(browser),
            "--headless=new",
            "--disable-gpu",
            f"--print-to-pdf={OUT_PDF}",
            "--no-pdf-header-footer",
            uri,
        ]
        try:
            subprocess.run(cmd, check=True, capture_output=True, timeout=60)
            if OUT_PDF.exists() and OUT_PDF.stat().st_size > 5000:
                print("PDF generado:", OUT_PDF)
                return 0
        except (subprocess.CalledProcessError, subprocess.TimeoutExpired, OSError):
            continue

    # Fallback: copiar HTML al docs
    html_out = OUT_DIR / "INFORME-EXCALIBU-SENTINEL.html"
    shutil.copy2(HTML, html_out)
    print("No se pudo generar PDF automático (Edge/Chrome headless).")
    print("Abra en navegador y use Ctrl+P → Guardar como PDF:")
    print(" ", HTML)
    print("Copia en docs:", html_out)
    return 0


if __name__ == "__main__":
    sys.exit(main())
