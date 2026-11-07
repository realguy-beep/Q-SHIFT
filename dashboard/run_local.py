"""Start the dashboard bound to loopback only from any working directory."""
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent
for entry in (str(ROOT), str(HERE)):
    if entry not in sys.path:
        sys.path.insert(0, entry)

from dashboard.app import main  # noqa: E402

if __name__ == "__main__":
    main()
