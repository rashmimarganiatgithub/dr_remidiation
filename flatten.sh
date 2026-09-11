#!/bin/bash
# flatten_for_email.sh

# Define the new safe directory name
EXPORT_DIR="email_safe_export"

echo "=========================================="
echo " Starting Flattening Process for Email"
echo "=========================================="

# 1. Ensure a clean slate for the export directory
if [ -d "$EXPORT_DIR" ]; then
    echo "Cleaning up old export directory..."
    rm -rf "$EXPORT_DIR"
fi
mkdir -p "$EXPORT_DIR"

# 2. Copy the relevant directories into the safe folder
echo "Copying repository contents to ./$EXPORT_DIR ..."
# Copy the main validator directory
cp -r gcp-dag-precommit-validator "$EXPORT_DIR/"
# Copy the secure validator directory if it exists
cp -r gcp-dag-precommit-validator-secure "$EXPORT_DIR/" 2>/dev/null
# Copy example usage
cp -r example-usage "$EXPORT_DIR/" 2>/dev/null
# Copy loose markdown files
cp local.md steps.md "$EXPORT_DIR/" 2>/dev/null

# 3. Find all .py files IN THE NEW FOLDER ONLY and append .txt
echo "Obfuscating Python files to bypass email filters..."
find "$EXPORT_DIR" -type f -name "*.py" -exec bash -c 'mv "$0" "${0}.txt"' {} \;


echo "=========================================="
echo "SUCCESS!"
echo "Your original code is untouched."
echo "=========================================="