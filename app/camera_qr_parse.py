"""Reconocer QR de Excalibu, DVR, NVR y cámaras WiFi."""

from __future__ import annotations

import json
import re
from urllib.parse import parse_qs, unquote, urlparse

EXCALIBU_PREFIX = "excalibu-cam:"


def extract_pair_token(text: str) -> str | None:
    raw = (text or "").strip()
    if raw.lower().startswith(EXCALIBU_PREFIX):
        return raw[len(EXCALIBU_PREFIX) :].split("?")[0].strip()[:64]
    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                t = (data.get("pair_token") or data.get("token") or "").strip()
                if t:
                    return t[:64]
                if (data.get("type") or "").lower() == "excalibu-cam":
                    return (data.get("id") or data.get("pair") or "").strip()[:64] or None
        except json.JSONDecodeError:
            pass
    try:
        u = urlparse(raw if "://" in raw else f"https://x/?{raw}")
        for key in ("pair", "cam-pair", "token", "pair_token"):
            val = parse_qs(u.query).get(key, [None])[0]
            if val:
                return val.strip()[:64]
        path = u.path or ""
        if "/pair/" in path:
            return path.rsplit("/pair/", 1)[-1].split("/")[0].strip()[:64] or None
    except Exception:
        pass
    return None


def _norm_brand(val: str) -> str:
    v = (val or "").strip().lower()
    for key in ("hikvision", "dahua", "imou", "tplink", "tapo", "ezviz", "reolink", "uniview", "xmeye", "v360"):
        if key in v:
            if key == "imou":
                return "dahua"
            if key == "tapo":
                return "tplink"
            return key
    return "other"


def _guess_camera_type(data: dict, text: str) -> str:
    t = " ".join(
        str(data.get(k) or "")
        for k in ("type", "deviceType", "device_type", "camera_type", "kind", "model")
    ).lower()
    blob = (text or "").lower()
    if any(x in t or x in blob for x in ("nvr", "network video")):
        return "nvr"
    if any(x in t or x in blob for x in ("dvr", "xmeye", "xvr")):
        return "dvr"
    if any(x in t or x in blob for x in ("wifi", "ipc", "ip cam", "tapo", "imou")):
        return "wifi"
    return "wifi"


def _parse_json_device(data: dict, raw: str) -> dict:
    ip = (
        data.get("ip")
        or data.get("IP")
        or data.get("host")
        or data.get("ipAddress")
        or data.get("ip_address")
        or ""
    )
    if isinstance(ip, str):
        ip = ip.strip()
    name = (
        data.get("name")
        or data.get("deviceName")
        or data.get("DeviceName")
        or data.get("title")
        or "Cámara detectada por QR"
    )
    brand = _norm_brand(str(data.get("brand") or data.get("manufacturer") or data.get("oem") or raw))
    cam_type = _guess_camera_type(data, raw)
    rtsp_port = int(data.get("rtsp_port") or data.get("rtspPort") or data.get("port") or 554)
    http_port = int(data.get("http_port") or data.get("httpPort") or data.get("webPort") or 80)
    channel = int(data.get("channel") or data.get("Channel") or 1)
    return {
        "recognized": True,
        "source": "device_json",
        "pair_kind": cam_type if cam_type in ("nvr", "dvr") else "wifi",
        "name": str(name).strip()[:120],
        "camera_type": cam_type,
        "brand": brand,
        "ip_address": str(ip).strip()[:45],
        "username": str(data.get("username") or data.get("user") or data.get("UserName") or "admin").strip()[:80],
        "password": str(data.get("password") or data.get("pwd") or data.get("pass") or "").strip()[:120],
        "rtsp_port": rtsp_port,
        "http_port": http_port,
        "channel": channel,
        "model_name": str(data.get("model") or data.get("model_name") or data.get("serial") or "").strip()[:80],
        "notes": f"Registrada por QR · {raw[:180]}",
    }


def parse_device_qr(text: str) -> dict:
    raw = (text or "").strip()
    if not raw:
        return {"recognized": False, "message": "QR vacío"}

    token = extract_pair_token(raw)
    if token:
        return {
            "recognized": True,
            "source": "excalibu",
            "pair_kind": "mobile",
            "pair_token": token,
            "message": "QR Excalibu — cámara compartida desde celular",
        }

    if raw.startswith("{"):
        try:
            data = json.loads(raw)
            if isinstance(data, dict):
                out = _parse_json_device(data, raw)
                out["message"] = f"QR reconocido — {out.get('camera_type', 'equipo').upper()}"
                return out
        except json.JSONDecodeError:
            pass

    if raw.startswith("WIFI:"):
        ssid = ""
        for part in raw.split(";"):
            if part.upper().startswith("S:"):
                ssid = part[2:]
        return {
            "recognized": True,
            "source": "wifi_setup",
            "pair_kind": "wifi",
            "camera_type": "wifi",
            "brand": "tplink",
            "name": ssid or "Cámara WiFi",
            "notes": f"QR WiFi detectado · {raw[:200]}",
            "message": "QR WiFi — complete IP tras conectar la cámara a la red",
        }

    try:
        u = urlparse(raw)
        qs = parse_qs(u.query)
        ip = (qs.get("ip") or qs.get("host") or [None])[0] or u.hostname or ""
        if ip and re.match(r"^[\d.]+$|^[a-zA-Z0-9.-]+$", ip):
            brand = _norm_brand(raw)
            cam_type = _guess_camera_type(qs, raw)
            return {
                "recognized": True,
                "source": "url",
                "pair_kind": cam_type if cam_type in ("nvr", "dvr") else "wifi",
                "name": unquote((qs.get("name") or ["Cámara QR"])[0])[:120],
                "camera_type": cam_type,
                "brand": brand,
                "ip_address": ip[:45],
                "username": (qs.get("username") or qs.get("user") or ["admin"])[0][:80],
                "password": (qs.get("password") or [""])[0][:120],
                "rtsp_port": int((qs.get("rtsp_port") or qs.get("port") or ["554"])[0]),
                "http_port": int((qs.get("http_port") or ["80"])[0]),
                "channel": int((qs.get("channel") or ["1"])[0]),
                "notes": f"QR URL · {raw[:200]}",
                "message": f"QR URL — {cam_type.upper()} detectado",
            }
    except Exception:
        pass

    ip_match = re.search(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", raw)
    if ip_match:
        ip = ip_match.group()
        brand = _norm_brand(raw)
        cam_type = _guess_camera_type({}, raw)
        return {
            "recognized": True,
            "source": "ip_text",
            "pair_kind": cam_type if cam_type in ("nvr", "dvr") else "wifi",
            "name": f"{'NVR' if cam_type == 'nvr' else 'DVR' if cam_type == 'dvr' else 'Cámara'} {ip}",
            "camera_type": cam_type,
            "brand": brand,
            "ip_address": ip,
            "username": "admin",
            "rtsp_port": 554,
            "http_port": 80,
            "channel": 1,
            "notes": f"QR con IP · {raw[:200]}",
            "message": f"IP {ip} detectada — verifique marca y claves",
        }

    return {
        "recognized": False,
        "raw_preview": raw[:300],
        "message": "QR no reconocido — use el formulario manual",
    }


def pair_qr_text(token: str) -> str:
    return f"{EXCALIBU_PREFIX}{token}"
