#!/bin/bash
#
# Build Go Services for Obby
# ===========================
#
# This script builds all Go microservices and places binaries in their respective directories.
# Run this script from the project root or specify PROJECT_ROOT environment variable.
#

set -e  # Exit on error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine project root
if [ -z "$PROJECT_ROOT" ]; then
    # Script is in scripts/ directory, so project root is parent
    PROJECT_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
fi

cd "$PROJECT_ROOT"

echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Building Obby Go Services${NC}"
echo -e "${BLUE}================================${NC}"
echo ""

# Check if Go is installed
if ! command -v go &> /dev/null; then
    echo -e "${RED}Error: Go is not installed or not in PATH${NC}"
    echo "Please install Go from https://golang.org/dl/"
    exit 1
fi

GO_VERSION=$(go version)
echo -e "${GREEN}✓${NC} Go found: $GO_VERSION"
echo ""

# Services to build
declare -a services=(
    "file-watcher"
    "content-tracker"
    "query-service"
    "sse-hub"
)

# Build function
build_service() {
    local service_name=$1
    local service_dir="go-services/${service_name}"
    local main_path="${service_dir}/cmd/server/main.go"

    echo -e "${YELLOW}Building ${service_name}...${NC}"

    # Check if service directory exists
    if [ ! -d "$service_dir" ]; then
        echo -e "${RED}  ✗ Service directory not found: ${service_dir}${NC}"
        return 1
    fi

    # Check if main.go exists
    if [ ! -f "$main_path" ]; then
        echo -e "${RED}  ✗ Main file not found: ${main_path}${NC}"
        return 1
    fi

    # Build the service
    cd "$service_dir"

    # Determine binary name based on platform
    BINARY_NAME="server"
    if [[ "$OSTYPE" == "msys" || "$OSTYPE" == "win32" ]]; then
        BINARY_NAME="server.exe"
    fi

    # Build with optimization
    echo -e "  Compiling..."
    if go build -o "$BINARY_NAME" -ldflags="-s -w" "./cmd/server"; then
        echo -e "${GREEN}  ✓ Built successfully: ${service_dir}/${BINARY_NAME}${NC}"

        # Make binary executable (Unix-like systems)
        if [[ "$OSTYPE" != "msys" && "$OSTYPE" != "win32" ]]; then
            chmod +x "$BINARY_NAME"
        fi

        cd "$PROJECT_ROOT"
        return 0
    else
        echo -e "${RED}  ✗ Build failed${NC}"
        cd "$PROJECT_ROOT"
        return 1
    fi
}

# Track build results
SUCCESS_COUNT=0
FAIL_COUNT=0
declare -a FAILED_SERVICES

# Build each service
for service in "${services[@]}"; do
    if build_service "$service"; then
        ((SUCCESS_COUNT++))
    else
        ((FAIL_COUNT++))
        FAILED_SERVICES+=("$service")
    fi
    echo ""
done

# Summary
echo -e "${BLUE}================================${NC}"
echo -e "${BLUE}Build Summary${NC}"
echo -e "${BLUE}================================${NC}"
echo -e "${GREEN}Successful builds: ${SUCCESS_COUNT}${NC}"

if [ $FAIL_COUNT -gt 0 ]; then
    echo -e "${RED}Failed builds: ${FAIL_COUNT}${NC}"
    echo -e "${RED}Failed services:${NC}"
    for service in "${FAILED_SERVICES[@]}"; do
        echo -e "${RED}  - ${service}${NC}"
    done
    echo ""
    echo -e "${YELLOW}Note: You can still run the application with Python implementations.${NC}"
    echo -e "${YELLOW}Set EMERGENCY_ROLLBACK=true in .env to disable all Go services.${NC}"
    exit 1
else
    echo ""
    echo -e "${GREEN}✓ All Go services built successfully!${NC}"
    echo ""
    echo -e "Next steps:"
    echo -e "  1. Start the backend: ${BLUE}python backend.py${NC}"
    echo -e "  2. All Go services will launch automatically"
    echo -e "  3. View service status at: ${BLUE}http://localhost:8001/services${NC}"
    exit 0
fi
