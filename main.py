# Re-export ObbyMonitor from the core module for backward compatibility
from core.monitor import ObbyMonitor

# Import CLI functionality from legacy module
from legacy.main_cli import main

# For backward compatibility, allow running the CLI directly
if __name__ == "__main__":
    main()