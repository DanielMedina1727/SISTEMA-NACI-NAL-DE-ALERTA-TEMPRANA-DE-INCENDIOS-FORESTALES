"""
Pruebas de la API FastAPI (app/main.py): endpoints públicos, validación de
reportes ciudadanos y protección de los endpoints de alerta.

Usa el TestClient de Starlette/FastAPI (sin red, sin servidor externo).
"""
from conftest import requires_dataset, requires_model

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_endpoint():
    r = client.get("/health")
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "ok"
    assert set(body["thresholds"]) == {"rojo", "amarillo"}


@requires_model
@requires_dataset
def test_risk_today_returns_geojson():
    r = client.get("/risk/today", params={"limit": 50})
    assert r.status_code == 200
    body = r.json()
    assert body["type"] == "FeatureCollection"
    assert body["count"] <= 50
    assert "stats" in body
    assert body["stats"]["total_analizado"] >= body["stats"]["rojo"]

    f0 = body["features"][0]
    assert f0["geometry"]["type"] == "Polygon"
    assert f0["properties"]["nivel"] in {"Verde", "Amarillo", "Rojo"}


@requires_model
def test_predict_returns_valid_level():
    r = client.post(
        "/predict",
        json={"grid_id": "test", "temp_2m": 35.0, "humedad_relativa": 8.0},
    )
    assert r.status_code == 200
    body = r.json()
    assert 0.0 <= body["probabilidad"] <= 1.0
    assert body["nivel"] in {"Verde", "Amarillo", "Rojo"}


def test_report_citizen_rejects_coords_outside_peru():
    r = client.post("/report/citizen", json={"lat": 40.0, "lon": -3.0})
    assert r.status_code == 422


def test_report_citizen_rejects_unknown_incident_type():
    r = client.post(
        "/report/citizen",
        json={"lat": -7.16, "lon": -78.5, "incident_type": "ovni"},
    )
    assert r.status_code == 422


def test_report_citizen_accepts_and_persists(tmp_path, monkeypatch):
    import app.main as m

    calls = []

    def fake_send(chat_id, message, accounts=None, max_retries=3):
        calls.append((chat_id, message, max_retries))
        return {"account": "principal", "response": {"idMessage": "test"}}

    monkeypatch.setattr(m, "REPORTS_PATH", tmp_path / "reports.jsonl")
    monkeypatch.setattr(m, "send_message_to_chat", fake_send)
    monkeypatch.setenv("WA_GROUP_CAJAMARCA", "cajamarca-test@g.us")
    r = client.post(
        "/report/citizen",
        json={
            "lat": -7.16,
            "lon": -78.5,
            "incident_type": "fuego_activo",
            "reporter_zone": "Cajamarca",
        },
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "received" and body["id"]
    assert body["zone"] == "Cajamarca"
    assert body["whatsapp"]["status"] == "sent"
    assert calls and calls[0][0] == "cajamarca-test@g.us"
    assert calls[0][2] == 1
    assert "Cajamarca" in calls[0][1]
    assert "-7.16000" in calls[0][1] and "-78.50000" in calls[0][1]
    assert (tmp_path / "reports.jsonl").exists()


def test_report_citizen_outside_zone_skips_whatsapp(tmp_path, monkeypatch):
    import app.main as m

    monkeypatch.setattr(m, "REPORTS_PATH", tmp_path / "reports.jsonl")

    def fail_send(*args, **kwargs):
        raise AssertionError("No se debe enviar WhatsApp fuera de una zona")

    monkeypatch.setattr(m, "send_message_to_chat", fail_send)
    r = client.post(
        "/report/citizen",
        json={"lat": -12.05, "lon": -77.04, "incident_type": "columna_humo"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["zone"] is None
    assert body["whatsapp"] == {"status": "skipped", "reason": "outside_zone"}


def test_find_zone_for_point():
    from app.zones import find_zone_for_point

    assert find_zone_for_point(-7.16, -78.5)["nombre"] == "Cajamarca"
    assert find_zone_for_point(-7.5, -78.1)["nombre"] == "San Marcos"
    assert find_zone_for_point(-12.05, -77.04) is None


def test_alerts_require_key_when_configured(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secreto-de-prueba")
    r = client.post("/alert/whatsapp", json={"grid_id": "x", "lat": -7.16, "lon": -78.5})
    assert r.status_code == 401


def test_alerts_reject_wrong_key(monkeypatch):
    monkeypatch.setenv("ADMIN_API_KEY", "secreto-de-prueba")
    r = client.post(
        "/alert/whatsapp",
        headers={"X-API-Key": "incorrecta"},
        json={"grid_id": "x", "lat": -7.16, "lon": -78.5},
    )
    assert r.status_code == 401


def test_report_recent_returns_list():
    r = client.get("/report/recent", params={"limit": 5})
    assert r.status_code == 200
    assert isinstance(r.json()["reports"], list)


def test_model_importance_shape():
    r = client.get("/model/importance")
    assert r.status_code == 200
    body = r.json()
    assert body["n_features"] == 18
    assert len(body["feature_importance"]) >= 1


def test_openapi_documents_key_endpoints():
    r = client.get("/openapi.json")
    assert r.status_code == 200
    paths = r.json()["paths"]
    for ep in ["/health", "/risk/today", "/predict", "/report/citizen"]:
        assert ep in paths
