# -*- coding: utf-8 -*-
"""Lista los grupos de todas las cuentas Green API configuradas.

Uso:
    python scripts/listar_grupos_alerta.py

Requiere GREEN_API_INSTANCE_ID/GREEN_API_TOKEN en .env. Para varias cuentas,
agrega GREEN_API_INSTANCE_ID_2/GREEN_API_TOKEN_2; los grupos se reparten solos.
No contiene credenciales hardcodeadas.
"""
from __future__ import annotations

import json
import logging
import os
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.whatsapp_alerts import get_accounts, get_linked_groups

logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")


def main() -> int:
    try:
        accounts = get_accounts()
    except RuntimeError as exc:
        print(f"❌ {exc}")
        return 1

    print("Cuentas configuradas y grupos asignados:")
    for account in accounts:
        print(
            f"  - {account.label}: instancia {account.instance_id}, "
            f"{len(account.group_ids)} grupo(s)"
        )
        for chat_id in account.group_ids:
            print(f"      {chat_id}")

    groups = get_linked_groups()
    if not groups:
        print("\nNo se encontraron grupos. Verifica que cada número esté en sus grupos.")
        return 0

    print(f"\nGrupos encontrados: {len(groups)}\n")
    for group in groups:
        print(f"  [{group['account']}] {group['name']}")
        print(f"    ChatID: {group['id']}")
        print()

    # Esqueleto listo para pegar en .env (los tokens se completan a mano).
    skeleton = []
    for account in accounts:
        ids = [group["id"] for group in groups if group["account"] == account.label]
        skeleton.append(
            {
                "label": account.label,
                "instance_id": account.instance_id,
                "token": "COMPLETAR_TOKEN",
                "group_ids": ids,
            }
        )

    print("Fragmento para GREEN_API_ACCOUNTS (reemplaza COMPLETAR_TOKEN):")
    print(
        "GREEN_API_ACCOUNTS='"
        + json.dumps(skeleton, ensure_ascii=False, separators=(",", ":"))
        + "'"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
