# -*- coding: utf-8 -*-
"""Pruebas del soporte multi-instancia de Green API (sin llamadas de red)."""

from __future__ import annotations

import asyncio
import json
import os

import pytest

from app import whatsapp_alerts as wa


@pytest.fixture
def clean_whatsapp_env(monkeypatch):
    """Aísla las pruebas de las credenciales reales cargadas desde .env."""
    monkeypatch.delenv("GREEN_API_ACCOUNTS", raising=False)
    monkeypatch.delenv("GREEN_API_MAX_GROUPS_PER_INSTANCE", raising=False)
    for key in list(os.environ):
        if key.startswith(("GREEN_API_INSTANCE_ID", "GREEN_API_TOKEN", "WHATSAPP_GROUP_IDS")):
            monkeypatch.delenv(key, raising=False)
    for key in [key for key in os.environ if key.startswith("WA_GROUP_")]:
        monkeypatch.delenv(key, raising=False)
    yield


def _accounts_json() -> str:
    return json.dumps(
        [
            {
                "label": "principal",
                "instance_id": "100",
                "token": "token-principal",
                "group_ids": ["g1@g.us", "g2@g.us"],
            },
            {
                "label": "secundaria",
                "instance_id": "200",
                "token": "token-secundaria",
                "group_ids": ["g3@g.us", "g4@g.us"],
            },
        ]
    )


def test_get_accounts_legacy(clean_whatsapp_env, monkeypatch):
    monkeypatch.setenv("GREEN_API_INSTANCE_ID", "100")
    monkeypatch.setenv("GREEN_API_TOKEN", "token")
    monkeypatch.setenv("WHATSAPP_GROUP_IDS", "g1@g.us, g2@g.us")

    accounts = wa.get_accounts()

    assert len(accounts) == 1
    assert accounts[0].label == "principal"
    assert accounts[0].group_ids == ("g1@g.us", "g2@g.us")


def test_get_accounts_legacy_uses_zone_groups_if_needed(clean_whatsapp_env, monkeypatch):
    monkeypatch.setenv("GREEN_API_INSTANCE_ID", "100")
    monkeypatch.setenv("GREEN_API_TOKEN", "token")
    monkeypatch.setenv("WA_GROUP_SAN_MARCOS", "g1@g.us")

    accounts = wa.get_accounts()

    assert accounts[0].group_ids == ("g1@g.us",)


def test_simple_two_accounts_auto_split(clean_whatsapp_env, monkeypatch):
    from app import scheduler

    # El import de scheduler puede recargar .env; limpiar otra vez para aislar.
    for key in list(os.environ):
        if key == "GREEN_API_ACCOUNTS" or key.startswith(
            ("GREEN_API_INSTANCE_ID", "GREEN_API_TOKEN", "WHATSAPP_GROUP_IDS", "WA_GROUP_")
        ):
            monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("GREEN_API_INSTANCE_ID", "100")
    monkeypatch.setenv("GREEN_API_TOKEN", "token-principal")
    monkeypatch.setenv("GREEN_API_INSTANCE_ID_2", "200")
    monkeypatch.setenv("GREEN_API_TOKEN_2", "token-secundaria")
    for index, zona in enumerate(scheduler.ZONAS, start=1):
        monkeypatch.setenv(zona["env_key"], f"zona-{index}@g.us")

    accounts = wa.get_accounts()

    assert [account.label for account in accounts] == ["principal", "secundaria"]
    assert accounts[0].group_ids == ("zona-1@g.us", "zona-2@g.us", "zona-3@g.us")
    assert accounts[1].group_ids == ("zona-4@g.us", "zona-5@g.us", "zona-6@g.us")
    assert wa.find_account_for_chat("zona-5@g.us", accounts).label == "secundaria"


def test_simple_respects_first_account_explicit_groups(clean_whatsapp_env, monkeypatch):
    from app import scheduler

    for key in list(os.environ):
        if key == "GREEN_API_ACCOUNTS" or key.startswith(
            ("GREEN_API_INSTANCE_ID", "GREEN_API_TOKEN", "WHATSAPP_GROUP_IDS", "WA_GROUP_")
        ):
            monkeypatch.delenv(key, raising=False)

    monkeypatch.setenv("GREEN_API_INSTANCE_ID", "100")
    monkeypatch.setenv("GREEN_API_TOKEN", "token-principal")
    monkeypatch.setenv("GREEN_API_INSTANCE_ID_2", "200")
    monkeypatch.setenv("GREEN_API_TOKEN_2", "token-secundaria")
    for index, zona in enumerate(scheduler.ZONAS, start=1):
        monkeypatch.setenv(zona["env_key"], f"zona-{index}@g.us")
    # La primera instancia ya estaba en estos 3 grupos, que no son los primeros.
    monkeypatch.setenv("WHATSAPP_GROUP_IDS", "zona-2@g.us,zona-4@g.us,zona-6@g.us")

    accounts = wa.get_accounts()

    assert accounts[0].group_ids == ("zona-2@g.us", "zona-4@g.us", "zona-6@g.us")
    assert accounts[1].group_ids == ("zona-1@g.us", "zona-3@g.us", "zona-5@g.us")


def test_simple_second_account_requires_token(clean_whatsapp_env, monkeypatch):
    monkeypatch.setenv("GREEN_API_INSTANCE_ID", "100")
    monkeypatch.setenv("GREEN_API_TOKEN", "token-principal")
    monkeypatch.setenv("GREEN_API_INSTANCE_ID_2", "200")

    with pytest.raises(RuntimeError, match="GREEN_API_TOKEN_2"):
        wa.get_accounts()


def test_get_accounts_json_and_routing(clean_whatsapp_env, monkeypatch):
    monkeypatch.setenv("GREEN_API_ACCOUNTS", _accounts_json())

    accounts = wa.get_accounts()

    assert [account.label for account in accounts] == ["principal", "secundaria"]
    assert wa.find_account_for_chat("g4@g.us", accounts).label == "secundaria"
    assert wa.find_account_for_chat("desconocido@g.us", accounts) is None


def test_duplicate_group_is_assigned_to_first_account(clean_whatsapp_env, monkeypatch):
    raw = json.dumps(
        [
            {"label": "a", "instance_id": "1", "token": "t1", "group_ids": ["g1@g.us"]},
            {
                "label": "b",
                "instance_id": "2",
                "token": "t2",
                "group_ids": ["g1@g.us", "g2@g.us"],
            },
        ]
    )
    monkeypatch.setenv("GREEN_API_ACCOUNTS", raw)

    accounts = wa.get_accounts()

    assert accounts[0].group_ids == ("g1@g.us",)
    assert accounts[1].group_ids == ("g2@g.us",)


def test_invalid_json_raises(clean_whatsapp_env, monkeypatch):
    monkeypatch.setenv("GREEN_API_ACCOUNTS", "{no-es-json")

    with pytest.raises(RuntimeError, match="JSON"):
        wa.get_accounts()


def test_send_red_alert_fans_out_to_all_accounts(clean_whatsapp_env, monkeypatch):
    monkeypatch.setenv("GREEN_API_ACCOUNTS", _accounts_json())
    calls = []

    def fake_send(instance_id, token, chat_id, message, max_retries=3):
        calls.append((instance_id, chat_id))
        return {"idMessage": chat_id}

    monkeypatch.setattr(wa, "_send_message", fake_send)

    results = wa.send_red_alert("grid-1", -7.16, -78.5, 0.9)

    assert calls == [
        ("100", "g1@g.us"),
        ("100", "g2@g.us"),
        ("200", "g3@g.us"),
        ("200", "g4@g.us"),
    ]
    assert all(result["status"] == "ok" for result in results)


def test_send_message_to_chat_routes_and_rejects_unknown(clean_whatsapp_env, monkeypatch):
    monkeypatch.setenv("GREEN_API_ACCOUNTS", _accounts_json())

    def fake_send(instance_id, token, chat_id, message, max_retries=3):
        return {"instance": instance_id, "chat": chat_id}

    monkeypatch.setattr(wa, "_send_message", fake_send)
    accounts = wa.get_accounts()

    result = wa.send_message_to_chat("g4@g.us", "hola", accounts=accounts)
    assert result["account"] == "secundaria"

    with pytest.raises(RuntimeError, match="no está asignado"):
        wa.send_message_to_chat("desconocido@g.us", "hola", accounts=accounts)


def test_send_message_error_does_not_leak_token(clean_whatsapp_env, monkeypatch):
    class FakeResponse:
        status_code = 466
        text = '{"error":"group limit","token":"SUPER_SECRETO"}'

        def json(self):
            return {}

    monkeypatch.setattr(wa.requests, "post", lambda *args, **kwargs: FakeResponse())

    with pytest.raises(wa.GreenAPIError) as exc:
        wa._send_message("100", "SUPER_SECRETO", "g1@g.us", "hola", max_retries=1)

    assert "466" in str(exc.value)
    assert "SUPER_SECRETO" not in str(exc.value)


def test_scheduler_routes_each_zone_to_its_account(clean_whatsapp_env, monkeypatch):
    from app import scheduler

    zone_groups = {
        zona["env_key"]: f"zona-{index}@g.us"
        for index, zona in enumerate(scheduler.ZONAS, start=1)
    }
    for key, value in zone_groups.items():
        monkeypatch.setenv(key, value)

    group_ids = list(zone_groups.values())
    raw = json.dumps(
        [
            {
                "label": "principal",
                "instance_id": "100",
                "token": "token-principal",
                "group_ids": group_ids[:3],
            },
            {
                "label": "secundaria",
                "instance_id": "200",
                "token": "token-secundaria",
                "group_ids": group_ids[3:],
            },
        ]
    )
    monkeypatch.setenv("GREEN_API_ACCOUNTS", raw)
    monkeypatch.setattr(scheduler, "_fetch_risk_data", lambda: [{}])
    monkeypatch.setattr(
        scheduler,
        "_classify_zone",
        lambda features, zona: {"nombre": zona["nombre"], "nivel": "Verde"},
    )
    monkeypatch.setattr(scheduler, "_build_message", lambda info: "mensaje de prueba")

    calls = []

    def fake_send(chat_id, message, accounts=None):
        account = wa.find_account_for_chat(chat_id, accounts)
        calls.append((chat_id, account.label))
        return {"chat_id": chat_id, "account": account.label, "response": {}}

    monkeypatch.setattr(scheduler, "send_message_to_chat", fake_send)

    asyncio.run(scheduler.run_daily_alerts())

    assert [account for _, account in calls] == [
        "principal",
        "principal",
        "principal",
        "secundaria",
        "secundaria",
        "secundaria",
    ]
