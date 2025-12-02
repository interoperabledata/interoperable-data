from pathlib import Path

# This file lives in: <project_root>/runner/paths.py
# So parent -> <project_root>
WORKFLOW_ROOT = Path(__file__).resolve().parent.parent  # <project_root>

# Functions and schemas are direct children of the project root
FUNCTIONS_ROOT = WORKFLOW_ROOT / "functions"            # <project_root>/functions
SCHEMAS_ROOT = WORKFLOW_ROOT / "schemas"                # <project_root>/schemas

# Workflow and core requirements also sit at the project root
WORKFLOW_FILE = WORKFLOW_ROOT / "workflow.id"           # <project_root>/workflow.id
CORE_REQUIREMENTS = WORKFLOW_ROOT / "requirements.txt"  # <project_root>/requirements.txt
