#!/usr/bin/env bash

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd scripts && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    printf "${BLUE}%s${NC}\n" "${SCRIPT_NAME} - Complete build and packaging script for Dyn AI"
    printf "\n"
    printf "${YELLOW}USAGE:${NC}\n"
    printf "    ./${SCRIPT_NAME} [OPTIONS] [VERSION]\n"
    printf "    ./${SCRIPT_NAME} -h|--help\n"
    printf "    ./${SCRIPT_NAME} vX.Y.Z\n"
    printf "\n"
    printf "${YELLOW}DESCRIPTION:${NC}\n"
    printf "    This script runs the complete build pipeline:\n"
    printf "    1. test.sh     - Run tests\n"
    printf "    2. cross_compile.sh - Build main executable\n"
    printf "    3. cross_compile_datamgmt.sh - Build data management executable\n"
    printf "    4. pack.sh     - Package everything\n"
    printf "    \n"
    printf "    If a version parameter is provided, it will be passed to pack.sh\n"
    printf "    for versioned packaging.\n"
    printf "\n"
    printf "${YELLOW}OPTIONS:${NC}\n"
    printf "    -h, --help          Show this help message and exit\n"
    printf "    -s, --skip-tests    Skip the test phase\n"
    printf "    -v, --verbose       Enable verbose output (set -x)\n"
    printf "\n"
    printf "${YELLOW}VERSION PARAMETER:${NC}\n"
    printf "    If a version parameter matching the pattern ${GREEN}vX.Y.Z${NC} (where X, Y, Z are digits) \n"
    printf "    is provided, it will be passed to pack.sh for versioned packaging.\n"
    printf "    \n"
    printf "    Examples:\n"
    printf "        ${GREEN}v1.2.3${NC}      - Version 1.2.3\n"
    printf "        ${GREEN}v0.1.0${NC}      - Version 0.1.0\n"
    printf "        ${GREEN}v10.99.5${NC}    - Version 10.99.5\n"
    printf "\n"
    printf "${YELLOW}EXAMPLES:${NC}\n"
    printf "    # Full build and package\n"
    printf "    ./${SCRIPT_NAME}\n"
    printf "    \n"
    printf "    # Build and package with version\n"
    printf "    ./${SCRIPT_NAME} v1.2.3\n"
    printf "    \n"
    printf "    # Skip tests, build and package\n"
    printf "    ./${SCRIPT_NAME} --skip-tests\n"
    printf "    \n"
    printf "    # Skip tests with version\n"
    printf "    ./${SCRIPT_NAME} -s v2.0.0\n"
    printf "\n"
    printf "${YELLOW}EXIT CODES:${NC}\n"
    printf "    0   - Success\n"
    printf "    1   - General error\n"
    printf "    2   - Test failed\n"
    printf "    3   - Cross-compile failed\n"
    printf "    4   - Data management build failed\n"
    printf "    5   - Packaging failed\n"
}

# Function to validate version format
validate_version() {
    [[ "$1" =~ ^v[0-9]+\.[0-9]+\.[0-9]+$ ]]
}

# Function to print colored messages
print_info() {
    echo -e "${GREEN}[INFO]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

print_step() {
    echo -e "${BLUE}[STEP]${NC} $1"
}

# Parse command line arguments
SKIP_TESTS=false
VERBOSE=false
VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--skip-tests)
            SKIP_TESTS=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            set -x
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            echo "Try '$SCRIPT_NAME --help' for more information."
            exit 1
            ;;
        *)
            # Check if it matches version pattern
            if validate_version "$1"; then
                VERSION="$1"
                print_info "Version detected: $VERSION"
                shift
            else
                print_error "Invalid parameter: $1"
                echo "Expected: --help, --skip-tests, --verbose, or version pattern vX.Y.Z"
                echo "Try '$SCRIPT_NAME --help' for more information."
                exit 1
            fi
            ;;
    esac
done

# Navigate to scripts directory
cd "${SCRIPT_DIR}"
print_info "Working directory: $(pwd)"

# Run test.sh
if [ "$SKIP_TESTS" = false ]; then
    print_step "Running tests..."
    if [ -f "./test.sh" ]; then
        ./test.sh || {
            print_error "Tests failed!"
            exit 2
        }
        print_info "Tests passed"
    else
        print_error "test.sh not found!"
        exit 1
    fi
else
    print_info "Skipping tests (--skip-tests)"
fi

# Run cross_compile.sh
print_step "Building main executable..."
if [ -f "./cross_compile.sh" ]; then
    ./cross_compile.sh || {
        print_error "Cross-compile failed!"
        exit 3
    }
    print_info "Main executable built successfully"
else
    print_error "cross_compile.sh not found!"
    exit 1
fi

# Run cross_compile_datamgmt.sh
print_step "Building data management executable..."
if [ -f "./cross_compile_datamgmt.sh" ]; then
    ./cross_compile_datamgmt.sh || {
        print_error "Data management build failed!"
        exit 4
    }
    print_info "Data management executable built successfully"
else
    print_error "cross_compile_datamgmt.sh not found!"
    exit 1
fi

# Run pack.sh with version if provided
print_step "Packaging..."
if [ -f "./pack.sh" ]; then
    if [ -n "$VERSION" ]; then
        print_info "Passing version $VERSION to pack.sh"
        ./pack.sh "$VERSION" || {
            print_error "Packaging failed!"
            exit 5
        }
    else
        ./pack.sh || {
            print_error "Packaging failed!"
            exit 5
        }
    fi
    print_info "Packaging completed successfully"
else
    print_error "pack.sh not found!"
    exit 1
fi

print_info "=== Build pipeline completed successfully ==="
exit 0
