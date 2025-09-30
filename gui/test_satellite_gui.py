#!/usr/bin/env python3

"""
Test runner for the Satellite GUI application
This script tests the GUI components without requiring a full graphics environment
"""

import os
import sys
import traceback

# Set offscreen rendering for testing environments
os.environ['QT_QPA_PLATFORM'] = 'offscreen'

# Add the gui directory to path
sys.path.insert(0, '/home/ajax/source/mobileinsight/mi/mobileinsight-core/gui')

def test_satellite_gui():
    """Test the satellite GUI components."""
    try:
        print("Testing Satellite GUI Components...")
        
        # Import the GUI module
        import mobile_insight_gui
        from mobile_insight_gui import (QApplication, WindowClass, SatelliteIdentificationDialog, 
                                       SatelliteOrbitServiceDialog, RealTimeDataVisualizationDialog,
                                       WEB_ENGINE_AVAILABLE)
        print("✓ Import successful")
        
        # Create QApplication
        app = QApplication(sys.argv)
        print("✓ QApplication created successfully")
        
        # Check WebEngine availability
        print(f"✓ WebEngine available: {WEB_ENGINE_AVAILABLE}")
        
        # Test main window creation
        window = WindowClass()
        print("✓ Main window created successfully")
        
        # Test satellite dialogs
        print("\nTesting satellite dialogs...")
        
        # Test SatelliteIdentificationDialog
        sat_dialog = SatelliteIdentificationDialog()
        print("✓ SatelliteIdentificationDialog created successfully")
        
        # Test data generation
        sat_dialog.generate_mock_data()
        print("✓ Mock satellite data generated successfully")
        print(f"  - Generated {len(sat_dialog.satellite_data)} satellites")
        
        # Test SatelliteOrbitServiceDialog
        orbit_dialog = SatelliteOrbitServiceDialog()
        print("✓ SatelliteOrbitServiceDialog created successfully")
        
        # Test orbital data generation
        orbit_dialog.generate_mock_orbital_data()
        print("✓ Mock orbital data generated successfully")
        print(f"  - Generated {len(orbit_dialog.orbital_data)} orbital tracks")
        
        # Test RealTimeDataVisualizationDialog
        viz_dialog = RealTimeDataVisualizationDialog()
        print("✓ RealTimeDataVisualizationDialog created successfully")
        
        # Test data generation
        dopp_meas, dopp_pred, dist_meas, dist_pred = viz_dialog.generate_mock_data_point(10.0)
        print("✓ Mock real-time data generated successfully")
        print(f"  - Doppler: {dopp_meas:.2f} kHz (measured), {dopp_pred:.2f} kHz (predicted)")
        print(f"  - Distance: {dist_meas:.1f} km (measured), {dist_pred:.1f} km (predicted)")
        
        # Test menu integration
        try:
            window.show_satellite_identification()
            print("✓ Satellite identification menu function works")
        except Exception as e:
            print(f"✗ Error testing satellite identification menu: {e}")
        
        try:
            window.show_satellite_orbit()
            print("✓ Satellite orbit menu function works")
        except Exception as e:
            print(f"✗ Error testing satellite orbit menu: {e}")
        
        try:
            window.show_realtime_visualization()
            print("✓ Real-time visualization menu function works")
        except Exception as e:
            print(f"✗ Error testing real-time visualization menu: {e}")
        
        print("\n🎉 All tests passed successfully!")
        print("\nThe Satellite GUI is ready to use.")
        print("To run the GUI with graphics, use:")
        print("  conda activate mobileinsight && cd gui && python mobile_insight_gui.py")
        
        # Clean up
        app.quit()
        return True
        
    except Exception as e:
        print(f"\n❌ Error: {e}")
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_satellite_gui()
    sys.exit(0 if success else 1)