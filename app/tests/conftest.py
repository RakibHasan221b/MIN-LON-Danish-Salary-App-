import sys
from pathlib import Path

# Allow `import app...` when running pytest from the repo root or elsewhere.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
