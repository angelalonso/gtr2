#!/bin/bash

set -e

CWD=$(pwd)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=== PyInstaller Script Validator ==="
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Get all Python files (excluding test files)
ALL_PY_FILES=$(ls *.py 2>/dev/null | grep -v "^test" | grep -v "^test_" | grep -v "_test" | grep -v "dyn_ai_data_manager" || true)

echo -e "${BLUE}Found Python files (excluding tests):${NC}"
echo "$ALL_PY_FILES" | while read f; do
    echo "  - $f"
done
echo ""

# Parse the cross_compile.sh file
CROSS_COMPILE="cross_compile.sh"
if [ ! -f "$CROSS_COMPILE" ]; then
    echo -e "${RED}Error: $CROSS_COMPILE not found${NC}"
    exit 1
fi

# Extract --add-data entries
ADD_DATA_ENTRIES=$(grep -oP -- '--add-data="\K[^"]+' "$CROSS_COMPILE" | sed 's/;.*$//' | sort -u)

# Extract --hidden-import entries
HIDDEN_IMPORTS=$(grep -oP -- '--hidden-import=\K[^ ]+' "$CROSS_COMPILE" | sort -u)

echo -e "${BLUE}Current --add-data files:${NC}"
echo "$ADD_DATA_ENTRIES" | while read f; do
    if [ -n "$f" ]; then
        echo "  - $f"
    fi
done
echo ""

echo -e "${BLUE}Current --hidden-import modules:${NC}"
echo "$HIDDEN_IMPORTS" | while read m; do
    if [ -n "$m" ]; then
        echo "  - $m"
    fi
done
echo ""

# Check for missing entries
echo -e "${YELLOW}=== Validation Results ===${NC}"
echo ""

MISSING_ADD_DATA=""
MISSING_HIDDEN_IMPORT=""
EXTRA_ADD_DATA=""
EXTRA_HIDDEN_IMPORT=""
VALID=true

# Check each Python file
for py_file in $ALL_PY_FILES; do
    module_name="${py_file%.py}"
    
    # Check --add-data
    if ! echo "$ADD_DATA_ENTRIES" | grep -q "^${py_file}$"; then
        MISSING_ADD_DATA="${MISSING_ADD_DATA}${py_file}\n"
        VALID=false
    fi
    
    # Check --hidden-import
    if ! echo "$HIDDEN_IMPORTS" | grep -q "^${module_name}$"; then
        MISSING_HIDDEN_IMPORT="${MISSING_HIDDEN_IMPORT}${module_name}\n"
        VALID=false
    fi
done

# Check for extra entries (not needed but not harmful)
for add_data in $ADD_DATA_ENTRIES; do
    if [ ! -f "$add_data" ] && [[ ! "$add_data" =~ \.(yml|json|db)$ ]] && [[ ! "$add_data" =~ pyqtgraph ]]; then
        if ! echo "$ALL_PY_FILES" | grep -q "^${add_data}$"; then
            EXTRA_ADD_DATA="${EXTRA_ADD_DATA}${add_data}\n"
        fi
    fi
done

for hidden_import in $HIDDEN_IMPORTS; do
    if [ -f "${hidden_import}.py" ] && ! echo "$ALL_PY_FILES" | grep -q "^${hidden_import}.py$"; then
        EXTRA_HIDDEN_IMPORT="${EXTRA_HIDDEN_IMPORT}${hidden_import}\n"
    fi
done

# Report results
if [ -n "$MISSING_ADD_DATA" ]; then
    echo -e "${RED}❌ Missing --add-data entries:${NC}"
    echo -e "$MISSING_ADD_DATA" | while read f; do
        if [ -n "$f" ]; then
            echo -e "  ${RED}--add-data=\"$f;.\"${NC}"
        fi
    done
    echo ""
fi

if [ -n "$MISSING_HIDDEN_IMPORT" ]; then
    echo -e "${RED}❌ Missing --hidden-import entries:${NC}"
    echo -e "$MISSING_HIDDEN_IMPORT" | while read m; do
        if [ -n "$m" ]; then
            echo -e "  ${RED}--hidden-import=$m${NC}"
        fi
    done
    echo ""
fi

if [ -n "$EXTRA_ADD_DATA" ]; then
    echo -e "${YELLOW}⚠️  Extra --add-data entries (not files, but harmless):${NC}"
    echo -e "$EXTRA_ADD_DATA" | while read f; do
        if [ -n "$f" ]; then
            echo -e "  ${YELLOW}--add-data=\"$f;.\"${NC}"
        fi
    done
    echo ""
fi

if [ -n "$EXTRA_HIDDEN_IMPORT" ]; then
    echo -e "${YELLOW}⚠️  Extra --hidden-import entries (not modules, but harmless):${NC}"
    echo -e "$EXTRA_HIDDEN_IMPORT" | while read m; do
        if [ -n "$m" ]; then
            echo -e "  ${YELLOW}--hidden-import=$m${NC}"
        fi
    done
    echo ""
fi

if [ "$VALID" = true ]; then
    echo -e "${GREEN}✅ All Python files are properly included!${NC}"
else
    echo -e "${RED}❌ Validation FAILED! Missing entries found.${NC}"
    echo ""
    echo -e "${BLUE}=== Generate Missing Entries ===${NC}"
    
    # Generate complete add-data lines
    if [ -n "$MISSING_ADD_DATA" ]; then
        echo ""
        echo -e "${BLUE}# Add these --add-data lines:${NC}"
        echo -e "$MISSING_ADD_DATA" | while read f; do
            if [ -n "$f" ]; then
                echo "    --add-data=\"$f;.\" \\"
            fi
        done
    fi
    
    # Generate complete hidden-import lines
    if [ -n "$MISSING_HIDDEN_IMPORT" ]; then
        echo ""
        echo -e "${BLUE}# Add these --hidden-import lines:${NC}"
        echo -e "$MISSING_HIDDEN_IMPORT" | while read m; do
            if [ -n "$m" ]; then
                echo "    --hidden-import=$m \\"
            fi
        done
    fi
fi

echo ""
exit 0
