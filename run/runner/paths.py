from pathlib import Path

# The workflow root is the 'run' directory
WORKFLOW_ROOT = Path(__file__).resolve().parent.parent
DATA_FUNCTIONS_ROOT = WORKFLOW_ROOT.parent / "data_functions"
SCHEMAS_ROOT = WORKFLOW_ROOT / "schemas"
WORKFLOW_FILE = WORKFLOW_ROOT / "workflow.id"
CORE_REQUIREMENTS = WORKFLOW_ROOT / "requirements.txt"
