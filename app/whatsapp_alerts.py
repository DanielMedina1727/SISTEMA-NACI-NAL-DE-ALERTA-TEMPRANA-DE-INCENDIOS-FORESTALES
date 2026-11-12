"""
Envía alertas de incendio forestal a grupos de WhatsApp usando Green API.

Green API es un servicio freemium que permite enviar mensajes a grupos reales
de WhatsApp vinculando un número mediante código QR (sin WhatsApp Business).

Soporta una o varias instancias de Green API. Esto es útil porque el plan Free
permite 3 grupos por instancia: se pueden repartir, por ejemplo, 6 grupos entre
dos cuentas.

Configuración rápida:
  1. Regístrate en https://green-api.com/ y crea una instancia.
  2. Escanea el QR con el número de WhatsApp que enviará los mensajes.
  3. En el panel, usa getChats para obtener los IDs de grupo
     (formato 120363XXXXXXXXXXXXXXXX@g.us).
  4. Configura el .env:

     Opción A (recomendada, solo editas credenciales):
       GREEN_API_INSTANCE_ID=...
       GREEN_API_TOKEN=...
       GREEN_API_INSTANCE_ID_2=...
       GREEN_API_TOKEN_2=...

       El sistema reparte automáticamente los ChatID de WHATSAPP_GROUP_IDS y
       WA_GROUP_* entre las cuentas. Con 2 cuentas y 6 grupos: 3 y 3.

     Opción B (avanzada, asignación manual de grupos):
       GREEN_API_ACCOUNTS='[{"label":"principal","instance_id":"...","token":"...","group_ids":["...","..."]},{"label":"secundaria","instance_id":"...","token":"...","group_ids":["...","..."]}]'

  Si no se usa GREEN_API_ACCOUNTS, se leen los pares INSTANCE_ID/TOKEN
  numerados. Cada WA_GROUP_* queda asignado automáticamente a una cuenta.

Variables de entorno:
  GREEN_API_INSTANCE_ID[_N] / GREEN_API_TOKEN[_N] → cuentas numeradas.
  GREEN_API_ACCOUNTS  → JSON para asignar grupos manualmente (avanzado).
  WHATSAPP_GROUP_IDS / WA_GROUP_* → ChatID que se reparten entre las cuentas.
  GREEN_API_MAX_GROUPS_PER_INSTANCE → aviso de límite (por defecto 3; 0 lo apaga).
"""

from __future__ import annotations

import json
import logging
import os
import time
from dataclasses import dataclass
from typing import Iterable

import requests
from dotenv import load_dotenv

from app.zones import ZONAS, ZONE_GROUP_ENV_KEYS

load_dotenv()

logger = logging.getLogger(__name__)

_GREEN_API_BASE = "https://api.green-api.com/waInstance{instance_id}/{method}/{token}"
_RETRY_STATUS = {429, 500, 502, 503, 504}
_PLACEHOLDER_HINTS = ("tu_", "your_", "xxxx", "ejemplo", "example", "completar", "cambiar")
_WARNED_LIMITS: set[tuple[str, int]] = set()


class GreenAPIError(RuntimeError):
    """Error sanitizado de Green API (nunca incluye el token en el mensaje)."""

    def __init__(self, message: str, status_code: int | None = None, detail: str = "") -> None:
        super().__init__(message)
        self.status_code = status_code
        self.detail = detail


@dataclass(frozen=True)
class GreenAccount:
    """Una instancia de Green API y los chats que le corresponden."""

    label: str
    instance_id: str
    token: str
    group_ids: tuple[str, ...]

    def __repr__(self) -> str:  # evita filtrar el token en logs/tracebacks
        return (
            f"GreenAccount(label={self.label!r}, instance_id={self.instance_id!r}, "
            f"groups={len(self.group_ids)})"
        )


def _clean(value: object) -> str:
    return str(value).strip() if value is not None else ""


def _is_placeholder(value: str) -> bool:
    low = value.lower()
    return not low or any(hint in low for hint in _PLACEHOLDER_HINTS)


def _mask_chat(chat_id: str) -> str:
    if len(chat_id) <= 12:
        return chat_id
    return f"{chat_id[:6]}...{chat_id[-4:]}"


def _split_group_ids(value: object) -> list[str]:
    if isinstance(value, str):
        parts: Iterable[object] = value.split(",")
    elif isinstance(value, (list, tuple, set)):
        parts = value
    else:
        parts = []
    return [str(part).strip() for part in parts if part is not None and str(part).strip()]


def _dedupe(values: Iterable[str]) -> list[str]:
    seen: set[str] = set()
    result: list[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            result.append(value)
    return result


def _valid_chat_id(chat_id: str) -> bool:
    return chat_id.endswith("@g.us") or chat_id.endswith("@c.us")


def _parse_accounts_json(raw: str) -> list[GreenAccount]:
    """Convierte GREEN_API_ACCOUNTS en una lista de cuentas validadas."""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(
            "GREEN_API_ACCOUNTS no es JSON válido. Debe ser una lista JSON en una sola línea; "
            "revisa comas, corchetes y comillas."
        ) from exc

    if isinstance(data, dict) and ("instance_id" in data or "idInstance" in data):
        items: list[tuple[str, object]] = [("principal", data)]
    elif isinstance(data, dict):
        items = list(data.items())
    elif isinstance(data, list):
        items = [(f"cuenta_{index + 1}", item) for index, item in enumerate(data)]
    else:
        raise RuntimeError("GREEN_API_ACCOUNTS debe ser una lista JSON de cuentas.")

    accounts: list[GreenAccount] = []
    assigned: dict[str, str] = {}
    labels: set[str] = set()
    for fallback_label, item in items:
        if not isinstance(item, dict):
            raise RuntimeError(f"La cuenta {fallback_label!r} debe ser un objeto JSON.")

        label = _clean(item.get("label") or fallback_label) or "cuenta"
        if label in labels:
            raise RuntimeError(f"El label {label!r} está repetido en GREEN_API_ACCOUNTS.")
        labels.add(label)
        instance_id = _clean(item.get("instance_id") or item.get("idInstance"))
        token = _clean(item.get("token") or item.get("apiTokenInstance"))
        raw_groups = item.get("group_ids", item.get("groups", item.get("chat_ids", [])))
        groups = _split_group_ids(raw_groups)

        if not instance_id or _is_placeholder(instance_id):
            raise RuntimeError(f"Cuenta {label!r}: falta un instance_id válido en GREEN_API_ACCOUNTS.")
        if not token or _is_placeholder(token):
            raise RuntimeError(f"Cuenta {label!r}: falta un token válido en GREEN_API_ACCOUNTS.")

        unique_groups: list[str] = []
        for chat_id in groups:
            if "..." in chat_id or "xxxx" in chat_id.lower():
                logger.warning(
                    "Cuenta %s: el ChatID %s parece un ejemplo; se omite hasta que lo reemplaces.",
                    label,
                    _mask_chat(chat_id),
                )
                continue
            if not _valid_chat_id(chat_id):
                logger.warning(
                    "Cuenta %s: el ChatID %s no termina en @g.us ni @c.us; se usará igual.",
                    label,
                    _mask_chat(chat_id),
                )
            if chat_id in assigned:
                if assigned[chat_id] == label:
                    logger.warning(
                        "Cuenta %s: el ChatID %s está repetido; se enviará una sola vez.",
                        label,
                        _mask_chat(chat_id),
                    )
                else:
                    logger.warning(
                        "ChatID %s repetido en las cuentas %s y %s; se enviará solo por %s.",
                        _mask_chat(chat_id),
                        assigned[chat_id],
                        label,
                        assigned[chat_id],
                    )
                continue
            assigned[chat_id] = label
            unique_groups.append(chat_id)

        if not unique_groups:
            logger.warning(
                "Cuenta %s: no tiene group_ids; se podrá usar para descubrir grupos, "
                "pero no enviará mensajes hasta que se agreguen.",
                label,
            )
        accounts.append(
            GreenAccount(
                label=label,
                instance_id=instance_id,
                token=token,
                group_ids=tuple(unique_groups),
            )
        )

    if not accounts:
        raise RuntimeError("GREEN_API_ACCOUNTS no contiene ninguna cuenta.")
    return accounts


def _legacy_account() -> GreenAccount | None:
    """Cuenta única de compatibilidad con GREEN_API_INSTANCE_ID/TOKEN."""
    instance_id = _clean(os.getenv("GREEN_API_INSTANCE_ID"))
    token = _clean(os.getenv("GREEN_API_TOKEN"))
    groups = _split_group_ids(os.getenv("WHATSAPP_GROUP_IDS"))

    if not groups:
        zone_groups: list[str] = []
        for key in sorted(key for key in os.environ if key.startswith("WA_GROUP_")):
            zone_groups.extend(_split_group_ids(os.getenv(key)))
        groups = zone_groups

    if not instance_id and not token and not groups:
        return None
    if any("xxxx" in group.lower() or "..." in group for group in groups):
        raise RuntimeError(
            "WHATSAPP_GROUP_IDS contiene ChatID de ejemplo; reemplázalos por los IDs reales "
            "que obtienes con getChats en el panel de Green API."
        )
    if not instance_id or _is_placeholder(instance_id):
        raise RuntimeError(
            "Falta GREEN_API_INSTANCE_ID en .env — regístrate en https://green-api.com/ "
            "y copia tu idInstance."
        )
    if not token or _is_placeholder(token):
        raise RuntimeError(
            "Falta GREEN_API_TOKEN en .env — copia el apiTokenInstance desde el panel de Green API."
        )
    if not groups:
        raise RuntimeError(
            "Falta WHATSAPP_GROUP_IDS en .env — usa getChats en el panel de Green API "
            "para obtener los IDs de tus grupos."
        )
    return GreenAccount(
        label="principal",
        instance_id=instance_id,
        token=token,
        group_ids=tuple(_dedupe(groups)),
    )


_SIMPLE_LABELS = ("principal", "secundaria", "terciaria")


def _simple_credentials() -> list[tuple[str, str, str]]:
    """Lee GREEN_API_INSTANCE_ID[_N] y GREEN_API_TOKEN[_N] en orden."""
    credentials: list[tuple[str, str, str]] = []
    index = 1
    while True:
        suffix = "" if index == 1 else f"_{index}"
        instance_id = _clean(os.getenv(f"GREEN_API_INSTANCE_ID{suffix}"))
        token = _clean(os.getenv(f"GREEN_API_TOKEN{suffix}"))

        if not instance_id and not token:
            break
        if not instance_id or _is_placeholder(instance_id):
            raise RuntimeError(
                f"Falta GREEN_API_INSTANCE_ID{suffix} válido en .env — "
                "copia el idInstance de esa instancia de Green API."
            )
        if not token or _is_placeholder(token):
            raise RuntimeError(
                f"Falta GREEN_API_TOKEN{suffix} válido en .env — "
                "copia el apiTokenInstance de esa instancia de Green API."
            )

        label = _SIMPLE_LABELS[index - 1] if index <= len(_SIMPLE_LABELS) else f"cuenta_{index}"
        credentials.append((label, instance_id, token))
        index += 1

    return credentials


def _known_group_ids() -> list[str]:
    """Reúne los ChatID de las zonas y de WHATSAPP_GROUP_IDS, sin duplicados."""
    groups: list[str] = []
    for env_key in ZONE_GROUP_ENV_KEYS:
        groups.extend(_split_group_ids(os.getenv(env_key)))
    groups.extend(_split_group_ids(os.getenv("WHATSAPP_GROUP_IDS")))

    zone_keys = set(ZONE_GROUP_ENV_KEYS)
    for env_key in sorted(key for key in os.environ if key.startswith("WA_GROUP_") and key not in zone_keys):
        groups.extend(_split_group_ids(os.getenv(env_key)))

    return _dedupe(
        group
        for group in groups
        if "..." not in group and "xxxx" not in group.lower()
    )


def _chunk_groups(groups: list[str], parts: int) -> list[tuple[str, ...]]:
    """Divide una lista de grupos en partes contiguas lo más parejas posible."""
    if parts <= 0:
        return []
    base, remainder = divmod(len(groups), parts)
    chunks: list[tuple[str, ...]] = []
    start = 0
    for index in range(parts):
        size = base + (1 if index < remainder else 0)
        chunks.append(tuple(groups[start:start + size]))
        start += size
    return chunks


def _simple_accounts() -> list[GreenAccount]:
    """Crea cuentas numeradas y reparte los grupos automáticamente.

    Si WHATSAPP_GROUP_IDS contiene hasta 3 grupos (lo habitual: los que ya
    tenía la primera instancia), se respetan como grupos de la cuenta
    principal y el resto se reparte entre las cuentas secundarias. Si no,
    todos los grupos se reparten en partes parejas. Así el usuario solo edita
    los pares INSTANCE_ID/TOKEN.
    """
    credentials = _simple_credentials()
    if not credentials:
        return []
    if len(credentials) == 1:
        legacy = _legacy_account()
        return [legacy] if legacy else []

    all_groups = _known_group_ids()
    if not all_groups:
        raise RuntimeError(
            "Configuraste una segunda instancia Green API, pero no hay ChatID en "
            "WHATSAPP_GROUP_IDS ni en WA_GROUP_* para repartir entre las cuentas."
        )

    first_explicit = _dedupe(
        group
        for group in _split_group_ids(os.getenv("WHATSAPP_GROUP_IDS"))
        if "..." not in group and "xxxx" not in group.lower()
    )

    if 0 < len(first_explicit) <= 3:
        # Respetar los grupos que ya tenía la primera instancia; el resto se
        # reparte entre las secundarias.
        first_groups = list(first_explicit)
        remaining = [g for g in all_groups if g not in set(first_groups)]
        other_credentials = credentials[1:]
        other_chunks = _chunk_groups(remaining, len(other_credentials))

        accounts = [
            GreenAccount(
                label=credentials[0][0],
                instance_id=credentials[0][1],
                token=credentials[0][2],
                group_ids=tuple(first_groups),
            )
        ]
        for (label, instance_id, token), chunk in zip(other_credentials, other_chunks):
            accounts.append(
                GreenAccount(
                    label=label,
                    instance_id=instance_id,
                    token=token,
                    group_ids=chunk,
                )
            )
        return accounts

    chunks = _chunk_groups(all_groups, len(credentials))
    return [
        GreenAccount(
            label=label,
            instance_id=instance_id,
            token=token,
            group_ids=chunk,
        )
        for (label, instance_id, token), chunk in zip(credentials, chunks)
    ]


def _warn_group_limits(accounts: list[GreenAccount]) -> None:
    raw_limit = _clean(os.getenv("GREEN_API_MAX_GROUPS_PER_INSTANCE", "3"))
    try:
        limit = int(raw_limit) if raw_limit else 0
    except ValueError:
        limit = 3
    if limit <= 0:
        return
    for account in accounts:
        key = (account.label, len(account.group_ids))
        if len(account.group_ids) > limit and key not in _WARNED_LIMITS:
            _WARNED_LIMITS.add(key)
            logger.warning(
                "La cuenta %s tiene %d grupos; el plan Free de Green API permite %d por "
                "instancia. Agrega otra instancia (GREEN_API_INSTANCE_ID_3/TOKEN_3) "
                "o usa un plan superior.",
                account.label,
                len(account.group_ids),
                limit,
            )


def get_accounts() -> list[GreenAccount]:
    """Devuelve las cuentas Green API configuradas (multi-instancia o única)."""
    raw_accounts = _clean(os.getenv("GREEN_API_ACCOUNTS"))
    if raw_accounts:
        if _clean(os.getenv("GREEN_API_INSTANCE_ID_2")):
            logger.warning(
                "GREEN_API_ACCOUNTS está definido y tiene prioridad; "
                "se ignoran GREEN_API_INSTANCE_ID_2/GREEN_API_TOKEN_2."
            )
        accounts = _parse_accounts_json(raw_accounts)
    else:
        accounts = _simple_accounts()

    if not accounts:
        raise RuntimeError(
            "No hay cuentas Green API configuradas. Define GREEN_API_INSTANCE_ID/"
            "GREEN_API_TOKEN (y _2 para otra cuenta) o GREEN_API_ACCOUNTS."
        )
    _warn_group_limits(accounts)
    return accounts


def _get_config() -> tuple[str, str, list[str]]:
    """Compatibilidad: devuelve la primera cuenta configurada.

    Para el envío a todas las cuentas usa :func:`get_accounts` y
    :func:`send_message_to_chat`.
    """
    account = get_accounts()[0]
    if not account.group_ids:
        raise RuntimeError("La primera cuenta Green API no tiene group_ids configurados.")
    return account.instance_id, account.token, list(account.group_ids)


def find_account_for_chat(
    chat_id: str,
    accounts: list[GreenAccount] | None = None,
) -> GreenAccount | None:
    """Busca la cuenta que tiene asignado un ChatID.

    Si no se usa GREEN_API_ACCOUNTS y hay una sola cuenta (modo compatibilidad),
    se usa esa cuenta aunque el chat no esté en su lista; así no se rompen las
    configuraciones antiguas. En modo multi-cuenta el chat debe estar asignado.
    """
    accounts = accounts if accounts is not None else get_accounts()
    for account in accounts:
        if chat_id in account.group_ids:
            return account
    if len(accounts) == 1 and not _clean(os.getenv("GREEN_API_ACCOUNTS")):
        return accounts[0]
    return None


def _redact_token(text: str, token: str) -> str:
    """Reemplaza el token por *** si aparece en un texto de error."""
    return text.replace(token, "***") if token else text


def _safe_response_text(response: requests.Response, token: str) -> str:
    """Devuelve un extracto de la respuesta sin exponer el token."""
    return _redact_token((response.text or "").strip(), token)[:300]


def _send_message(
    instance_id: str,
    token: str,
    chat_id: str,
    message: str,
    max_retries: int = 3,
) -> dict:
    """Envía un mensaje de texto a un chatId usando Green API.

    Reintenta con backoff exponencial (1s, 2s, 4s) ante errores transitorios
    (429 o 5xx). Los errores se elevan como GreenAPIError sanitizado.
    """
    url = _GREEN_API_BASE.format(
        instance_id=instance_id,
        method="sendMessage",
        token=token,
    )
    payload = {"chatId": chat_id, "message": message}
    attempts = max(1, max_retries)

    for attempt in range(attempts):
        try:
            response = requests.post(url, json=payload, timeout=15)
        except requests.RequestException:
            if attempt < attempts - 1:
                time.sleep(2**attempt)
                continue
            raise GreenAPIError(
                "No se pudo conectar con Green API tras varios intentos."
            ) from None

        if response.status_code in _RETRY_STATUS and attempt < attempts - 1:
            time.sleep(2**attempt)
            continue

        if response.status_code >= 400:
            detail = _safe_response_text(response, token)
            raise GreenAPIError(
                f"Green API respondió HTTP {response.status_code}: {detail}",
                status_code=response.status_code,
                detail=detail,
            )

        try:
            return response.json()
        except ValueError:
            raise GreenAPIError(
                "Green API devolvió una respuesta que no es JSON.",
                status_code=response.status_code,
            ) from None

    raise GreenAPIError("No se pudo enviar el mensaje tras varios intentos.")


def send_message_to_chat(
    chat_id: str,
    message: str,
    accounts: list[GreenAccount] | None = None,
    max_retries: int = 3,
) -> dict:
    """Envía un mensaje al ChatID usando la cuenta que lo tiene asignado."""
    accounts = accounts if accounts is not None else get_accounts()
    account = find_account_for_chat(chat_id, accounts)
    if account is None:
        raise RuntimeError(
            f"El chat {_mask_chat(chat_id)} no está asignado a ninguna cuenta Green API. "
            "Revisa el reparto con `python -m app.whatsapp_alerts --plan` o usa "
            "GREEN_API_ACCOUNTS para asignarlo manualmente."
        )

    result = _send_message(
        account.instance_id,
        account.token,
        chat_id,
        message,
        max_retries=max_retries,
    )
    return {
        "chat_id": chat_id,
        "status": "ok",
        "account": account.label,
        "response": result,
    }


def send_red_alert(
    grid_id: str,
    lat: float,
    lon: float,
    confianza: float,
    nivel: str = "ROJO 🔴",
    extra_info: str | None = None,
) -> list[dict]:
    """Envía una alerta a todos los grupos de todas las cuentas configuradas."""
    accounts = get_accounts()

    targets: list[tuple[GreenAccount, str]] = []
    seen: set[str] = set()
    for account in accounts:
        for chat_id in account.group_ids:
            if chat_id not in seen:
                seen.add(chat_id)
                targets.append((account, chat_id))

    if not targets:
        raise RuntimeError(
            "Ninguna cuenta Green API tiene group_ids configurados. "
            "Define WHATSAPP_GROUP_IDS o WA_GROUP_* en .env."
        )

    mapa_url = f"https://www.google.com/maps?q={lat},{lon}"
    mensaje = (
        f"🔥 *ALERTA TEMPRANA DE INCENDIO FORESTAL*\n"
        f"━━━━━━━━━━━━━━━━━━━━\n"
        f"⚠️ Nivel: *{nivel}*\n"
        f"📍 Grilla: {grid_id}\n"
        f"🌐 Coordenadas: {lat:.4f}, {lon:.4f}\n"
        f"📊 Índice de riesgo: *{nivel}* (confianza interna: {confianza:.0%})\n"
        f"🗺️ Ver en mapa: {mapa_url}"
    )

    if extra_info:
        mensaje += f"\n\nℹ️ {extra_info}"

    mensaje += (
        "\n━━━━━━━━━━━━━━━━━━━━\n"
        "_Sistema Nacional de Alerta Temprana de Incendios Forestales_"
    )

    results: list[dict] = []
    for account, chat_id in targets:
        try:
            result = _send_message(account.instance_id, account.token, chat_id, mensaje)
            logger.info("✅ Alerta enviada a %s vía %s → %s", _mask_chat(chat_id), account.label, result)
            results.append(
                {"chat_id": chat_id, "account": account.label, "status": "ok", "response": result}
            )
        except GreenAPIError as exc:
            error_text = _redact_token(str(exc), account.token)
            logger.error(
                "❌ Error de Green API al enviar a %s vía %s: %s",
                _mask_chat(chat_id),
                account.label,
                error_text,
            )
            results.append(
                {
                    "chat_id": chat_id,
                    "account": account.label,
                    "status": "error",
                    "error": error_text,
                }
            )
        except Exception as exc:  # pragma: no cover - salvaguarda
            error_text = _redact_token(str(exc), account.token)
            logger.error(
                "❌ Error inesperado al enviar a %s vía %s: %s",
                _mask_chat(chat_id),
                account.label,
                error_text,
            )
            results.append(
                {
                    "chat_id": chat_id,
                    "account": account.label,
                    "status": "error",
                    "error": error_text,
                }
            )

    return results


def send_alert_by_level(
    grid_id: str,
    lat: float,
    lon: float,
    confianza: float,
    nivel_numerico: int,
) -> list[dict]:
    """Envía una alerta seleccionando el emoji/etiqueta según el nivel (1-3)."""
    niveles = {
        1: "AMARILLO 🟡",
        2: "AMARILLO 🟡",
        3: "ROJO 🔴",
    }
    nivel = niveles.get(nivel_numerico, "ROJO 🔴")
    return send_red_alert(grid_id=grid_id, lat=lat, lon=lon, confianza=confianza, nivel=nivel)


def get_linked_groups(account: GreenAccount | None = None) -> list[dict]:
    """Lista los grupos vinculados a una cuenta o a todas las cuentas.

    Returns:
        Lista de grupos con id, name, type, account e instance_id.
    """
    accounts = [account] if account else get_accounts()
    grupos: list[dict] = []

    for current in accounts:
        url = _GREEN_API_BASE.format(
            instance_id=current.instance_id,
            method="getChats",
            token=current.token,
        )
        try:
            response = requests.get(url, timeout=15)
        except requests.RequestException:
            logger.error("No se pudo conectar con Green API para la cuenta %s.", current.label)
            continue

        if response.status_code >= 400:
            logger.error(
                "Green API respondió HTTP %s al listar los chats de la cuenta %s.",
                response.status_code,
                current.label,
            )
            continue

        try:
            chats = response.json()
        except ValueError:
            logger.error("Green API devolvió una respuesta no JSON para la cuenta %s.", current.label)
            continue

        if not isinstance(chats, list):
            logger.error("Green API devolvió un formato inesperado para la cuenta %s.", current.label)
            continue

        for chat in chats:
            if not isinstance(chat, dict):
                continue
            if str(chat.get("id", "")).endswith("@g.us"):
                grupos.append(
                    {
                        "id": chat.get("id"),
                        "name": chat.get("name"),
                        "type": chat.get("type"),
                        "account": current.label,
                        "instance_id": current.instance_id,
                    }
                )
    return grupos


def _print_accounts(accounts: list[GreenAccount]) -> None:
    print("Cuentas Green API configuradas:")
    for account in accounts:
        print(
            f"  - {account.label}: instancia {account.instance_id}, "
            f"{len(account.group_ids)} grupo(s)"
        )


def _print_account_plan(accounts: list[GreenAccount]) -> None:
    zone_names: dict[str, str] = {}
    for zona in ZONAS:
        for chat_id in _split_group_ids(os.getenv(zona["env_key"])):
            zone_names.setdefault(chat_id, zona["nombre"])

    print("Asignación de grupos por cuenta:")
    for account in accounts:
        print(f"  {account.label}:")
        if not account.group_ids:
            print("    (sin grupos asignados)")
            continue
        for chat_id in account.group_ids:
            name = zone_names.get(chat_id)
            suffix = f"  ({name})" if name else ""
            print(f"    - {chat_id}{suffix}")


if __name__ == "__main__":
    import argparse
    import sys

    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")

    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
    parser = argparse.ArgumentParser(description="Lista grupos y prueba el envío por Green API.")
    parser.add_argument(
        "--send-test",
        action="store_true",
        help="Envía una alerta de prueba a todos los grupos configurados.",
    )
    parser.add_argument(
        "--plan",
        action="store_true",
        help="Muestra qué ChatID usará cada cuenta, sin llamar a Green API.",
    )
    args = parser.parse_args()

    if args.plan:
        print("\n📋 Calculando la asignación de grupos (sin llamar a Green API)...\n")
    else:
        print("\n📋 Consultando cuentas y grupos de Green API...\n")
    try:
        accounts = get_accounts()
    except RuntimeError as exc:
        print(f"⚠️  {exc}")
        print("\nConfigura GREEN_API_INSTANCE_ID/GREEN_API_TOKEN (y _2 si usas otra cuenta) en .env.")
        raise SystemExit(1) from None

    _print_accounts(accounts)
    if args.plan:
        print()
        _print_account_plan(accounts)
        raise SystemExit(0)

    print()
    grupos = get_linked_groups()
    if grupos:
        print(f"Encontrados {len(grupos)} grupo(s):\n")
        for grupo in grupos:
            print(f"  [{grupo['account']}] {grupo['name']}")
            print(f"    ChatID: {grupo['id']}")
            print()
    else:
        print("No se encontraron grupos. Verifica que el número esté en algún grupo.")
        print("También puedes usar el panel de Green API → getChats.\n")

    if args.send_test:
        print("📤 Enviando alerta de prueba a todos los grupos...\n")
        try:
            resultados = send_red_alert(
                grid_id="-78.5000_-7.1600",
                lat=-7.16,
                lon=-78.5,
                confianza=0.85,
            )
            print(json.dumps(resultados, indent=2, ensure_ascii=False))
        except RuntimeError as exc:
            print(f"⚠️  {exc}")
    else:
        print("Para enviar una prueba usa: python -m app.whatsapp_alerts --send-test")
