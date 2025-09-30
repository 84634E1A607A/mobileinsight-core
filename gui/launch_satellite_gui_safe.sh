#!/bin/bash

# Safe launcher for MobileInsight Satellite GUI
# Automatically handles common graphics issues

echo "🛰️  MobileInsight Satellite GUI Launcher"
echo "========================================"

# Function to test Qt platform
test_qt_platform() {
    local platform=$1
    echo "Testing Qt platform: $platform"
    
    QT_QPA_PLATFORM=$platform python3 -c "
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QLoggingCategory
QLoggingCategory.setFilterRules('*=false')
app = QApplication(sys.argv)
app.quit()
print('✓ $platform works')
" 2>/dev/null
    
    return $?
}

# Activate conda environment
echo "📦 Activating mobileinsight environment..."
source ~/miniconda3/etc/profile.d/conda.sh
conda activate mobileinsight

if [[ "$CONDA_DEFAULT_ENV" != "mobileinsight" ]]; then
    echo "❌ Failed to activate mobileinsight environment"
    exit 1
fi

echo "✅ Environment activated successfully"

# Change to GUI directory
cd "$(dirname "$0")"

# Determine best Qt platform
QT_PLATFORM=""

if [[ -n "$SSH_CLIENT" ]] || [[ -n "$SSH_CONNECTION" ]]; then
    echo "🔍 SSH session detected, using offscreen rendering"
    QT_PLATFORM="offscreen"
elif test_qt_platform "xcb"; then
    echo "🔍 Using X11 backend"
    QT_PLATFORM="xcb"
elif test_qt_platform "wayland"; then
    echo "🔍 Using Wayland backend"
    QT_PLATFORM="wayland"
else
    echo "🔍 Using offscreen rendering (fallback)"
    QT_PLATFORM="offscreen"
fi

# Set environment variables for graphics compatibility
export QT_QPA_PLATFORM=$QT_PLATFORM
export QTWEBENGINE_DISABLE_SANDBOX=1
export QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --disable-software-rasterizer"

# Additional graphics environment variables
export MESA_GL_VERSION_OVERRIDE=3.3
export MESA_GLSL_VERSION_OVERRIDE=330

echo "🚀 Starting Satellite GUI..."
echo "   Platform: $QT_PLATFORM"

# Run the GUI
python3 mobile_insight_gui.py

echo "👋 Satellite GUI closed"
