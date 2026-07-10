def test_health_returns_200_and_expected_payload(app_client):
    """Validar endpoint de health check da aplicacao."""

    response = app_client.get("/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
