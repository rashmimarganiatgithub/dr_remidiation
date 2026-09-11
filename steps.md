
# Authenticate your local terminal with GCP
gcloud auth login
gcloud auth application-default login


# Install the Artifact Registry auth helper & pre-commit for pip
pip install keyrings.google-artifactregistry-auth pre-commit


# install precommit-dag-scanner package
pip install gcp-dag-precommit-validator/dist/gcp_dag_validator-2.1.6-py3-none-any.whl


pip install --index-url https://us-central1-python.pkg.dev/dmgcp-del-181/python-precommit-repo/simple/ gcp-dag-validator==2.1.6


# -----------------------------------------------------------
# Compiling to C-Extensions via Cython
# -----------------------------------------------------------

Here is the complete guide to implementing a dual-approach setup.py that supports both pure Python (for local dev) and Cython (for secure distribution).

Step 1: Prerequisites
To compile C-Extensions, the machine building the package needs a C compiler and the Cython library.

Install Build Tools:

#### Windows: Install Microsoft Visual C++ Build Tools.

#### Linux: sudo apt-get install build-essential python3-dev

#### macOS: xcode-select --install

Install Python Build Dependencies:


``` `
 pip install setuptools wheel Cython build 
``` `
 


# ---- Clean the environment ----
rm -rf build/ dist/ *.egg-info/ secure_gcp_dag_validator/core/*.c

# <!-- -------------------------------- -->
# 1. Get the absolute path to your current directory
# <!-- -------------------------------- -->

export ROOT_DIR=$(pwd)

# 2. Update the environment variables with absolute paths
export CC="$ROOT_DIR/gcc.bat"
export CXX="$ROOT_DIR/g++.bat"

# 3. These flags tell setuptools to respect the CC/CXX overrides
export DISTUTILS_USE_SDK=1
export MSSdk=1
export USE_CYTHON=1

python -m build --wheel --no-isolation

# 1. Thoroughly clean old artifacts
rm -rf build/ dist/ *.egg-info/ secure_gcp_dag_validator/core/*.c

# 2. Build the secure wheel
python -m build --wheel --no-isolation

# 3. Reinstall
pip uninstall -y secure-dag-validator
pip install dist/secure_dag_validator-2.1.7-*.whl