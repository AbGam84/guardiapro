import math


def haversine_m(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    """Distancia en metros entre dos coordenadas GPS."""
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp = math.radians(lat2 - lat1)
    dl = math.radians(lng2 - lng1)
    a = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return r * 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))


def route_distance_m(points: list[tuple[float, float]]) -> float:
    """Suma distancia entre puntos consecutivos con GPS válido."""
    total = 0.0
    prev = None
    for lat, lng in points:
        if lat is None or lng is None:
            continue
        if prev is not None:
            total += haversine_m(prev[0], prev[1], lat, lng)
        prev = (lat, lng)
    return total


def format_distance(meters: float) -> str:
    if meters < 1000:
        return f"{meters:.0f} m"
    return f"{meters / 1000:.2f} km"
