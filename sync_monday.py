"""Pull Abi's group from the shared Monday board into data/abi-levine.js.
Usage: MONDAY_TOKEN=... MONDAY_BOARD_ID=... python3 sync_monday.py

Only items with the "C.Dashboard" checkbox ticked are published.
 - "Client Action" also ticked -> shows under "Needed from <client>" (item name is shown
   to the client as written, so word it for them). Status Done = checked off.
 - otherwise -> a deliverable card (Status Done = green).
Priority and Person columns are never read.
"""
import json, os, urllib.request, datetime

CLIENT, OUT, GROUP = "Abi Levine", "abi-levine-09c9mv9mvn/data/abi-levine.js", "Abi Levine"
# Optional friendlier client-facing wording for deliverables: keyword -> (name, description)
DELIVERABLES = {
    "Video Ads": ("5 Initial AI Videos", "Five AI video ads for your campaign, built and ready for your review."),
    "Facebook Page": ("Facebook Page Populated", "Your Facebook page set up and filled with content."),
    "Media Buying": ("Facebook Ads Built", "Your ads built in Meta Ads Manager, ready to launch."),
}
DONE, WORKING = "Done", {"Working on it", "In Progress", "Stuck"}

Q = """query($b:[ID!]){boards(ids:$b){items_page(limit:200){items{name group{title}
  column_values{text column{title}} subitems{column_values{text column{title}}}}}}}"""
req = urllib.request.Request("https://api.monday.com/v2", method="POST",
    data=json.dumps({"query": Q, "variables": {"b": [os.environ["MONDAY_BOARD_ID"]]}}).encode(),
    headers={"Content-Type": "application/json", "Authorization": os.environ["MONDAY_TOKEN"], "API-Version": "2024-10"})
res = json.load(urllib.request.urlopen(req))
if "errors" in res: raise SystemExit(res["errors"])

def col(cols, title): return next((c["text"] or "" for c in cols if c["column"]["title"] == title), "")
def checked(cols, title): return bool(col(cols, title).strip())  # Monday checkbox text is "v" when ticked

ms, actions = [], []
for it in res["data"]["boards"][0]["items_page"]["items"]:
    cv = it["column_values"]
    if it["group"]["title"] != GROUP or not checked(cv, "C.Dashboard"): continue
    status, due = col(cv, "Status"), col(cv, "Deadline") or None
    if checked(cv, "Client Action"):
        actions.append({"name": it["name"], "due": due, "done": status == DONE})
        continue
    name, desc = next((v for k, v in DELIVERABLES.items() if k.lower() in it["name"].lower()), (it["name"], ""))
    subs = it.get("subitems") or []
    ms.append({"name": name, "description": desc, "due": due,
        "status": "done" if status == DONE else "in_progress" if status in WORKING else "not_started",
        "tasksDone": sum(col(x["column_values"], "Status") == DONE for x in subs), "tasksTotal": len(subs)})
def load_old():
    try: return json.loads(open(OUT).read().split("=", 1)[1].rstrip().rstrip(";"))
    except Exception: return None
old = load_old()
data = {"client": CLIENT, "updatedAt": datetime.datetime.now().astimezone().isoformat(), "actions": actions, "milestones": ms}
if old and {k: v for k, v in old.items() if k != "updatedAt"} == {k: v for k, v in data.items() if k != "updatedAt"}:
    data["updatedAt"] = old["updatedAt"]
open(OUT, "w").write("window.DASHBOARD = " + json.dumps(data, indent=2) + ";\n")
print("Synced", len(ms), "deliverables,", len(actions), "client actions")
