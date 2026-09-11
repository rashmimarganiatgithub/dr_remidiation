#!/bin/bash
# unflatten_from_email.sh

# Target directory (defaults to 'email_safe_export' if no argument is provided)
TARGET_DIR=${1:-"email_safe_export"}

echo "=========================================="
echo " Starting Un-Flattening Process"
echo "=========================================="

if [ ! -d "$TARGET_DIR" ]; then
    echo "Error: Directory '$TARGET_DIR' not found."
    echo "Please unzip the package first or provide the correct folder name."
    exit 1
fi

echo "Scanning '$TARGET_DIR' for obfuscated Python files..."

# Find all files ending in .py.txt and remove the .txt extension
find "$TARGET_DIR" -type f -name "*.py.txt" -exec bash -c 'mv "$0" "${0%.txt}"' {} \;

echo "=========================================="
echo "SUCCESS!"
echo "=========================================="