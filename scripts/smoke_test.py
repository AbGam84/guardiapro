from fastapi.testclient import TestClient

from app.main import app

with TestClient(app) as c:
    assert c.get("/api/health").json()["ok"]
    r = c.post("/api/auth/login", json={"username": "juan", "password": "Guardia2026!"})
    assert r.status_code == 200, r.text
    h = {"Authorization": "Bearer " + r.json()["access_token"]}
    s = c.post("/api/shifts/start", json={"site_id": 1, "note": "Turno"}, headers=h).json()["shift"]
    c.post(f"/api/shifts/{s['id']}/log", json={"entry_type": "incidente", "note": "Test", "severity": "critica"}, headers=h)
    ad = c.post("/api/auth/login", json={"username": "admin", "password": "Admin2026!"})
    ah = {"Authorization": "Bearer " + ad.json()["access_token"]}
    d = c.get("/api/dashboard", headers=ah).json()
    vl = c.post("/api/vendor/login", json={"username": "vendor", "password": "GuardiaVendor2026"})
    vh = {"Authorization": "Bearer " + vl.json()["access_token"]}
    co = c.post(
        "/api/vendor/companies",
        json={"name": "Seguridad Test", "admin_username": "testadmin", "admin_password": "Test2026!"},
        headers=vh,
    )
    print("OK", d["open_shifts"], co.json()["company"]["code"])
