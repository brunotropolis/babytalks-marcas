import os, json, urllib.request, urllib.error

BASE = "https://n8n-n8n.xktssy.easypanel.host"
SHEET = "1B6QvnWo36Xu6vobVJXx_bmRw7CPFeUnXWXtQ7zG3JHQ"
CRED_ID = "8fMI5lX6WRmrn4Cy"
CRED_NAME = "Google Sheets"
SECRET = "9fKq2Wm7Zx4Lp"
LOAD_PATH = f"bt-marcas-{SECRET}"
SAVE_PATH = f"bt-marcas-{SECRET}-save"

# read API key from vault
KEY = None
with open("D:/CLAUDE/.env.meta", encoding="utf-8") as f:
    for line in f:
        if line.startswith("N8N_API_KEY"):
            KEY = line.split("=", 1)[1].strip().strip('"')
            break
assert KEY, "no N8N_API_KEY"

def req(method, path, body=None):
    url = BASE + path
    data = json.dumps(body).encode() if body is not None else None
    r = urllib.request.Request(url, data=data, method=method,
        headers={"X-N8N-API-KEY": KEY, "Content-Type": "application/json", "Accept": "application/json"})
    try:
        with urllib.request.urlopen(r) as resp:
            return resp.status, json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()

cors = {"responseHeaders": {"entries": [{"name": "Access-Control-Allow-Origin", "value": "*"}]}}
gs_cred = {"googleSheetsOAuth2Api": {"id": CRED_ID, "name": CRED_NAME}}

nodes = [
    # ---- LOAD flow ----
    {"id": "wLoad", "name": "WEBHOOK LOAD", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
     "position": [0, 0], "webhookId": LOAD_PATH,
     "parameters": {"httpMethod": "GET", "path": LOAD_PATH, "responseMode": "responseNode", "options": {}}},
    {"id": "hRead", "name": "HTTP READ", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [220, 0],
     "parameters": {"method": "GET",
        "url": f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/A1",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "googleSheetsOAuth2Api",
        "options": {}},
     "credentials": gs_cred},
    {"id": "rLoad", "name": "RESPOND LOAD", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
     "position": [440, 0],
     "parameters": {"respondWith": "text",
        "responseBody": "={{ ($json.values && $json.values[0] && $json.values[0][0]) || '[]' }}",
        "options": cors}},
    # ---- SAVE flow ----
    {"id": "wSave", "name": "WEBHOOK SAVE", "type": "n8n-nodes-base.webhook", "typeVersion": 2,
     "position": [0, 240], "webhookId": SAVE_PATH,
     "parameters": {"httpMethod": "POST", "path": SAVE_PATH, "responseMode": "responseNode", "options": {}}},
    {"id": "hWrite", "name": "HTTP WRITE", "type": "n8n-nodes-base.httpRequest", "typeVersion": 4.2,
     "position": [220, 240],
     "parameters": {"method": "PUT",
        "url": f"https://sheets.googleapis.com/v4/spreadsheets/{SHEET}/values/A1",
        "authentication": "predefinedCredentialType", "nodeCredentialType": "googleSheetsOAuth2Api",
        "sendQuery": True, "queryParameters": {"parameters": [{"name": "valueInputOption", "value": "RAW"}]},
        "sendBody": True, "specifyBody": "json",
        "jsonBody": "={{ JSON.stringify({ values: [[ typeof $json.body === 'string' ? $json.body : JSON.stringify($json.body) ]] }) }}",
        "options": {}},
     "credentials": gs_cred},
    {"id": "rSave", "name": "RESPOND SAVE", "type": "n8n-nodes-base.respondToWebhook", "typeVersion": 1.1,
     "position": [440, 240],
     "parameters": {"respondWith": "json", "responseBody": "={{ JSON.stringify({ok:true}) }}", "options": cors}},
]

connections = {
    "WEBHOOK LOAD": {"main": [[{"node": "HTTP READ", "type": "main", "index": 0}]]},
    "HTTP READ": {"main": [[{"node": "RESPOND LOAD", "type": "main", "index": 0}]]},
    "WEBHOOK SAVE": {"main": [[{"node": "HTTP WRITE", "type": "main", "index": 0}]]},
    "HTTP WRITE": {"main": [[{"node": "RESPOND SAVE", "type": "main", "index": 0}]]},
}

wf = {"name": "BABY TALKS | Marcas API", "nodes": nodes, "connections": connections,
      "settings": {"executionOrder": "v1"}}

st, res = req("POST", "/api/v1/workflows", wf)
print("create:", st)
if st not in (200, 201):
    print(res); raise SystemExit(1)
wid = res["id"]
print("workflow id:", wid)
st2, _ = req("POST", f"/api/v1/workflows/{wid}/activate")
print("activate:", st2)
print("LOAD_URL:", f"{BASE}/webhook/{LOAD_PATH}")
print("SAVE_URL:", f"{BASE}/webhook/{SAVE_PATH}")
print("SECRET:", SECRET)
