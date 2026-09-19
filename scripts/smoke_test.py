from fastapi.testclient import TestClient



from app.main import app



with TestClient(app) as c:

    assert c.get("/api/health").json()["ok"]

    assert c.get("/demo", follow_redirects=False).status_code == 307

    r = c.post("/api/auth/login", json={"username": "admin", "password": "Admin2026!"})

    assert r.status_code == 200, r.text

    ah = {"Authorization": "Bearer " + r.json()["access_token"]}

    d = c.get("/api/dashboard", headers=ah).json()

    assert d["guards"] == 0

    assert d["sites"] == 0

    vl = c.post("/api/vendor/login", json={"username": "vendor", "password": "GuardiaVendor2026"})

    assert vl.status_code == 200, vl.text

    print("OK — producción limpia, admin operativo")


