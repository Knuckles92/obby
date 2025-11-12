"""
Go Service Launcher

Automatically launches Go microservices when enabled via feature flags.
"""

import subprocess
import logging
import os
import time
import socket
from pathlib import Path
from typing import Optional, List
import signal
import sys

logger = logging.getLogger(__name__)


class GoServiceLauncher:
    """Manages launching and stopping Go microservices."""
    
    def __init__(self):
        self.processes: List[subprocess.Popen] = []
        self.project_root = Path(__file__).parent.parent
        
    def _check_port_available(self, port: int) -> bool:
        """Check if a port is available (not in use)."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.settimeout(1)
                result = s.connect_ex(('localhost', port))
                return result != 0  # Port is available if connection fails
        except Exception:
            return False
    
    def _wait_for_service(self, port: int, timeout: int = 10) -> bool:
        """Wait for a service to become available on a port."""
        start_time = time.time()
        while time.time() - start_time < timeout:
            try:
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    s.settimeout(0.5)
                    if s.connect_ex(('localhost', port)) == 0:
                        return True
            except Exception:
                pass
            time.sleep(0.2)
        return False
    
    def _check_go_available(self) -> bool:
        """Check if Go is installed and available."""
        try:
            result = subprocess.run(
                ["go", "version"],
                capture_output=True,
                timeout=2
            )
            return result.returncode == 0
        except (FileNotFoundError, subprocess.TimeoutExpired):
            return False
    
    def _find_go_binary(self, service_name: str) -> Optional[Path]:
        """Find the Go binary for a service (built or source)."""
        # Check for built binary first
        service_dir = self.project_root / "go-services" / service_name
        binary_path = service_dir / "server.exe" if sys.platform == 'win32' else service_dir / "server"
        
        if binary_path.exists():
            return binary_path
        
        # If no binary, check if Go is available and source exists
        if not self._check_go_available():
            logger.warning(f"Go is not installed - cannot launch {service_name} service")
            return None
        
        # If no binary, we'll use `go run` instead
        main_path = service_dir / "cmd" / "server" / "main.go"
        if main_path.exists():
            return main_path
        
        return None
    
    def launch_file_watcher(self, host: str = "localhost", port: int = 50051) -> Optional[subprocess.Popen]:
        """Launch the Go File Watcher service."""
        try:
            # Check if already running
            if not self._check_port_available(port):
                logger.info(f"File Watcher service already running on port {port}")
                return None
            
            binary = self._find_go_binary("file-watcher")
            if not binary:
                logger.warning("File Watcher service not found - skipping launch")
                return None
            
            # Set up environment
            env = os.environ.copy()
            env["WATCHER_PORT"] = str(port)
            env["LOG_LEVEL"] = "info"
            
            # Launch service
            if binary.suffix == '.go':
                # Use `go run` for source files
                cmd = ["go", "run", str(binary)]
                cwd = binary.parent.parent.parent
            else:
                # Use built binary
                cmd = [str(binary)]
                cwd = binary.parent
            
            logger.info(f"Launching File Watcher service on {host}:{port}...")
            process = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )
            
            self.processes.append(process)
            
            # Wait for service to start
            if self._wait_for_service(port, timeout=5):
                logger.info(f"File Watcher service started successfully on port {port}")
                return process
            else:
                logger.warning(f"File Watcher service may not have started properly (port {port} not responding)")
                # Don't kill it - it might still be starting
                return process
                
        except Exception as e:
            logger.error(f"Failed to launch File Watcher service: {e}")
            return None
    
    def launch_content_tracker(self, host: str = "localhost", port: int = 50052, db_path: str = "obby.db") -> Optional[subprocess.Popen]:
        """Launch the Go Content Tracker service."""
        try:
            # Check if already running
            if not self._check_port_available(port):
                logger.info(f"Content Tracker service already running on port {port}")
                return None

            binary = self._find_go_binary("content-tracker")
            if not binary:
                logger.warning("Content Tracker service not found - skipping launch")
                return None

            # Set up environment
            env = os.environ.copy()
            env["TRACKER_PORT"] = str(port)
            env["DB_PATH"] = str(self.project_root / db_path)

            # Launch service
            if binary.suffix == '.go':
                # Use `go run` for source files
                cmd = ["go", "run", str(binary)]
                cwd = binary.parent.parent.parent
            else:
                # Use built binary
                cmd = [str(binary)]
                cwd = binary.parent

            logger.info(f"Launching Content Tracker service on {host}:{port}...")
            process = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )

            self.processes.append(process)

            # Wait for service to start
            if self._wait_for_service(port, timeout=5):
                logger.info(f"Content Tracker service started successfully on port {port}")
                return process
            else:
                logger.warning(f"Content Tracker service may not have started properly (port {port} not responding)")
                return process

        except Exception as e:
            logger.error(f"Failed to launch Content Tracker service: {e}")
            return None

    def launch_query_service(self, host: str = "localhost", port: int = 50053, db_path: str = "obby.db") -> Optional[subprocess.Popen]:
        """Launch the Go Query Service."""
        try:
            # Check if already running
            if not self._check_port_available(port):
                logger.info(f"Query Service already running on port {port}")
                return None

            binary = self._find_go_binary("query-service")
            if not binary:
                logger.warning("Query Service not found - skipping launch")
                return None

            # Set up command with flags
            if binary.suffix == '.go':
                # Use `go run` for source files
                cmd = ["go", "run", str(binary), "--port", str(port), "--db", str(self.project_root / db_path)]
                cwd = binary.parent.parent.parent
            else:
                # Use built binary
                cmd = [str(binary), "--port", str(port), "--db", str(self.project_root / db_path)]
                cwd = binary.parent

            logger.info(f"Launching Query Service on {host}:{port}...")
            process = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )

            self.processes.append(process)

            # Wait for service to start
            if self._wait_for_service(port, timeout=5):
                logger.info(f"Query Service started successfully on port {port}")
                return process
            else:
                logger.warning(f"Query Service may not have started properly (port {port} not responding)")
                return process

        except Exception as e:
            logger.error(f"Failed to launch Query Service: {e}")
            return None

    def launch_sse_hub(self, grpc_host: str = "localhost", grpc_port: int = 50054,
                       http_host: str = "localhost", http_port: int = 8080) -> Optional[subprocess.Popen]:
        """Launch the Go SSE Hub service."""
        try:
            # Check if already running (check both gRPC and HTTP ports)
            if not self._check_port_available(grpc_port):
                logger.info(f"SSE Hub service already running on gRPC port {grpc_port}")
                return None
            if not self._check_port_available(http_port):
                logger.info(f"SSE Hub service already running on HTTP port {http_port}")
                return None

            binary = self._find_go_binary("sse-hub")
            if not binary:
                logger.warning("SSE Hub service not found - skipping launch")
                return None

            # Set up command with flags
            if binary.suffix == '.go':
                # Use `go run` for source files
                cmd = ["go", "run", str(binary), "--grpc-port", str(grpc_port), "--http-port", str(http_port)]
                cwd = binary.parent.parent.parent
            else:
                # Use built binary
                cmd = [str(binary), "--grpc-port", str(grpc_port), "--http-port", str(http_port)]
                cwd = binary.parent

            logger.info(f"Launching SSE Hub service on gRPC:{grpc_host}:{grpc_port}, HTTP:{http_host}:{http_port}...")
            process = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                creationflags=subprocess.CREATE_NEW_PROCESS_GROUP if sys.platform == 'win32' else 0
            )

            self.processes.append(process)

            # Wait for both services to start (check gRPC port)
            if self._wait_for_service(grpc_port, timeout=5):
                logger.info(f"SSE Hub service started successfully on gRPC port {grpc_port}, HTTP port {http_port}")
                return process
            else:
                logger.warning(f"SSE Hub service may not have started properly (port {grpc_port} not responding)")
                return process

        except Exception as e:
            logger.error(f"Failed to launch SSE Hub service: {e}")
            return None
    
    def stop_all(self):
        """Stop all launched services."""
        for process in self.processes:
            try:
                if process.poll() is None:  # Still running
                    logger.info(f"Stopping Go service (PID: {process.pid})...")
                    if sys.platform == 'win32':
                        # Windows: Use taskkill or terminate
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    else:
                        # Unix: Send SIGTERM
                        process.send_signal(signal.SIGTERM)
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                    logger.info(f"Go service stopped (PID: {process.pid})")
            except Exception as e:
                logger.error(f"Error stopping Go service: {e}")
        
        self.processes.clear()
    
    def launch_enabled_services(self):
        """Launch all enabled Go services based on feature flags."""
        from config.settings import (
            USE_GO_FILE_WATCHER, GO_FILE_WATCHER_HOST, GO_FILE_WATCHER_PORT,
            USE_GO_CONTENT_TRACKER, GO_CONTENT_TRACKER_HOST, GO_CONTENT_TRACKER_PORT,
            USE_GO_QUERY_SERVICE, GO_QUERY_SERVICE_HOST, GO_QUERY_SERVICE_PORT,
            USE_GO_SSE_HUB, GO_SSE_HUB_GRPC_HOST, GO_SSE_HUB_GRPC_PORT,
            GO_SSE_HUB_HTTP_HOST, GO_SSE_HUB_HTTP_PORT,
            EMERGENCY_ROLLBACK_TO_PYTHON
        )

        if EMERGENCY_ROLLBACK_TO_PYTHON:
            logger.warning("EMERGENCY ROLLBACK activated - Go services will not be launched")
            return

        logger.info("Launching enabled Go services...")

        if USE_GO_FILE_WATCHER:
            self.launch_file_watcher(GO_FILE_WATCHER_HOST, GO_FILE_WATCHER_PORT)

        if USE_GO_CONTENT_TRACKER:
            self.launch_content_tracker(GO_CONTENT_TRACKER_HOST, GO_CONTENT_TRACKER_PORT)

        if USE_GO_QUERY_SERVICE:
            self.launch_query_service(GO_QUERY_SERVICE_HOST, GO_QUERY_SERVICE_PORT)

        if USE_GO_SSE_HUB:
            self.launch_sse_hub(
                GO_SSE_HUB_GRPC_HOST, GO_SSE_HUB_GRPC_PORT,
                GO_SSE_HUB_HTTP_HOST, GO_SSE_HUB_HTTP_PORT
            )

        logger.info("Go service startup complete")


# Global launcher instance
_launcher: Optional[GoServiceLauncher] = None


def get_launcher() -> GoServiceLauncher:
    """Get or create the global service launcher."""
    global _launcher
    if _launcher is None:
        _launcher = GoServiceLauncher()
    return _launcher


def launch_go_services():
    """Launch enabled Go services."""
    launcher = get_launcher()
    launcher.launch_enabled_services()


def stop_go_services():
    """Stop all Go services."""
    global _launcher
    if _launcher:
        _launcher.stop_all()
        _launcher = None

