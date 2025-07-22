# Obby - Note Change Tracker Web Application
"""
Main entry point for Obby web application.
This application provides real-time monitoring of markdown files with AI-powered summarization.

For web mode (recommended):
    python api_server.py

For legacy CLI mode:
    python legacy/main_cli.py
"""

# Re-export core components for programmatic use
from core.monitor import ObbyMonitor

def main():
    """Main entry point - directs users to the appropriate mode"""
    print("🔍 Obby - Note Change Tracker")
    print("=" * 40)
    print("\n💡 For the web interface (recommended):")
    print("cd frontend")
    print("npm run dev")
    print("   python api_server.py")
    print("   Then open: http://localhost:3001")
    print("\n See README.md for detailed setup instructions")

if __name__ == "__main__":
    main()