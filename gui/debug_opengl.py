#!/usr/bin/env python3

"""
OpenGL Debugging Script for Satellite GUI
This script helps diagnose and fix OpenGL/graphics issues in PyQt6 applications
"""

import os
import sys
import subprocess

def check_system_graphics():
    """Check system graphics configuration and capabilities."""
    print("🔍 System Graphics Diagnosis")
    print("=" * 50)
    
    # Check if running in SSH/remote session
    display = os.environ.get('DISPLAY')
    ssh_client = os.environ.get('SSH_CLIENT')
    ssh_connection = os.environ.get('SSH_CONNECTION')
    
    print(f"DISPLAY environment: {display}")
    print(f"SSH_CLIENT: {ssh_client}")
    print(f"SSH_CONNECTION: {ssh_connection}")
    
    if ssh_client or ssh_connection:
        print("⚠️  Running in SSH session - graphics may be limited")
    
    # Check available graphics drivers
    print("\n📊 Graphics Information:")
    try:
        result = subprocess.run(['lspci', '-k'], capture_output=True, text=True)
        lines = result.stdout.split('\n')
        for line in lines:
            if 'VGA' in line or 'Display' in line or '3D' in line:
                print(f"  {line}")
    except:
        print("  Could not run lspci")
    
    # Check OpenGL support
    print("\n🎮 OpenGL Support:")
    try:
        result = subprocess.run(['glxinfo', '-B'], capture_output=True, text=True)
        if result.returncode == 0:
            lines = result.stdout.split('\n')
            for line in lines:
                if 'OpenGL' in line and ('version' in line.lower() or 'vendor' in line.lower() or 'renderer' in line.lower()):
                    print(f"  {line.strip()}")
        else:
            print("  glxinfo not available or failed")
    except:
        print("  glxinfo command not found")
    
    # Check Mesa/software rendering
    print("\n🖥️  Mesa/Software Rendering:")
    mesa_debug = os.environ.get('MESA_DEBUG')
    libgl_debug = os.environ.get('LIBGL_DEBUG')
    print(f"  MESA_DEBUG: {mesa_debug}")
    print(f"  LIBGL_DEBUG: {libgl_debug}")

def test_qt_backends():
    """Test different Qt platform backends."""
    print("\n🧪 Testing Qt Platform Backends")
    print("=" * 50)
    
    backends = [
        ('xcb', 'X11 backend (default on Linux)'),
        ('wayland', 'Wayland backend'),
        ('offscreen', 'Offscreen rendering (no display)'),
        ('minimal', 'Minimal platform (text only)'),
    ]
    
    for backend, description in backends:
        print(f"\n🔧 Testing {backend} backend ({description}):")
        
        env = os.environ.copy()
        env['QT_QPA_PLATFORM'] = backend
        
        test_code = f'''
import sys
from PyQt6.QtWidgets import QApplication
from PyQt6.QtCore import QLoggingCategory

try:
    # Suppress Qt logging for cleaner output
    QLoggingCategory.setFilterRules("*=false")
    
    app = QApplication(sys.argv)
    print(f"✓ QApplication created successfully with {backend}")
    
    # Test creating a simple widget
    from PyQt6.QtWidgets import QWidget
    widget = QWidget()
    print(f"✓ QWidget created successfully")
    
    app.quit()
    
except Exception as e:
    print(f"✗ Failed: {{e}}")
'''
        
        try:
            result = subprocess.run([
                'python3', '-c', test_code
            ], env=env, capture_output=True, text=True, timeout=10)
            
            if result.returncode == 0:
                print(result.stdout.strip())
            else:
                print(f"✗ Backend failed with return code {result.returncode}")
                if result.stderr:
                    # Show only relevant error lines
                    errors = [line for line in result.stderr.split('\n') 
                             if 'error' in line.lower() or 'failed' in line.lower()]
                    for error in errors[:3]:  # Show first 3 errors
                        print(f"   {error.strip()}")
                        
        except subprocess.TimeoutExpired:
            print("✗ Backend test timed out")
        except Exception as e:
            print(f"✗ Test failed: {e}")

def test_webengine_alternatives():
    """Test WebEngine and alternatives."""
    print("\n🌐 Testing WebEngine and Alternatives")
    print("=" * 50)
    
    # Test WebEngine availability
    test_code = '''
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    print("✓ PyQt6.QtWebEngineWidgets available")
except ImportError as e:
    print(f"✗ WebEngine not available: {e}")

try:
    from PyQt6.QtWidgets import QTextEdit
    print("✓ QTextEdit fallback available")
except ImportError as e:
    print(f"✗ QTextEdit fallback failed: {e}")
'''
    
    env = os.environ.copy()
    env['QT_QPA_PLATFORM'] = 'offscreen'  # Use safe backend
    
    try:
        result = subprocess.run([
            'python3', '-c', test_code
        ], env=env, capture_output=True, text=True, timeout=5)
        print(result.stdout.strip())
        if result.stderr:
            print("Warnings:", result.stderr.strip())
    except Exception as e:
        print(f"Test failed: {e}")

def test_matplotlib_backends():
    """Test matplotlib backends."""
    print("\n📊 Testing Matplotlib Backends")
    print("=" * 50)
    
    backends = ['Agg', 'Qt5Agg', 'TkAgg']
    
    for backend in backends:
        test_code = f'''
import matplotlib
matplotlib.use('{backend}')
import matplotlib.pyplot as plt

try:
    fig, ax = plt.subplots()
    ax.plot([1, 2, 3], [1, 4, 2])
    print(f"✓ Matplotlib {backend} backend works")
    plt.close(fig)
except Exception as e:
    print(f"✗ Matplotlib {backend} failed: {{e}}")
'''
        
        try:
            result = subprocess.run([
                'python3', '-c', test_code
            ], capture_output=True, text=True, timeout=5)
            
            if result.returncode == 0:
                print(result.stdout.strip())
            else:
                print(f"✗ {backend} backend failed")
                
        except Exception as e:
            print(f"✗ {backend} test failed: {e}")

def provide_solutions():
    """Provide solutions based on common scenarios."""
    print("\n💡 Common Solutions")
    print("=" * 50)
    
    solutions = [
        {
            "scenario": "SSH/Remote Session",
            "solution": """
# Enable X11 forwarding
ssh -X username@hostname

# Or use offscreen rendering
export QT_QPA_PLATFORM=offscreen

# Run with conda
conda activate mobileinsight && QT_QPA_PLATFORM=offscreen python mobile_insight_gui.py
""",
        },
        {
            "scenario": "Missing Graphics Drivers",
            "solution": """
# Install Mesa drivers (Ubuntu/Debian)
sudo apt update
sudo apt install mesa-utils libgl1-mesa-glx libgl1-mesa-dri

# Test OpenGL
glxinfo | grep OpenGL
""",
        },
        {
            "scenario": "Wayland Issues",
            "solution": """
# Force X11 backend
export QT_QPA_PLATFORM=xcb

# Or disable Wayland temporarily
export WAYLAND_DISPLAY=""
export XDG_SESSION_TYPE=x11
""",
        },
        {
            "scenario": "WebEngine Problems",
            "solution": """
# Disable GPU acceleration
export QTWEBENGINE_DISABLE_SANDBOX=1
export QTWEBENGINE_CHROMIUM_FLAGS="--disable-gpu --disable-software-rasterizer"

# Or use fallback mode (already implemented in our code)
# The GUI will automatically use QTextEdit instead of QWebEngineView
""",
        },
        {
            "scenario": "Virtual Environment/Docker",
            "solution": """
# Use virtual display
sudo apt install xvfb
export DISPLAY=:99
Xvfb :99 -screen 0 1024x768x24 &

# Run with virtual display
DISPLAY=:99 python mobile_insight_gui.py

# Or use offscreen mode
QT_QPA_PLATFORM=offscreen python mobile_insight_gui.py
""",
        }
    ]
    
    for solution in solutions:
        print(f"\n🔧 {solution['scenario']}:")
        print(solution['solution'])

def create_safe_launcher():
    """Create a launcher script that handles graphics issues automatically."""
    print("\n🚀 Creating Safe Launcher Script")
    print("=" * 50)
    
    launcher_content = '''#!/bin/bash

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
'''
    
    with open('/home/ajax/source/mobileinsight/mi/mobileinsight-core/gui/launch_satellite_gui_safe.sh', 'w') as f:
        f.write(launcher_content)
    
    # Make executable
    os.chmod('/home/ajax/source/mobileinsight/mi/mobileinsight-core/gui/launch_satellite_gui_safe.sh', 0o755)
    
    print("✅ Created safe launcher: launch_satellite_gui_safe.sh")
    print("Run with: ./launch_satellite_gui_safe.sh")

def main():
    """Run comprehensive OpenGL debugging."""
    print("🔧 OpenGL/Graphics Debugging for Satellite GUI")
    print("=" * 60)
    
    check_system_graphics()
    test_qt_backends()
    test_webengine_alternatives()
    test_matplotlib_backends()
    provide_solutions()
    create_safe_launcher()
    
    print("\n🎯 Quick Fix Commands:")
    print("=" * 50)
    print("1. For SSH/Remote: export QT_QPA_PLATFORM=offscreen")
    print("2. For local X11: export QT_QPA_PLATFORM=xcb")
    print("3. Use safe launcher: ./launch_satellite_gui_safe.sh")
    print("4. Test mode: python test_satellite_gui.py")

if __name__ == "__main__":
    main()