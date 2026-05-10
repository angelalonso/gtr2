#!/usr/bin/env bash

set -e

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    echo ""
    echo "${SCRIPT_NAME} - Complete build and packaging script for Dyn AI"
    echo ""
    echo "USAGE:"
    echo "    ./${SCRIPT_NAME} [OPTIONS] [VERSION]"
    echo "    ./${SCRIPT_NAME} -h|--help"
    echo "    ./${SCRIPT_NAME} vX.Y.Z"
    echo ""
    echo "DESCRIPTION:"
    echo "    This script runs the complete build pipeline:"
    echo "    1. test.sh     - Run tests"
    echo "    2. cross_compile.sh - Build main executable"
    echo "    3. cross_compile_datamgmt.sh - Build data management executable"
    echo "    4. pack.sh     - Package everything"
    echo ""
    echo "    If a version parameter is provided, it will be passed to pack.sh"
    echo "    for versioned packaging."
    echo ""
    echo "OPTIONS:"
    echo "    -h, --help       Show this help message and exit"
    echo "    -s, --skiptests  Skip the test phase"
    echo "    -v, --verbose    Enable verbose output (set -x)"
    echo "    --formula        Run only formula tests, then exit (no compile, no pack)"
    echo "    --unit           Run only unit tests, then exit (no compile, no pack)"
    echo "    --plr            Run only PLR tests, then exit (no compile, no pack)"
    echo "    --outlier        Run only outlier detection tests, then exit (no compile, no pack)"
    echo "    --resource       Run only resource path tests, then exit (no compile, no pack)"
    echo "    --pyinstaller    Run only PyInstaller compatibility tests, then exit (no compile, no pack)"
    echo "    --datamanager    Run only data manager tests, then exit (no compile, no pack)"
    echo "    --dialog         Run only GUI dialog tests, then exit (no compile, no pack)"
    echo ""
    echo "VERSION PARAMETER:"
    echo "    If a version parameter matching the pattern vX.Y.Z (where X, Y, Z are digits)"
    echo "    is provided, it will be passed to pack.sh for versioned packaging."
    echo ""
    echo "    Examples:"
    echo "        v1.2.3      - Version 1.2.3"
    echo "        v0.1.0      - Version 0.1.0"
    echo "        v10.99.5    - Version 10.99.5"
    echo ""
    echo "EXAMPLES:"
    echo "    # Full build and package"
    echo "    ./${SCRIPT_NAME}"
    echo ""
    echo "    # Build and package with version"
    echo "    ./${SCRIPT_NAME} v1.2.3"
    echo ""
    echo "    # Skip tests, build and package"
    echo "    ./${SCRIPT_NAME} --skiptests"
    echo ""
    echo "    # Skip tests with version"
    echo "    ./${SCRIPT_NAME} -s v2.0.0"
    echo ""
    echo "    # Run only formula tests"
    echo "    ./${SCRIPT_NAME} --formula"
    echo ""
    echo "    # Run only unit tests"
    echo "    ./${SCRIPT_NAME} --unit"
    echo ""
    echo "EXIT CODES:"
    echo "    0   - Success"
    echo "    1   - General error"
    echo "    2   - Test failed"
    echo "    3   - Cross-compile failed"
    echo "    4   - Data management build failed"
    echo "    5   - Packaging failed"
    echo ""
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
TEST_MODE=""
VERSION=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--skiptests)
            SKIP_TESTS=true
            shift
            ;;
        -v|--verbose)
            VERBOSE=true
            set -x
            shift
            ;;
        --formula)
            TEST_MODE="formula"
            shift
            ;;
        --unit)
            TEST_MODE="unit"
            shift
            ;;
        --plr)
            TEST_MODE="plr"
            shift
            ;;
        --outlier)
            TEST_MODE="outlier"
            shift
            ;;
        --resource)
            TEST_MODE="resource"
            shift
            ;;
        --pyinstaller)
            TEST_MODE="pyinstaller"
            shift
            ;;
        --datamanager)
            TEST_MODE="datamanager"
            shift
            ;;
        --dialog)
            TEST_MODE="dialog"
            shift
            ;;
        -*)
            print_error "Unknown option: $1"
            echo "Try '$SCRIPT_NAME --help' for more information."
            exit 1
            ;;
        *)
            if validate_version "$1"; then
                VERSION="$1"
                print_info "Version detected: $VERSION"
                shift
            else
                print_error "Invalid parameter: $1"
                echo "Try '$SCRIPT_NAME --help' for more information."
                exit 1
            fi
            ;;
    esac
done

# Navigate to scripts directory
cd "${SCRIPT_DIR}/scripts"
print_info "Working directory: $(pwd)"

# Run test.sh
if [ "$SKIP_TESTS" = false ]; then
    print_step "Running tests..."
    if [ -f "./test.sh" ]; then
        if [ -n "$TEST_MODE" ]; then
            print_info "Running with mode: --${TEST_MODE}"
            ./test.sh "--${TEST_MODE}" || {
                print_error "Tests failed!"
                exit 2
            }
        else
            ./test.sh || {
                print_error "Tests failed!"
                exit 2
            }
        fi
        print_info "Tests passed"
    else
        print_error "test.sh not found!"
        exit 1
    fi
else
    print_info "Skipping tests (--skiptests)"
fi

# If we're in any test-only mode, exit after tests
if [ -n "$TEST_MODE" ]; then
    print_info "Test-only mode (--${TEST_MODE}), skipping compilation and packaging"
    exit 0
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
