
import os, sys
from pathlib import Path

# Ensure the CareLog_structured package root is on sys.path
HERE = Path(__file__).resolve()
PKG_ROOT = HERE.parent.parent  # CareLog_structured/
if str(PKG_ROOT) not in sys.path:
    sys.path.insert(0, str(PKG_ROOT))
