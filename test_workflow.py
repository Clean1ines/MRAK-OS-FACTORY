import requests
import json

base_url = "https://mrak-os-factory.onrender.com"

# 1. Создать workflow
print("Создание workflow...")
wf_resp = requests.post(f"{base_url}/api/workflows", json={
    "name": "Test Workflow",
    "description": "Простой тестовый пайплайн",
    "is_default": False
})
wf_resp.raise_for_status()
workflow_id = wf_resp.json()["id"]
print(f"✅ Workflow создан с ID: {workflow_id}")

# 2. Добавить узлы
nodes = [
    {"node_id": "node_1", "prompt_key": "02_IDEA_CLARIFIER", "position_x": 100, "position_y": 100},
    {"node_id": "node_2", "prompt_key": "03_PRODUCT_COUNCIL", "position_x": 300, "position_y": 100},
    {"node_id": "node_3", "prompt_key": "04_BUSINESS_REQ_GEN", "position_x": 500, "position_y": 100},
]
for node in nodes:
    resp = requests.post(f"{base_url}/api/workflows/{workflow_id}/nodes", json=node)
    resp.raise_for_status()
    print(f"✅ Узел {node['node_id']} создан (record_id: {resp.json()['id']})")

# 3. Добавить рёбра
edges = [
    {"source_node": "node_1", "target_node": "node_2"},
    {"source_node": "node_2", "target_node": "node_3"},
]
for edge in edges:
    resp = requests.post(f"{base_url}/api/workflows/{workflow_id}/edges", json={
        "source_node": edge["source_node"],
        "target_node": edge["target_node"],
        "source_output": "output",
        "target_input": "input"
    })
    resp.raise_for_status()
    print(f"✅ Ребро {edge['source_node']} → {edge['target_node']} создано (id: {resp.json()['id']})")

# 4. Получить полный workflow
get_resp = requests.get(f"{base_url}/api/workflows/{workflow_id}")
get_resp.raise_for_status()
print("\n📦 Полученный workflow:")
print(json.dumps(get_resp.json(), indent=2, ensure_ascii=False))