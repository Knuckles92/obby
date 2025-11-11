"""gRPC clients for Go microservices."""

# Make generated modules available
import sys
from pathlib import Path

# Add generated directory to path if not already there
generated_path = Path(__file__).parent / "generated"
if str(generated_path) not in sys.path:
    sys.path.insert(0, str(generated_path))
