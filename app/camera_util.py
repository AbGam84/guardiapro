from urllib.parse import quote

CAMERA_TYPES = {
    "wifi": "Cámara WiFi / IP",
    "nvr": "Grabador NVR",
    "dvr": "Grabador DVR",
    "nvr_channel": "Canal en NVR",
    "dvr_channel": "Canal en DVR",
}

BRANDS = {
    "hikvision": "Hikvision",
    "dahua": "Dahua / Imou",
    "tplink": "TP-Link / Tapo",
    "ezviz": "Ezviz / Hik-connect",
    "reolink": "Reolink",
    "uniview": "Uniview",
    "v360": "V360 / Genérico P2P",
    "xmeye": "XMEye / DVR genérico",
    "other": "Otra marca",
}


def _cred(user: str, pwd: str) -> str:
    u = quote(user or "", safe="")
    p = quote(pwd or "", safe="")
    if u and p:
        return f"{u}:{p}@"
    if u:
        return f"{u}@"
    return ""


def build_rtsp_url(
    *,
    brand: str,
    camera_type: str,
    ip: str,
    port: int,
    channel: int,
    username: str,
    password: str,
    rtsp_override: str = "",
) -> str:
    if rtsp_override.strip():
        return rtsp_override.strip()
    if not ip:
        return ""
    cred = _cred(username, password)
    host = f"{ip}:{port or 554}"
    ch = max(1, channel or 1)
    b = (brand or "other").lower()

    if camera_type == "wifi":
        if b == "hikvision":
            return f"rtsp://{cred}{host}/Streaming/Channels/101"
        if b == "dahua":
            return f"rtsp://{cred}{host}/cam/realmonitor?channel=1&subtype=0"
        if b == "reolink":
            return f"rtsp://{cred}{host}/h264Preview_01_main"
        if b == "tplink":
            return f"rtsp://{cred}{host}/stream1"
        return f"rtsp://{cred}{host}/"

    # NVR / DVR / canales
    if b == "hikvision":
        # Canal N: 101 main, 102 sub...
        stream = ch * 100 + 1
        return f"rtsp://{cred}{host}/Streaming/Channels/{stream}"
    if b == "dahua":
        return f"rtsp://{cred}{host}/cam/realmonitor?channel={ch}&subtype=0"
    if b == "xmeye" or b == "v360":
        return f"rtsp://{cred}{host}/user={quote(username or '')}&password={quote(password or '')}&channel={ch}&stream=0.sdp?"
    if b == "uniview":
        return f"rtsp://{cred}{host}/video1"
    return f"rtsp://{cred}{host}/ch{ch}/main"


def build_web_url(
    *,
    brand: str,
    ip: str,
    http_port: int,
    username: str,
    web_override: str = "",
) -> str:
    if web_override.strip():
        return web_override.strip()
    if not ip:
        return ""
    port = http_port or 80
    base = f"http://{ip}:{port}" if port != 80 else f"http://{ip}"
    b = (brand or "other").lower()
    if b == "hikvision":
        return f"{base}/doc/page/login.asp"
    if b == "dahua":
        return base
    if b == "tplink":
        return base
    return base
