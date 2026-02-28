# ADDED: Workflow graph domain class
from typing import List, Dict, Any, Optional, Set

class WorkflowGraph:
    """Represents a workflow graph with nodes and edges."""

    def __init__(self, nodes: List[Dict[str, Any]], edges: List[Dict[str, Any]]):
        """
        :param nodes: List of node dicts, each must contain 'node_id' and other metadata.
        :param edges: List of edge dicts, each must contain 'source_node' and 'target_node'.
        """
        self.nodes = {node['node_id']: node for node in nodes}
        self.outgoing: Dict[str, List[str]] = {}
        self.incoming: Dict[str, List[str]] = {}
        for edge in edges:
            src = edge['source_node']
            tgt = edge['target_node']
            self.outgoing.setdefault(src, []).append(tgt)
            self.incoming.setdefault(tgt, []).append(src)

    def get_node(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Return node dict by ID, or None if not found."""
        return self.nodes.get(node_id)

    def get_start_nodes(self) -> List[str]:
        """Return list of node IDs that have no incoming edges."""
        all_nodes = set(self.nodes.keys())
        nodes_with_incoming = set(self.incoming.keys())
        return list(all_nodes - nodes_with_incoming)

    def get_next_node(self, current_node_id: str) -> Optional[str]:
        """
        Return the first outgoing node ID, or None if no outgoing edges.
        (Assumes linear workflow – first edge only.)
        """
        outgoing = self.outgoing.get(current_node_id, [])
        return outgoing[0] if outgoing else None

    def is_finished(self, node_id: str) -> bool:
        """Return True if node has no outgoing edges."""
        return not self.outgoing.get(node_id, [])
