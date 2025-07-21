#!/bin/bash
echo "Starting environment check..."

# Check for Python
if ! command -v python3 &> /dev/null; then
    echo " Python3 is not installed. Please install it first."
    exit 1
fi
echo " Python3 found: $(python3 --version)"

# Check for pip
if ! command -v pip3 &> /dev/null; then
    echo " pip3 is not installed. Please install pip."
    exit 1
fi
echo " pip3 found: $(pip3 --version)"

# Install required Python packages
echo "Installing required Python packages: toml, pathlib, logging..."

python3 -m pip install --user toml pathlib || {
    echo " Failed to install Python packages."
    exit 
}

echo " Python packages installed."

# Check for kubectl
if ! command -v kubectl &> /dev/null; then
    echo " kubectl is not installed. Please install kubectl to proceed."
    exit 1
fi
echo " kubectl found: $(kubectl version --client --short)"

echo " Environment prerequisites completed!"
