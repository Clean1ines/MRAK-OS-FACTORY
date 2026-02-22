import pytest
from db import (
    create_workflow, get_workflow, list_workflows, update_workflow, delete_workflow,
    create_workflow_node, get_workflow_nodes, update_workflow_node, delete_workflow_node,
    create_workflow_edge, get_workflow_edges, delete_workflow_edge
)

pytestmark = pytest.mark.asyncio

async def test_create_workflow(db_connection):
    name = "Test WF"
    desc = "Description"
    wf_id = await create_workflow(name, desc, is_default=False, conn=db_connection)

    wf = await get_workflow(wf_id, conn=db_connection)
    assert wf is not None
    assert wf["name"] == name
    assert wf["description"] == desc
    assert wf["is_default"] is False

async def test_list_workflows(db_connection):
    await create_workflow("WF1", "", False, conn=db_connection)
    await create_workflow("WF2", "", True, conn=db_connection)

    workflows = await list_workflows(conn=db_connection)
    names = [w["name"] for w in workflows]
    assert "WF1" in names
    assert "WF2" in names

async def test_update_workflow(db_connection):
    wf_id = await create_workflow("Old", "Old desc", False, conn=db_connection)
    await update_workflow(wf_id, name="New", description="New desc", is_default=True, conn=db_connection)

    updated = await get_workflow(wf_id, conn=db_connection)
    assert updated["name"] == "New"
    assert updated["description"] == "New desc"
    assert updated["is_default"] is True

async def test_delete_workflow(db_connection):
    wf_id = await create_workflow("ToDelete", "", False, conn=db_connection)
    await delete_workflow(wf_id, conn=db_connection)
    wf = await get_workflow(wf_id, conn=db_connection)
    assert wf is None

async def test_create_workflow_node(db_connection):
    wf_id = await create_workflow("Test WF", "", False, conn=db_connection)
    node_id = "node1"
    prompt_key = "02_IDEA_CLARIFIER"
    config = {"temp": 0.7}
    pos_x, pos_y = 100.0, 200.0

    record_id = await create_workflow_node(wf_id, node_id, prompt_key, config, pos_x, pos_y, conn=db_connection)

    nodes = await get_workflow_nodes(wf_id, conn=db_connection)
    assert len(nodes) == 1
    node = nodes[0]
    assert node["node_id"] == node_id
    assert node["prompt_key"] == prompt_key
    assert node["config"] == config
    assert node["position_x"] == pos_x
    assert node["position_y"] == pos_y
    assert node["id"] == record_id

async def test_update_workflow_node(db_connection):
    wf_id = await create_workflow("Test WF", "", False, conn=db_connection)
    record_id = await create_workflow_node(wf_id, "node1", "02_IDEA_CLARIFIER", {}, 0, 0, conn=db_connection)

    await update_workflow_node(record_id, prompt_key="03_PRODUCT_COUNCIL", config={"key": "val"}, position_x=10, position_y=20, conn=db_connection)

    nodes = await get_workflow_nodes(wf_id, conn=db_connection)
    node = nodes[0]
    assert node["prompt_key"] == "03_PRODUCT_COUNCIL"
    assert node["config"] == {"key": "val"}
    assert node["position_x"] == 10
    assert node["position_y"] == 20

async def test_delete_workflow_node(db_connection):
    wf_id = await create_workflow("Test WF", "", False, conn=db_connection)
    record_id = await create_workflow_node(wf_id, "node1", "02_IDEA_CLARIFIER", {}, 0, 0, conn=db_connection)
    await delete_workflow_node(record_id, conn=db_connection)

    nodes = await get_workflow_nodes(wf_id, conn=db_connection)
    assert len(nodes) == 0

async def test_create_workflow_edge(db_connection):
    wf_id = await create_workflow("Test WF", "", False, conn=db_connection)
    await create_workflow_node(wf_id, "node1", "02_IDEA_CLARIFIER", {}, 0, 0, conn=db_connection)
    await create_workflow_node(wf_id, "node2", "03_PRODUCT_COUNCIL", {}, 100, 0, conn=db_connection)

    edge_id = await create_workflow_edge(wf_id, "node1", "node2", "output", "input", conn=db_connection)

    edges = await get_workflow_edges(wf_id, conn=db_connection)
    assert len(edges) == 1
    edge = edges[0]
    assert edge["source_node"] == "node1"
    assert edge["target_node"] == "node2"
    assert edge["source_output"] == "output"
    assert edge["target_input"] == "input"

async def test_delete_workflow_edge(db_connection):
    wf_id = await create_workflow("Test WF", "", False, conn=db_connection)
    await create_workflow_node(wf_id, "node1", "02_IDEA_CLARIFIER", {}, 0, 0, conn=db_connection)
    await create_workflow_node(wf_id, "node2", "03_PRODUCT_COUNCIL", {}, 100, 0, conn=db_connection)
    edge_id = await create_workflow_edge(wf_id, "node1", "node2", conn=db_connection)

    await delete_workflow_edge(edge_id, conn=db_connection)

    edges = await get_workflow_edges(wf_id, conn=db_connection)
    assert len(edges) == 0