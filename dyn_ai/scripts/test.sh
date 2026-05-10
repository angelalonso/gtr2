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
    echo "${SCRIPT_NAME} - Test runner for Dyn AI"
    echo ""
    echo "USAGE:"
    echo "    ./${SCRIPT_NAME} [OPTIONS]"
    echo "    ./${SCRIPT_NAME} -h|--help"
    echo ""
    echo "DESCRIPTION:"
    echo "    This script runs the test suite for Dyn AI."
    echo ""
    echo "OPTIONS:"
    echo "    -h, --help       Show this help message and exit"
    echo "    --formula        Run only formula tests"
    echo "    --unit           Run only unit tests"
    echo "    --plr            Run only PLR tests"
    echo "    --outlier        Run only outlier detection tests"
    echo "    --resource       Run only resource path tests"
    echo "    --pyinstaller    Run only PyInstaller compatibility tests"
    echo "    --datamanager    Run only data manager tests"
    echo "    --dialog         Run only GUI dialog tests"
    echo ""
    echo "EXAMPLES:"
    echo "    # Run all tests"
    echo "    ./${SCRIPT_NAME}"
    echo ""
    echo "    # Run only formula tests"
    echo "    ./${SCRIPT_NAME} --formula"
    echo ""
    echo "EXIT CODES:"
    echo "    0   - Success"
    echo "    1   - General error"
    echo "    2   - Test failed"
    echo ""
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
TEST_MODE=""

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
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
        *)
            print_error "Unknown option: $1"
            echo "Try '$SCRIPT_NAME --help' for more information."
            exit 1
            ;;
    esac
done

# Navigate to the parent directory (project root where tests/ is located)
cd "${SCRIPT_DIR}/.."
print_info "Working directory: $(pwd)"

# Run tests based on mode
print_step "Running tests..."

# Check if test_run_all.py exists
TEST_RUNNER="tests/test_run_all.py"
if [ ! -f "$TEST_RUNNER" ]; then
    print_error "Test runner not found: $TEST_RUNNER"
    exit 1
fi

# Run tests with the appropriate mode
case $TEST_MODE in
    formula)
        print_info "Running formula tests..."
        pipenv run python3 "$TEST_RUNNER" --formula || {
            print_error "Formula tests failed!"
            exit 2
        }
        ;;
    unit)
        print_info "Running unit tests..."
        pipenv run python3 "$TEST_RUNNER" --unit || {
            print_error "Unit tests failed!"
            exit 2
        }
        ;;
    plr)
        print_info "Running PLR tests..."
        pipenv run python3 "$TEST_RUNNER" --plr || {
            print_error "PLR tests failed!"
            exit 2
        }
        ;;
    outlier)
        print_info "Running outlier detection tests..."
        pipenv run python3 "$TEST_RUNNER" --outlier || {
            print_error "Outlier detection tests failed!"
            exit 2
        }
        ;;
    resource)
        print_info "Running resource path tests..."
        pipenv run python3 "$TEST_RUNNER" --resource || {
            print_error "Resource path tests failed!"
            exit 2
        }
        ;;
    pyinstaller)
        print_info "Running PyInstaller compatibility tests..."
        pipenv run python3 "$TEST_RUNNER" --pyinstaller || {
            print_error "PyInstaller compatibility tests failed!"
            exit 2
        }
        ;;
    datamanager)
        print_info "Running data manager tests..."
        pipenv run python3 "$TEST_RUNNER" --datamanager || {
            print_error "Data manager tests failed!"
            exit 2
        }
        ;;
    dialog)
        print_info "Running GUI dialog tests..."
        pipenv run python3 "$TEST_RUNNER" --dialogs || {
            print_error "GUI dialog tests failed!"
            exit 2
        }
        ;;
    "")
        print_info "Running all tests..."
        pipenv run python3 "$TEST_RUNNER" --all || {
            print_error "Tests failed!"
            exit 2
        }
        ;;
esac

print_info "All tests passed successfully!"
exit 0
