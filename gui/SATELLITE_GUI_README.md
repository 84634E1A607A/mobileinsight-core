# MobileInsight Satellite GUI

This GUI application provides three satellite monitoring and analysis pages as requested in GOAL.md.

## Features

### 1. Satellite Identification Page
- **Non-modal dialog** showing satellite tracking information
- **Google Maps integration** with satellite view
- **User terminal location** marked with a red circle icon
- **Satellite positions** displayed with green arrow markers
- **Coverage areas** shown as blue semi-transparent circles around satellites
- **Data table** showing:
  - Satellite Name
  - Distance from user (km)
  - Elevation angle (degrees)
  - Azimuth angle (degrees)
  - Coverage radius (km)
- **Refresh button** to reload satellite data with new mock values

### 2. Satellite Orbit & Service Page
- **Orbital path visualization** on satellite map view
- **Current satellite positions** marked on their orbital paths
- **Service timing information** in data table showing:
  - Satellite Name
  - Current Position (lat, lng)
  - Service Time Remaining (minutes)
  - Next Satellite Entry Time (minutes)
- **Refresh button** to update orbital and service data
- **Color-coded orbital paths** for different satellites

### 3. Real-time Data Visualization Page
- **Two matplotlib plots** displayed in 1:1 ratio:
  1. **Doppler Frequency Shift vs Time**
     - Red scattered points for measured data
     - Blue smooth curve for TLE predictions
     - Y-axis in kHz units
  2. **Distance vs Time**
     - Red scattered points for measured data
     - Blue smooth curve for TLE predictions
     - Y-axis in km units
- **Real-time updates** every second when simulation is running
- **Control buttons**:
  - Start Simulation
  - Stop Simulation
  - Clear Data
- **Mock data generation** using sine wave patterns with noise

## How to Run

### Method 1: Using the Launcher Script
```bash
cd /home/ajax/source/mobileinsight/mi/mobileinsight-core/gui
./launch_satellite_gui.sh
```

### Method 2: Manual Command
```bash
conda activate mobileinsight && cd /home/ajax/source/mobileinsight/mi/mobileinsight-core/gui && python mobile_insight_gui.py
```

## Accessing Satellite Features

Once the main MobileInsight GUI is running:

1. **Menu Bar**: Go to "Satellite" menu and select:
   - "Satellite Identification"
   - "Satellite Orbit & Service"
   - "Real-time Data Visualization"

2. **Toolbar**: Click the satellite-related toolbar buttons:
   - Satellite ID (satellite icon)
   - Satellite Orbit (orbit icon)
   - Real-time Data (chart icon)

## Dependencies

The application requires the following packages (included in mobileinsight conda environment):
- PyQt6 (6.9.1) - Main GUI framework
- PyQt6-WebEngine (6.9.0) - For Google Maps integration
- matplotlib (3.10.6) - For real-time plotting
- numpy (2.3.3) - For numerical operations
- Standard Python libraries: json, math, datetime, random

## Mock Data

Currently, all satellite data is generated using mock/simulation functions:
- **Satellite positions**: Randomly generated coordinates around user location
- **Orbital paths**: Mathematical sine/cosine patterns
- **Service timing**: Random values within realistic ranges
- **Real-time measurements**: Sine wave patterns with added noise
- **TLE predictions**: Smooth sine wave curves

## Notes

- All interfaces use **English** language as requested
- Comprehensive **inline documentation** provided in English
- **Non-modal dialogs** allow multiple windows to be open simultaneously
- Google Maps integration requires API key for full functionality (currently shows fallback demo)
- Real-time simulation continues running until manually stopped

## Technical Architecture

- **Object-oriented design** with separate dialog classes
- **PyQt6 signal/slot mechanism** for event handling
- **Matplotlib integration** with Qt backend for plotting
- **WebEngine integration** for maps display
- **Timer-based updates** for real-time simulation
- **Mock data generators** for demonstration purposes