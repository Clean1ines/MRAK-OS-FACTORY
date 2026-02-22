# CHANGED: Now a facade re-exporting from repositories
from repositories.project_repository import (
    get_projects, create_project, get_project, delete_project
)
from repositories.artifact_repository import (
    get_artifacts, get_last_artifact, get_last_validated_artifact,
    get_last_package, get_last_version_by_parent_and_type, save_artifact,
    update_artifact_status, delete_artifact, get_artifact
)
from repositories.session_repository import (
    create_clarification_session, get_clarification_session,
    update_clarification_session, add_message_to_session,
    list_active_sessions_for_project
)
from repositories.workflow_repository import (
    create_workflow, get_workflow, list_workflows, update_workflow, delete_workflow,
    create_workflow_node, get_workflow_nodes, update_workflow_node, delete_workflow_node,
    create_workflow_edge, get_workflow_edges, delete_workflow_edge
)
from repositories.artifact_type_repository import (
    get_artifact_types, get_artifact_type, create_artifact_type,
    update_artifact_type, delete_artifact_type
)

# Keep get_connection for backward compatibility, though it's now in base
from repositories.base import get_connection

# Optionally re-export all above functions (already done)
