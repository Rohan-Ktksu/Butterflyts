
# Step 19.4 - Run complete aircraft processing pipeline

from pathlib import Path
import subprocess
import sys

# Locate the trajectories directory
SCRIPT_DIR = Path(__file__).resolve().parent

# Define pipeline scripts
pipeline_scripts = [
    "process_all_sessions.py",
    "build_classification_history.py",
    "validate_classification_history.py"
]

# Run each pipeline stage in order
for script_name in pipeline_scripts:

    script_path = SCRIPT_DIR / script_name

    if not script_path.exists():
        print("Missing pipeline script:", script_path)
        raise SystemExit(1)

    print()
    print("Running:", script_name, flush=True)

    result = subprocess.run(
        [sys.executable, str(script_path)],
        check=False
    )

    if result.returncode != 0:
        print("Pipeline failed at:", script_name)
        raise SystemExit(result.returncode)

# Display completion message
print()
print("BUTTERFLYTS PIPELINE COMPLETED SUCCESSFULLY")
