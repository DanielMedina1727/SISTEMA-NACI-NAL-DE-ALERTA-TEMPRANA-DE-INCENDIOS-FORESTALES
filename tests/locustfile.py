"""
Prueba de carga concurrente para la API (Semana 15-16).
Simula 100 peticiones simultáneas sobre endpoints críticos.

Uso:
    locust -f tests/locustfile.py --host=http://localhost:8000
    O en modo headless:
    locust -f tests/locustfile.py --host=http://localhost:8000 --headless -u 100 -r 10 --run-time 30s
"""
from locust import HttpUser, between, task


class WildfireAPIUser(HttpUser):
    wait_time = between(0.2, 1.0)

    @task(5)
    def get_health(self):
        self.client.get("/health")

    @task(3)
    def get_risk_today(self):
        self.client.get("/risk/today?limit=100")

    @task(2)
    def predict_risk(self):
        self.client.post("/predict", json={
            "grid_id": "-78.5000_-7.1600",
            "pendiente_pct": 22.5,
            "orientacion": "NE",
            "ndvi": 0.55,
            "dist_carretera_m": 450,
            "dist_poblado_m": 1100,
            "temp_2m": 30.5,
            "humedad_relativa": 25.0,
            "viento_velocidad": 28.0,
            "viento_direccion": 45.0,
        })

    @task(1)
    def propagate_wind(self):
        self.client.post("/propagate?grid_id=-78.5000_-7.1600&viento_direccion=45&viento_velocidad=25")

