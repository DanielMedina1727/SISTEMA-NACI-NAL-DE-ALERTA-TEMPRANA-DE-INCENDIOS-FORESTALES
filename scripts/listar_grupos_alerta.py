import sys
import io
import requests

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

instance_id = "710722761252"
token = "fd6f6e4abf7142cd9a4d01884a6db6874c46150df0754953b6"

url = f"https://api.green-api.com/waInstance{instance_id}/getChats/{token}"
r = requests.get(url, timeout=20)
chats = r.json()

todos_grupos = [c for c in chats if str(c.get("id", "")).endswith("@g.us")]
grupos_alerta = [c for c in todos_grupos if "AlertaForestal" in str(c.get("name", ""))]

print(f"=== GRUPOS AlertaForestal encontrados: {len(grupos_alerta)} de {len(todos_grupos)} grupos totales ===\n")

ids = []
for g in grupos_alerta:
    nombre = g.get("name", "")
    chat_id = g.get("id", "")
    ids.append(chat_id)
    print(f"  Nombre : {nombre}")
    print(f"  ChatID : {chat_id}")
    print()

if not grupos_alerta:
    print("No se encontraron grupos con 'AlertaForestal' en el nombre.")
    print("Puede que esten archivados — la API de Green API los incluye igual.")
    print("\nTodos los grupos disponibles:")
    for g in todos_grupos:
        nombre = g.get("name", "")
        chat_id = g.get("id", "")
        print(f"  {nombre} => {chat_id}")
else:
    print("\n=== LINEA PARA EL .env ===")
    print(f"WHATSAPP_GROUP_IDS={','.join(ids)}")
