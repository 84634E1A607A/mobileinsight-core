#!/bin/bash

# Satellite GUI Launcher Script
# This script activates the mobileinsight conda environment and launches the satellite GUI

echo "Launching MobileInsight Satellite GUI..."
echo "Activating mobileinsight conda environment..."

# Activate conda environment and run the GUI
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mobileinsight

# Check if activation was successful
if [[ "$CONDA_DEFAULT_ENV" == "mobileinsight" ]]; then
    echo "Successfully activated mobileinsight environment"
    echo "Starting GUI application..."
    python mobile_insight_gui.py
else
    echo "Failed to activate mobileinsight environment"
    echo "Please make sure the conda environment exists and is properly configured"
    exit 1
fi