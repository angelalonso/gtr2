#!/usr/bin/env bash

set -e

# Get the script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPT_NAME="$(basename "${BASH_SOURCE[0]}")"

TESTS_DIR="$(cd ../tests && pwd)"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to display help
show_help() {
    cat << EOF
${SCRIPT_NAME} - Run Dyn AI tests

USAGE:
    ./${SCRIPT_NAME} [OPTIONS]

OPTIONS:
    -h, --help          Show this help message
    -s, --skip-race     Skip the race simulation test

EXIT CODES:
    0   - All tests passed
    1   - General error
    2   - test_run_all.py failed
    3   - test_races_simulation.py failed

EOF
}

# Function to print colored output
print_success() {
    echo -e "${GREEN}✓${NC} $1"
}

print_error() {
    echo -e "${RED}✗${NC} $1"
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

print_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

# Parse arguments
SKIP_RACE=false

while [[ $# -gt 0 ]]; do
    case $1 in
        -h|--help)
            show_help
            exit 0
            ;;
        -s|--skip-race)
            SKIP_RACE=true
            shift
            ;;
        *)
            print_error "Unknown option: $1"
            echo "Try '$SCRIPT_NAME --help' for more information."
            exit 1
            ;;
    esac
done

# Navigate to project root
cd "${SCRIPT_DIR}/.."
PROJECT_ROOT="$(pwd)"
print_info "Project root: $PROJECT_ROOT"

cd "${TESTS_DIR}"

# Check if pipenv is available
if ! command -v pipenv &> /dev/null; then
    print_error "pipenv is not installed or not in PATH"
    echo "Please install pipenv: pip install pipenv"
    exit 1
fi

# Run test_run_all.py (preserve interactivity)
echo ""
print_header "Running: Main Test Suite (test_run_all.py)"
echo ""

pipenv run python3 test_run_all.py
TEST1_RESULT=$?

if [ $TEST1_RESULT -ne 0 ]; then
    echo ""
    print_error "Main test suite failed with exit code: $TEST1_RESULT"
    exit 2
else
    print_success "Main test suite completed successfully"
fi

# to be corrected
## Run test_races_simulation.py (preserve interactivity)
if [ "$SKIP_RACE" = false ]; then
    echo ""
    print_header "Running: Race Simulation Test (test_races_simulation.py)"
    echo ""
    
    pipenv run python3 test_races_simulation.py
    TEST2_RESULT=$?
    
    if [ $TEST2_RESULT -ne 0 ]; then
        echo ""
        print_error "Race simulation test failed with exit code: $TEST2_RESULT"
        exit 3
    else
        print_success "Race simulation test completed successfully"
    fi
else
    print_warning "Skipping race simulation test (--skip-race)"
    TEST2_RESULT=0
fi

# Final summary
echo ""
print_header "TEST SUMMARY"
echo ""

if [ $TEST1_RESULT -eq 0 ] && [ $TEST2_RESULT -eq 0 ]; then
    print_success "All tests passed successfully!"
    echo ""
    echo "  ✓ Main test suite"
    [ "$SKIP_RACE" = false ] && echo "  ✓ Race simulation test"
    echo ""
    print_info "Ready for cross-compilation."
    exit 0
else
    print_error "Some tests failed!"
    [ $TEST1_RESULT -ne 0 ] && echo "  ✗ Main test suite failed"
    [ $TEST2_RESULT -ne 0 ] && echo "  ✗ Race simulation test failed"
    exit 1
fi
