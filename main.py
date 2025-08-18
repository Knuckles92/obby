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
    print("Obby - Note Change Tracker")
    print("=" * 40)
    print("\nFor the web interface (recommended):")
    print("1. Start backend: python backend.py")
    print("2. Start frontend: cd frontend && npm run dev")
    print("3. Open: http://localhost:8001 (backend with built frontend)")
    print("   Or: http://localhost:5173 (development frontend)")
    print("\nSee CLAUDE.md for detailed setup instructions")

if __name__ == "__main__":
    main()