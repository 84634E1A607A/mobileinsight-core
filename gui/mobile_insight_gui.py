#!/usr/bin/python3

"""
Python GUI for MobileInsight
Author: Moustafa Alzantot
Date : Feb 26, 2016
Converted to PyQt6 by Assistant
"""

import sys
import os
from pathlib import Path
from threading import Thread
from random import random
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional, Union
import json
import math
import numpy as np

import matplotlib
# Configure matplotlib to use non-interactive backend for headless environments
matplotlib.use('Agg')
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt import NavigationToolbar2QT as NavigationToolbar
from matplotlib.figure import Figure

import xml.dom.minidom
import xml.etree.ElementTree as ET

from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QHBoxLayout, 
                             QWidget, QPushButton, QTableWidget, QTableWidgetItem, 
                             QTreeWidget, QTreeWidgetItem, QLabel, QSlider, QDialog, 
                             QDialogButtonBox, QFileDialog, QMessageBox, QInputDialog,
                             QCheckBox, QListWidget, QListWidgetItem, QProgressDialog, QToolBar, 
                             QStatusBar, QMenuBar, QSplitter, QTextEdit, QFrame,
                             QHeaderView, QGroupBox)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QTimer, QSize, QEvent, QUrl
from PyQt6.QtGui import QAction, QIcon, QPixmap, QFont, QMovie, QCloseEvent

# Try to import WebEngine, fall back to TextEdit if not available
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    WEB_ENGINE_AVAILABLE = True
except ImportError:
    WEB_ENGINE_AVAILABLE = False
    print("WebEngine not available, using fallback text display")

from mobile_insight.analyzer import LogAnalyzer
from mobile_insight.monitor.dm_collector.dm_endec.dm_log_packet import DMLogPacket

# Get the directory containing this script for relative resource paths
GUI_DIR = Path(__file__).parent
ICONS_DIR = GUI_DIR / "icons"


class ResultEvent:
    def __init__(self, data: List[Dict[str, Any]]) -> None:
        self.data = data


class ProgressDialog(QDialog):
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint)
        layout = QVBoxLayout()
        
        # Create a loading animation - using a simple label for now
        self.label = QLabel("Loading...")
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        # Try to load a GIF if available
        try:
            loading_gif_path = ICONS_DIR / "loading.gif"
            if loading_gif_path.exists():
                movie = QMovie(str(loading_gif_path))
                if movie.isValid():
                    self.label.setMovie(movie)
                    movie.start()
            else:
                # Fallback to text
                self.label.setText("Loading...")
        except Exception:
            # Fallback to text
            self.label.setText("Loading...")
        
        layout.addWidget(self.label)
        self.setLayout(layout)
        self.resize(200, 100)


class TimeWindowDialog(QDialog):
    def __init__(self, parent: Optional[QWidget], start_time: datetime, end_time: datetime) -> None:
        super().__init__(parent)
        self.setWindowTitle("Time Window")
        
        layout = QVBoxLayout()
        
        self.start_label = QLabel("...")
        self.end_label = QLabel("...")
        self.window_label = QLabel("\t to \t")
        
        font = QFont()
        font.setBold(True)
        self.start_label.setFont(font)
        self.end_label.setFont(font)
        
        font_italic = QFont()
        font_italic.setItalic(True)
        self.window_label.setFont(font_italic)
        
        label_layout = QHBoxLayout()
        label_layout.addWidget(self.start_label)
        label_layout.addWidget(self.window_label)
        label_layout.addWidget(self.end_label)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        start_layout = QHBoxLayout()
        start_layout.addWidget(QLabel("Start: "))
        self.start_slider = QSlider(Qt.Orientation.Horizontal)
        self.start_slider.setRange(0, 100)
        self.start_slider.setValue(0)
        self.start_slider.setMinimumWidth(250)
        start_layout.addWidget(self.start_slider)
        self.start_slider.valueChanged.connect(self.start_slider_update)
        
        end_layout = QHBoxLayout()
        end_layout.addWidget(QLabel("End: "))
        self.end_slider = QSlider(Qt.Orientation.Horizontal)
        self.end_slider.setRange(0, 100)
        self.end_slider.setValue(100)
        self.end_slider.setMinimumWidth(250)
        end_layout.addWidget(self.end_slider)
        self.end_slider.valueChanged.connect(self.end_slider_update)
        
        self.start_time: datetime = start_time
        self.cur_end: datetime = end_time
        self.cur_start: datetime = self.start_time
        self.unit_seconds: float = (end_time - start_time).total_seconds() / 100.0
        
        self.updateUI()
        
        layout.addLayout(label_layout)
        layout.addLayout(start_layout)
        layout.addLayout(end_layout)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        
    def start_slider_update(self, value: int) -> None:
        delta_seconds = value * self.unit_seconds
        self.cur_start = self.start_time + timedelta(seconds=int(delta_seconds))
        self.updateUI()
        
    def end_slider_update(self, value: int) -> None:
        delta_seconds = value * self.unit_seconds
        self.cur_end = self.start_time + timedelta(seconds=int(delta_seconds))
        self.updateUI()
        
    def updateUI(self) -> None:
        self.start_label.setText(str(self.cur_start))
        self.end_label.setText(str(self.cur_end))


class MyMCD(QDialog):
    def __init__(self, parent: Optional[QWidget], message: str, caption: str, choices: Optional[List[str]] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle(caption)
        
        if choices is None:
            choices = []
        
        layout = QVBoxLayout()
        
        self.message_label = QLabel(message)
        self.list_widget = QListWidget()
        
        for choice in choices:
            item = QListWidgetItem(choice)
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsUserCheckable)
            item.setCheckState(Qt.CheckState.Unchecked)
            self.list_widget.addItem(item)
        
        self.select_all_checkbox = QCheckBox('Select all')
        self.select_all_checkbox.stateChanged.connect(self.toggle_all)
        
        button_box = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | 
                                     QDialogButtonBox.StandardButton.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(self.message_label)
        layout.addWidget(self.list_widget)
        layout.addWidget(self.select_all_checkbox)
        layout.addWidget(button_box)
        
        self.setLayout(layout)
        self.resize(400, 300)
        
    def GetSelections(self) -> List[int]:
        selections = []
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item and item.checkState() == Qt.CheckState.Checked:
                selections.append(i)
        return selections
        
    def toggle_all(self, state: int) -> None:
        check_state = Qt.CheckState.Checked if state == 2 else Qt.CheckState.Unchecked
        for i in range(self.list_widget.count()):
            item = self.list_widget.item(i)
            if item:
                item.setCheckState(check_state)


class SatelliteIdentificationDialog(QDialog):
    """
    Non-modal dialog for satellite identification and tracking.
    Shows satellite positions on Google Maps with coverage areas and data table.
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Satellite Identification")
        self.setWindowFlags(Qt.WindowType.Window)  # Make it non-modal
        self.resize(1000, 700)
        
        # Mock satellite data
        self.satellite_data: List[Dict[str, Any]] = []
        self.user_location = {"lat": 40.7128, "lng": -74.0060}  # New York as default
        
        self.setup_ui()
        self.generate_mock_data()
        self.update_map()
        self.update_table()
        
    def setup_ui(self) -> None:
        """Set up the user interface components."""
        layout = QVBoxLayout()
        
        # Top panel with map
        map_group = QGroupBox("Satellite Map View")
        map_layout = QVBoxLayout()
        
        # Web view for Google Maps (with fallback)
        if WEB_ENGINE_AVAILABLE:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            from PyQt6.QtWebEngineCore import QWebEngineSettings
            self.map_view = QWebEngineView()
            self.map_view.setMinimumHeight(400)
            
            # Configure WebEngine settings for better compatibility
            try:
                settings = self.map_view.settings()
                if settings:
                    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
            except Exception as e:
                print(f"Warning: Could not configure WebEngine settings: {e}")
            
            map_layout.addWidget(self.map_view)
            self.is_web_engine = True
        else:
            self.map_view = QTextEdit()
            self.map_view.setMinimumHeight(400)
            self.map_view.setReadOnly(True)
            self.map_view.setPlainText("Google Maps integration would appear here.\nWebEngine not available - using fallback display.")
            map_layout.addWidget(self.map_view)
            self.is_web_engine = False
        
        map_group.setLayout(map_layout)
        layout.addWidget(map_group, 2)
        
        # Bottom panel with data table and controls
        data_group = QGroupBox("Satellite Data")
        data_layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.refresh_btn = QPushButton("Refresh Satellite Data")
        self.refresh_btn.clicked.connect(self.refresh_data)
        controls_layout.addWidget(self.refresh_btn)
        controls_layout.addStretch()
        
        # Data table
        self.data_table = QTableWidget()
        self.data_table.setColumnCount(5)
        self.data_table.setHorizontalHeaderLabels([
            "Satellite Name", "Distance (km)", "Elevation (°)", "Azimuth (°)", "Coverage Radius (km)"
        ])
        header = self.data_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        data_layout.addLayout(controls_layout)
        data_layout.addWidget(self.data_table)
        
        data_group.setLayout(data_layout)
        layout.addWidget(data_group, 1)
        
        self.setLayout(layout)
        
    def generate_mock_data(self) -> None:
        """Generate mock satellite data for demonstration."""
        satellites = [
            {"name": "GPS IIR-16", "lat": 45.0, "lng": -75.0},
            {"name": "GLONASS-M", "lat": 50.0, "lng": -70.0},
            {"name": "Galileo-FOC", "lat": 42.0, "lng": -78.0},
            {"name": "BeiDou-3", "lat": 48.0, "lng": -72.0},
        ]
        
        self.satellite_data = []
        for sat in satellites:
            # Calculate mock distance, elevation, and azimuth
            distance = 20000 + random() * 6000  # 20,000-26,000 km (typical GPS orbit)
            elevation = 15 + random() * 60  # 15-75 degrees
            azimuth = random() * 360  # 0-360 degrees
            coverage_radius = 2000 + random() * 1000  # 2000-3000 km coverage
            
            self.satellite_data.append({
                "name": sat["name"],
                "lat": sat["lat"],
                "lng": sat["lng"],
                "distance": distance,
                "elevation": elevation,
                "azimuth": azimuth,
                "coverage_radius": coverage_radius
            })
    
    def update_map(self) -> None:
        """Update the Google Maps view with satellite positions."""
        if not self.is_web_engine:
            # Update fallback text display
            fallback_text = f"""Google Maps Satellite Tracking (Fallback View)

User Location: {self.user_location['lat']:.4f}, {self.user_location['lng']:.4f}

Satellites:
"""
            for sat in self.satellite_data:
                fallback_text += f"\n{sat['name']}:"
                fallback_text += f"\n  Position: {sat['lat']:.2f}, {sat['lng']:.2f}"
                fallback_text += f"\n  Distance: {sat['distance']:.1f} km"
                fallback_text += f"\n  Coverage: {sat['coverage_radius']:.1f} km radius\n"
            
            # Type cast to QTextEdit for fallback case
            from typing import cast
            text_view = cast(QTextEdit, self.map_view)
            text_view.setPlainText(fallback_text)
            return
            
        # Create HTML content with Google Maps
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Satellite Tracking</title>
            <style>
                #map {{ height: 100%; width: 100%; }}
                html, body {{ height: 100%; margin: 0; padding: 0; font-family: Arial, sans-serif; }}
                .loading {{ 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    height: 100%; 
                    background: #f0f0f0; 
                    color: #666;
                    text-align: center;
                }}
                .error {{ 
                    background: #ffebee; 
                    color: #c62828; 
                    padding: 20px;
                }}
            </style>
        </head>
        <body>
            <div id="map">
                <div class="loading">
                    <div>
                        <h3>Loading Satellite Map...</h3>
                        <p>Initializing Google Maps</p>
                    </div>
                </div>
            </div>
            <script>
                console.log('Starting satellite map initialization...');
                
                function showError(message) {{
                    console.error('Map error:', message);
                    document.getElementById('map').innerHTML = 
                        '<div class="loading error">' +
                        '<div>' +
                        '<h3>Map Display Error</h3>' +
                        '<p>' + message + '</p>' +
                        '<p>User Location: {self.user_location["lat"]:.4f}, {self.user_location["lng"]:.4f}</p>' +
                        '<p>Satellite Data: {len(self.satellite_data)} satellites</p>' +
                        '</div></div>';
                }}
                
                function initMap() {{
                    try {{
                        console.log('Initializing Google Maps...');
                        
                        // User location
                        var userLocation = {{lat: {self.user_location['lat']}, lng: {self.user_location['lng']}}};
                        console.log('User location:', userLocation);
                        
                        // Create map
                        var map = new google.maps.Map(document.getElementById('map'), {{
                            zoom: 6,
                            center: userLocation,
                            mapTypeId: 'satellite',
                            gestureHandling: 'greedy'
                        }});
                        
                        console.log('Map created successfully');
                        
                        // Add user location marker
                        var userMarker = new google.maps.Marker({{
                            position: userLocation,
                            map: map,
                            title: 'User Terminal',
                            icon: {{
                                path: google.maps.SymbolPath.CIRCLE,
                                scale: 8,
                                fillColor: '#FF0000',
                                fillOpacity: 1,
                                strokeWeight: 2,
                                strokeColor: '#FFFFFF'
                            }}
                        }});
                        
                        // Add satellite markers and coverage circles
                        var satellites = {json.dumps(self.satellite_data)};
                        console.log('Adding', satellites.length, 'satellites');
                        
                        satellites.forEach(function(satellite, index) {{
                            console.log('Adding satellite:', satellite.name);
                            
                            // Satellite marker
                            var satelliteMarker = new google.maps.Marker({{
                                position: {{lat: satellite.lat, lng: satellite.lng}},
                                map: map,
                                title: satellite.name + ' (Distance: ' + satellite.distance.toFixed(1) + ' km)',
                                icon: {{
                                    path: google.maps.SymbolPath.BACKWARD_CLOSED_ARROW,
                                    scale: 6,
                                    fillColor: '#00FF00',
                                    fillOpacity: 1,
                                    strokeWeight: 2,
                                    strokeColor: '#FFFFFF'
                                }}
                            }});
                            
                            // Coverage circle
                            var coverageCircle = new google.maps.Circle({{
                                strokeColor: '#0066FF',
                                strokeOpacity: 0.8,
                                strokeWeight: 2,
                                fillColor: '#0066FF',
                                fillOpacity: 0.15,
                                map: map,
                                center: {{lat: satellite.lat, lng: satellite.lng}},
                                radius: satellite.coverage_radius * 1000  // Convert km to meters
                            }});
                        }});
                        
                        console.log('Map initialization completed successfully');
                        
                    }} catch (error) {{
                        console.error('Error initializing map:', error);
                        showError('Failed to initialize map: ' + error.message);
                    }}
                }}
                
                // Load Google Maps API with callback
                function loadGoogleMaps() {{
                    console.log('Loading Google Maps API...');
                    
                    var script = document.createElement('script');
                    script.async = true;
                    script.defer = true;
                    script.src = 'https://maps.googleapis.com/maps/api/js?key=AIzaSyCW6ZPZ8ahcXcRYGqDK74CPfvIJnhbgysE&callback=initMap';
                    script.onerror = function() {{
                        console.error('Failed to load Google Maps API');
                        showError('Unable to load Google Maps API. Please check your internet connection.');
                    }};
                    
                    document.head.appendChild(script);
                }}
                
                // Initialize when DOM is ready
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', loadGoogleMaps);
                }} else {{
                    loadGoogleMaps();
                }}
                
                // Fallback timeout
                setTimeout(function() {{
                    if (typeof google === 'undefined') {{
                        showError('Google Maps API failed to load within timeout period.');
                    }}
                }}, 10000);
            </script>
        </body>
        </html>
        """
        
        if self.is_web_engine:
            from typing import cast
            # Type cast to QWebEngineView when WebEngine is available
            if WEB_ENGINE_AVAILABLE:
                from PyQt6.QtWebEngineWidgets import QWebEngineView
                web_view = cast(QWebEngineView, self.map_view)
                # Enable debugging and monitoring
                try:
                    # Connect to load finished signal for debugging
                    web_view.loadFinished.connect(lambda success: 
                        print(f"Satellite map load finished: {success}"))
                    # Set HTML content
                    web_view.setHtml(html_content)
                    print("Satellite map HTML content set successfully")
                except Exception as e:
                    print(f"Error setting satellite map HTML: {e}")
    
    def update_table(self) -> None:
        """Update the satellite data table."""
        self.data_table.setRowCount(len(self.satellite_data))
        
        for row, satellite in enumerate(self.satellite_data):
            self.data_table.setItem(row, 0, QTableWidgetItem(satellite["name"]))
            self.data_table.setItem(row, 1, QTableWidgetItem(f"{satellite['distance']:.1f}"))
            self.data_table.setItem(row, 2, QTableWidgetItem(f"{satellite['elevation']:.1f}"))
            self.data_table.setItem(row, 3, QTableWidgetItem(f"{satellite['azimuth']:.1f}"))
            self.data_table.setItem(row, 4, QTableWidgetItem(f"{satellite['coverage_radius']:.1f}"))
    
    def refresh_data(self) -> None:
        """Refresh satellite data by generating new mock data."""
        self.generate_mock_data()
        self.update_map()
        self.update_table()


class SatelliteOrbitServiceDialog(QDialog):
    """
    Non-modal dialog for satellite orbit and service information.
    Shows satellite orbital paths and service timing data.
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Satellite Orbit & Service")
        self.setWindowFlags(Qt.WindowType.Window)  # Make it non-modal
        self.resize(1000, 700)
        
        # Mock orbital data
        self.orbital_data: List[Dict[str, Any]] = []
        self.user_location = {"lat": 40.7128, "lng": -74.0060}  # New York as default
        
        self.setup_ui()
        self.generate_mock_orbital_data()
        self.update_orbital_map()
        self.update_service_table()
        
    def setup_ui(self) -> None:
        """Set up the user interface components."""
        layout = QVBoxLayout()
        
        # Top panel with orbital map
        map_group = QGroupBox("Satellite Orbital View")
        map_layout = QVBoxLayout()
        
        # Web view for orbital display (with fallback)
        if WEB_ENGINE_AVAILABLE:
            from PyQt6.QtWebEngineWidgets import QWebEngineView
            from PyQt6.QtWebEngineCore import QWebEngineSettings
            self.orbital_view = QWebEngineView()
            self.orbital_view.setMinimumHeight(400)
            
            # Configure WebEngine settings for better compatibility
            try:
                settings = self.orbital_view.settings()
                if settings:
                    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessFileUrls, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.AllowRunningInsecureContent, True)
            except Exception as e:
                print(f"Warning: Could not configure orbital WebEngine settings: {e}")
            
            map_layout.addWidget(self.orbital_view)
            self.is_orbital_web_engine = True
        else:
            self.orbital_view = QTextEdit()
            self.orbital_view.setMinimumHeight(400)
            self.orbital_view.setReadOnly(True)
            self.orbital_view.setPlainText("Orbital tracking view would appear here.\nWebEngine not available - using fallback display.")
            map_layout.addWidget(self.orbital_view)
            self.is_orbital_web_engine = False
        
        map_group.setLayout(map_layout)
        layout.addWidget(map_group, 2)
        
        # Bottom panel with service data table and controls
        service_group = QGroupBox("Service Information")
        service_layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        self.refresh_orbital_btn = QPushButton("Refresh Orbital Data")
        self.refresh_orbital_btn.clicked.connect(self.refresh_orbital_data)
        controls_layout.addWidget(self.refresh_orbital_btn)
        controls_layout.addStretch()
        
        # Service timing table
        self.service_table = QTableWidget()
        self.service_table.setColumnCount(4)
        self.service_table.setHorizontalHeaderLabels([
            "Satellite Name", "Current Position", "Service Time Remaining (min)", "Next Satellite Entry (min)"
        ])
        header = self.service_table.horizontalHeader()
        if header:
            header.setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        
        service_layout.addLayout(controls_layout)
        service_layout.addWidget(self.service_table)
        
        service_group.setLayout(service_layout)
        layout.addWidget(service_group, 1)
        
        self.setLayout(layout)
        
    def generate_mock_orbital_data(self) -> None:
        """Generate mock orbital data including satellite positions and service timing."""
        satellites = [
            {"name": "GPS IIR-16", "orbital_period": 12},  # hours
            {"name": "GLONASS-M", "orbital_period": 11.25},
            {"name": "Galileo-FOC", "orbital_period": 14},
            {"name": "BeiDou-3", "orbital_period": 12.5},
        ]
        
        self.orbital_data = []
        for sat in satellites:
            # Generate orbital path points
            orbital_points = []
            for i in range(36):  # 36 points for orbital path
                angle = i * 10  # degrees
                lat = 50 * math.sin(math.radians(angle + random() * 30))
                lng = -180 + (angle * 2) % 360 + random() * 20 - 10
                orbital_points.append({"lat": lat, "lng": lng})
            
            # Current position (random point on orbit)
            current_idx = int(random() * len(orbital_points))
            current_pos = orbital_points[current_idx]
            
            # Service timing
            service_remaining = random() * 45  # 0-45 minutes
            next_entry = 90 + random() * 60  # 90-150 minutes
            
            self.orbital_data.append({
                "name": sat["name"],
                "orbital_period": sat["orbital_period"],
                "orbital_points": orbital_points,
                "current_position": current_pos,
                "service_remaining": service_remaining,
                "next_entry": next_entry
            })
    
    def update_orbital_map(self) -> None:
        """Update the orbital map view with satellite paths."""
        if not self.is_orbital_web_engine:
            # Update fallback text display
            fallback_text = f"""Satellite Orbital Tracking (Fallback View)

User Location: {self.user_location['lat']:.4f}, {self.user_location['lng']:.4f}

Orbital Data:
"""
            for sat in self.orbital_data:
                fallback_text += f"\n{sat['name']}:"
                fallback_text += f"\n  Current Position: {sat['current_position']['lat']:.2f}, {sat['current_position']['lng']:.2f}"
                fallback_text += f"\n  Orbital Period: {sat['orbital_period']:.1f} hours"
                fallback_text += f"\n  Service Remaining: {sat['service_remaining']:.1f} min"
                fallback_text += f"\n  Next Entry: {sat['next_entry']:.1f} min\n"
            
            # Type cast to QTextEdit for fallback case
            from typing import cast
            text_view = cast(QTextEdit, self.orbital_view)
            text_view.setPlainText(fallback_text)
            return
            
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>Satellite Orbital Tracking</title>
            <style>
                #map {{ height: 100%; width: 100%; }}
                html, body {{ height: 100%; margin: 0; padding: 0; font-family: Arial, sans-serif; }}
                .loading {{ 
                    display: flex; 
                    align-items: center; 
                    justify-content: center; 
                    height: 100%; 
                    background: #f0f0f0; 
                    color: #666;
                    text-align: center;
                }}
                .error {{ 
                    background: #ffebee; 
                    color: #c62828; 
                    padding: 20px;
                }}
            </style>
        </head>
        <body>
            <div id="map">
                <div class="loading">
                    <div>
                        <h3>Loading Orbital Map...</h3>
                        <p>Initializing satellite tracking</p>
                    </div>
                </div>
            </div>
            <script>
                console.log('Starting orbital map initialization...');
                
                function showError(message) {{
                    console.error('Orbital map error:', message);
                    document.getElementById('map').innerHTML = 
                        '<div class="loading error">' +
                        '<div>' +
                        '<h3>Orbital Map Error</h3>' +
                        '<p>' + message + '</p>' +
                        '<p>User Location: {self.user_location["lat"]:.4f}, {self.user_location["lng"]:.4f}</p>' +
                        '<p>Orbital Data: {len(self.orbital_data)} satellites</p>' +
                        '</div></div>';
                }}
                
                function initMap() {{
                    try {{
                        console.log('Initializing orbital map...');
                        
                        // User location
                        var userLocation = {{lat: {self.user_location['lat']}, lng: {self.user_location['lng']}}};
                        console.log('User location:', userLocation);
                        
                        // Create map
                        var map = new google.maps.Map(document.getElementById('map'), {{
                            zoom: 3,
                            center: {{lat: 20, lng: 0}},
                            mapTypeId: 'satellite',
                            gestureHandling: 'greedy'
                        }});
                        
                        console.log('Orbital map created successfully');
                        
                        // Add user location marker
                        var userMarker = new google.maps.Marker({{
                            position: userLocation,
                            map: map,
                            title: 'User Terminal',
                            icon: {{
                                path: google.maps.SymbolPath.CIRCLE,
                                scale: 8,
                                fillColor: '#FF0000',
                                fillOpacity: 1,
                                strokeWeight: 2,
                                strokeColor: '#FFFFFF'
                            }}
                        }});
                        
                        // Add satellite orbital paths and current positions
                        var orbitalData = {json.dumps(self.orbital_data)};
                        var colors = ['#FF6B6B', '#4ECDC4', '#45B7D1', '#96CEB4'];
                        
                        console.log('Adding orbital data for', orbitalData.length, 'satellites');
                        
                        orbitalData.forEach(function(satellite, index) {{
                            var color = colors[index % colors.length];
                            console.log('Drawing orbital path for:', satellite.name);
                            
                            // Draw orbital path
                            var orbitalPath = new google.maps.Polyline({{
                                path: satellite.orbital_points,
                                geodesic: true,
                                strokeColor: color,
                                strokeOpacity: 1.0,
                                strokeWeight: 3
                            }});
                            orbitalPath.setMap(map);
                            
                            // Current satellite position
                            var satelliteMarker = new google.maps.Marker({{
                                position: satellite.current_position,
                                map: map,
                                title: satellite.name + ' (Service: ' + satellite.service_remaining.toFixed(1) + ' min)',
                                icon: {{
                                    path: google.maps.SymbolPath.FORWARD_CLOSED_ARROW,
                                    scale: 8,
                                    fillColor: color,
                                    fillOpacity: 1,
                                    strokeWeight: 2,
                                    strokeColor: '#FFFFFF'
                                }}
                            }});
                        }});
                        
                        console.log('Orbital map initialization completed successfully');
                        
                    }} catch (error) {{
                        console.error('Error initializing orbital map:', error);
                        showError('Failed to initialize orbital map: ' + error.message);
                    }}
                }}
                
                // Load Google Maps API with callback
                function loadGoogleMaps() {{
                    console.log('Loading Google Maps API for orbital tracking...');
                    
                    var script = document.createElement('script');
                    script.async = true;
                    script.defer = true;
                    script.src = 'https://maps.googleapis.com/maps/api/js?key=AIzaSyCW6ZPZ8ahcXcRYGqDK74CPfvIJnhbgysE&callback=initMap';
                    script.onerror = function() {{
                        console.error('Failed to load Google Maps API for orbital tracking');
                        showError('Unable to load Google Maps API. Please check your internet connection.');
                    }};
                    
                    document.head.appendChild(script);
                }}
                
                // Initialize when DOM is ready
                if (document.readyState === 'loading') {{
                    document.addEventListener('DOMContentLoaded', loadGoogleMaps);
                }} else {{
                    loadGoogleMaps();
                }}
                
                // Fallback timeout
                setTimeout(function() {{
                    if (typeof google === 'undefined') {{
                        showError('Google Maps API failed to load within timeout period.');
                    }}
                }}, 10000);
            </script>
        </body>
        </html>
        """
        
        if self.is_orbital_web_engine:
            from typing import cast
            # Type cast to QWebEngineView when WebEngine is available
            if WEB_ENGINE_AVAILABLE:
                from PyQt6.QtWebEngineWidgets import QWebEngineView
                web_view = cast(QWebEngineView, self.orbital_view)
                # Enable debugging and monitoring
                try:
                    # Connect to load finished signal for debugging
                    web_view.loadFinished.connect(lambda success: 
                        print(f"Orbital map load finished: {success}"))
                    # Set HTML content
                    web_view.setHtml(html_content)
                    print("Orbital map HTML content set successfully")
                except Exception as e:
                    print(f"Error setting orbital map HTML: {e}")
    
    def update_service_table(self) -> None:
        """Update the service timing data table."""
        self.service_table.setRowCount(len(self.orbital_data))
        
        for row, satellite in enumerate(self.orbital_data):
            pos_str = f"{satellite['current_position']['lat']:.2f}, {satellite['current_position']['lng']:.2f}"
            
            self.service_table.setItem(row, 0, QTableWidgetItem(satellite["name"]))
            self.service_table.setItem(row, 1, QTableWidgetItem(pos_str))
            self.service_table.setItem(row, 2, QTableWidgetItem(f"{satellite['service_remaining']:.1f}"))
            self.service_table.setItem(row, 3, QTableWidgetItem(f"{satellite['next_entry']:.1f}"))
    
    def refresh_orbital_data(self) -> None:
        """Refresh orbital data by generating new mock data."""
        self.generate_mock_orbital_data()
        self.update_orbital_map()
        self.update_service_table()


class RealTimeDataVisualizationDialog(QDialog):
    """
    Non-modal dialog for real-time data visualization.
    Shows two matplotlib plots: Doppler frequency shift and distance vs time.
    """
    
    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Real-time Data Visualization")
        self.setWindowFlags(Qt.WindowType.Window)  # Make it non-modal
        self.resize(1000, 700)
        
        # Data storage for plots
        self.time_data: List[float] = []
        self.doppler_measured: List[float] = []
        self.doppler_predicted: List[float] = []
        self.distance_measured: List[float] = []
        self.distance_predicted: List[float] = []
        
        # Timing for data generation
        self.start_time = datetime.now()
        self.data_timer = QTimer()
        self.data_timer.timeout.connect(self.update_data)
        
        self.setup_ui()
        self.start_simulation()
        
    def setup_ui(self) -> None:
        """Set up the user interface with two matplotlib plots."""
        layout = QVBoxLayout()
        
        # Controls
        controls_layout = QHBoxLayout()
        
        self.start_btn = QPushButton("Start Simulation")
        self.start_btn.clicked.connect(self.start_simulation)
        
        self.stop_btn = QPushButton("Stop Simulation")
        self.stop_btn.clicked.connect(self.stop_simulation)
        
        self.clear_btn = QPushButton("Clear Data")
        self.clear_btn.clicked.connect(self.clear_data)
        
        controls_layout.addWidget(self.start_btn)
        controls_layout.addWidget(self.stop_btn)
        controls_layout.addWidget(self.clear_btn)
        controls_layout.addStretch()
        
        layout.addLayout(controls_layout)
        
        # Matplotlib figures
        # Doppler frequency shift plot
        self.doppler_figure = Figure(figsize=(10, 4), dpi=100)
        self.doppler_canvas = FigureCanvas(self.doppler_figure)
        self.doppler_axes = self.doppler_figure.add_subplot(111)
        self.doppler_axes.set_title('Doppler Frequency Shift vs Time')
        self.doppler_axes.set_xlabel('Time (seconds)')
        self.doppler_axes.set_ylabel('Frequency Shift (kHz)')
        self.doppler_axes.grid(True)
        self.doppler_axes.legend(['Measured (Scattered)', 'Predicted (TLE)'])
        
        # Distance plot
        self.distance_figure = Figure(figsize=(10, 4), dpi=100)
        self.distance_canvas = FigureCanvas(self.distance_figure)
        self.distance_axes = self.distance_figure.add_subplot(111)
        self.distance_axes.set_title('Distance vs Time')
        self.distance_axes.set_xlabel('Time (seconds)')
        self.distance_axes.set_ylabel('Distance (km)')
        self.distance_axes.grid(True)
        self.distance_axes.legend(['Measured (Scattered)', 'Predicted (TLE)'])
        
        # Add canvases to layout (1:1 ratio)
        layout.addWidget(self.doppler_canvas, 1)
        layout.addWidget(self.distance_canvas, 1)
        
        self.setLayout(layout)
        
    def generate_mock_data_point(self, t: float) -> tuple[float, float, float, float]:
        """
        Generate mock data points for Doppler shift and distance.
        
        Args:
            t: Current time in seconds
            
        Returns:
            Tuple of (doppler_measured, doppler_predicted, distance_measured, distance_predicted)
        """
        # Base sine wave patterns with some randomization
        doppler_base = 5 * math.sin(0.1 * t) + 2 * math.sin(0.05 * t)  # kHz
        distance_base = 22000 + 2000 * math.sin(0.08 * t) + 1000 * math.cos(0.12 * t)  # km
        
        # Add noise to measured values
        doppler_measured = doppler_base + (random() - 0.5) * 2  # ±1 kHz noise
        distance_measured = distance_base + (random() - 0.5) * 200  # ±100 km noise
        
        # Predicted values are smoother
        doppler_predicted = doppler_base
        distance_predicted = distance_base
        
        return doppler_measured, doppler_predicted, distance_measured, distance_predicted
    
    def update_data(self) -> None:
        """Update data and refresh plots."""
        current_time = (datetime.now() - self.start_time).total_seconds()
        
        # Generate new data point
        dopp_meas, dopp_pred, dist_meas, dist_pred = self.generate_mock_data_point(current_time)
        
        # Append to data arrays
        self.time_data.append(current_time)
        self.doppler_measured.append(dopp_meas)
        self.doppler_predicted.append(dopp_pred)
        self.distance_measured.append(dist_meas)
        self.distance_predicted.append(dist_pred)
        
        # Keep only last 100 points for performance
        if len(self.time_data) > 100:
            self.time_data = self.time_data[-100:]
            self.doppler_measured = self.doppler_measured[-100:]
            self.doppler_predicted = self.doppler_predicted[-100:]
            self.distance_measured = self.distance_measured[-100:]
            self.distance_predicted = self.distance_predicted[-100:]
        
        # Update plots
        self.update_plots()
    
    def update_plots(self) -> None:
        """Update both matplotlib plots with current data."""
        if not self.time_data:
            return
            
        # Clear previous plots
        self.doppler_axes.clear()
        self.distance_axes.clear()
        
        # Doppler plot
        self.doppler_axes.scatter(self.time_data, self.doppler_measured, 
                                 c='red', s=20, alpha=0.7, label='Measured (Scattered)')
        self.doppler_axes.plot(self.time_data, self.doppler_predicted, 
                              'b-', linewidth=2, label='Predicted (TLE)')
        self.doppler_axes.set_title('Doppler Frequency Shift vs Time')
        self.doppler_axes.set_xlabel('Time (seconds)')
        self.doppler_axes.set_ylabel('Frequency Shift (kHz)')
        self.doppler_axes.grid(True)
        self.doppler_axes.legend()
        
        # Distance plot
        self.distance_axes.scatter(self.time_data, self.distance_measured, 
                                  c='red', s=20, alpha=0.7, label='Measured (Scattered)')
        self.distance_axes.plot(self.time_data, self.distance_predicted, 
                               'b-', linewidth=2, label='Predicted (TLE)')
        self.distance_axes.set_title('Distance vs Time')
        self.distance_axes.set_xlabel('Time (seconds)')
        self.distance_axes.set_ylabel('Distance (km)')
        self.distance_axes.grid(True)
        self.distance_axes.legend()
        
        # Refresh canvases
        self.doppler_canvas.draw()
        self.distance_canvas.draw()
    
    def start_simulation(self) -> None:
        """Start the real-time data simulation."""
        self.start_time = datetime.now()
        self.data_timer.start(1000)  # Update every 1 second
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
    
    def stop_simulation(self) -> None:
        """Stop the real-time data simulation."""
        self.data_timer.stop()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
    
    def clear_data(self) -> None:
        """Clear all data and reset plots."""
        self.stop_simulation()
        self.time_data.clear()
        self.doppler_measured.clear()
        self.doppler_predicted.clear()
        self.distance_measured.clear()
        self.distance_predicted.clear()
        
        # Clear plots
        self.doppler_axes.clear()
        self.distance_axes.clear()
        
        # Reset plot formatting
        self.doppler_axes.set_title('Doppler Frequency Shift vs Time')
        self.doppler_axes.set_xlabel('Time (seconds)')
        self.doppler_axes.set_ylabel('Frequency Shift (kHz)')
        self.doppler_axes.grid(True)
        
        self.distance_axes.set_title('Distance vs Time')
        self.distance_axes.set_xlabel('Time (seconds)')
        self.distance_axes.set_ylabel('Distance (km)')
        self.distance_axes.grid(True)
        
        self.doppler_canvas.draw()
        self.distance_canvas.draw()


class WindowClass(QMainWindow):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

        self.min_time: datetime = datetime.strptime("3000 Jan 1", '%Y %b %d')
        self.max_time: datetime = datetime.strptime("1900 Jan 1", '%Y %b %d')
        self.selectedTypes: Optional[List[str]] = None  # Message Filters
        self.progressDialog: Optional[ProgressDialog] = None
        self.data: Optional[List[Dict[str, Any]]] = None
        self.data_view: Optional[List[Dict[str, Any]]] = None
        self.pending_result: Optional[ResultEvent] = None
        self.content: Dict[str, Any] = {}
        
        # Satellite dialog instances
        self.satellite_id_dialog: Optional[SatelliteIdentificationDialog] = None
        self.satellite_orbit_dialog: Optional[SatelliteOrbitServiceDialog] = None
        self.realtime_viz_dialog: Optional[RealTimeDataVisualizationDialog] = None
        
        self.basicGUI()

    def basicGUI(self) -> None:

        self._log_analyzer = LogAnalyzer(self.OnReadComplete)
        
        # Menu Bar
        menubar = self.menuBar()
        if menubar:
            file_menu = menubar.addMenu('File')
            satellite_menu = menubar.addMenu('Satellite')

            open_action = QAction('Open', self)
            open_action.setShortcut('Ctrl+O')
            open_action.triggered.connect(self.Open)
            if file_menu:
                file_menu.addAction(open_action)

            exit_action = QAction('Exit', self)
            exit_action.setShortcut('Ctrl+Q')
            exit_action.triggered.connect(self.close)
            if file_menu:
                file_menu.addAction(exit_action)
                
            # Satellite menu items
            satellite_id_action = QAction('Satellite Identification', self)
            satellite_id_action.triggered.connect(self.show_satellite_identification)
            if satellite_menu:
                satellite_menu.addAction(satellite_id_action)
                
            satellite_orbit_action = QAction('Satellite Orbit && Service', self)
            satellite_orbit_action.triggered.connect(self.show_satellite_orbit)
            if satellite_menu:
                satellite_menu.addAction(satellite_orbit_action)
                
            realtime_viz_action = QAction('Real-time Data Visualization', self)
            realtime_viz_action.triggered.connect(self.show_realtime_visualization)
            if satellite_menu:
                satellite_menu.addAction(realtime_viz_action)

        # Toolbar
        self.toolbar = QToolBar()
        self.toolbar.setWindowTitle("Tool bar")
        self.addToolBar(self.toolbar)
        try:
            toggle_action = self.toolbar.toggleViewAction()
            if toggle_action is not None:
                toggle_action.setText("Show tool bar")
        except Exception:
            pass

        # Helper function to create icons
        def create_icon(icon_name: str) -> QIcon:
            try:
                icon_path = ICONS_DIR / icon_name
                if icon_path.exists():
                    return QIcon(str(icon_path))
                else:
                    return QIcon()  # Empty icon as fallback
            except Exception:
                return QIcon()  # Empty icon as fallback

        open_action = QAction(create_icon("open.png"), "Open", self)
        open_action.triggered.connect(self.Open)
        self.toolbar.addAction(open_action)
        
        self.toolbar.addSeparator()
        
        filter_action = QAction(create_icon("filter.png"), "Filter", self)
        filter_action.triggered.connect(self.OnFilter)
        self.toolbar.addAction(filter_action)
        
        self.toolbar.addSeparator()
        
        search_action = QAction(create_icon("search.png"), "Search", self)
        search_action.triggered.connect(self.OnSearch)
        self.toolbar.addAction(search_action)
        
        self.toolbar.addSeparator()
        
        time_action = QAction(create_icon("time.png"), "Time Window", self)
        time_action.triggered.connect(self.OnTime)
        self.toolbar.addAction(time_action)
        
        self.toolbar.addSeparator()
        
        reset_action = QAction(create_icon("reset.png"), "Reset", self)
        reset_action.triggered.connect(self.OnReset)
        self.toolbar.addAction(reset_action)
        
        self.toolbar.addSeparator()
        
        about_action = QAction(create_icon("about.png"), "About", self)
        about_action.triggered.connect(self.OnAbout)
        self.toolbar.addAction(about_action)
        
        self.toolbar.addSeparator()
        
        # Satellite monitoring actions
        satellite_id_action = QAction(create_icon("satellite.png"), "Satellite ID", self)
        satellite_id_action.triggered.connect(self.show_satellite_identification)
        self.toolbar.addAction(satellite_id_action)
        
        satellite_orbit_action = QAction(create_icon("orbit.png"), "Satellite Orbit", self)
        satellite_orbit_action.triggered.connect(self.show_satellite_orbit)
        self.toolbar.addAction(satellite_orbit_action)
        
        realtime_viz_action = QAction(create_icon("chart.png"), "Real-time Data", self)
        realtime_viz_action.triggered.connect(self.show_realtime_visualization)
        self.toolbar.addAction(realtime_viz_action)

        # Main Panel
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout()
        central_widget.setLayout(main_layout)

        # Create splitter for resizable panels
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Grid (Table) for log entries
        self.grid = QTableWidget()
        self.grid.setColumnCount(2)
        self.grid.setHorizontalHeaderLabels(["Timestamp", "Type ID"])
        self.grid.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.grid.cellClicked.connect(self.OnGridSelect)
        
        # Left panel for details
        left_panel = QWidget()
        left_layout = QVBoxLayout()
        left_panel.setLayout(left_layout)
        
        self.status_text = QLabel(
            "Welcome to MobileInsight 6.1.0 beta!\n\nMobileInsight is a Python 3 package for mobile network monitoring and analysis on the end device.")
        self.status_text.setWordWrap(True)
        
        self.details_text = QTreeWidget()
        self.details_text.setHeaderLabel("Details")
        
        left_layout.addWidget(self.status_text, 1)
        left_layout.addWidget(self.details_text, 3)
        
        # Add widgets to splitter
        splitter.addWidget(self.grid)
        splitter.addWidget(left_panel)
        splitter.setSizes([600, 400])  # Initial sizes
        
        main_layout.addWidget(splitter)
        
        # Set column widths
        self.grid.setColumnWidth(0, 200)
        self.grid.setColumnWidth(1, 300)
        
        # Status bar
        self.statusbar = QStatusBar()
        self.setStatusBar(self.statusbar)
        
        # Window properties
        self.setWindowTitle("MobileInsight")
        self.resize(1200, 800)
        self.show()

        self.data = None

        # Set up custom result handling
        self.result_timer = QTimer()
        self.result_timer.timeout.connect(self.check_results)
        self.result_timer.start(100)  # Check every 100ms
        self.pending_result = None

    def check_results(self) -> None:
        if self.pending_result is not None:
            self.OnResult(self.pending_result)
            self.pending_result = None

    def OnResult(self, event: Union[ResultEvent, List[Dict[str, Any]]]) -> None:
        if self.progressDialog:
            self.progressDialog.close()
            self.progressDialog = None

        data: List[Dict[str, Any]]
        if isinstance(event, ResultEvent):
            data = event.data
        else:
            data = event
            
        if data:
            self.statusbar.showMessage(f"Read {len(data)} logs")
            self.data = data
            self.data_view = self.data
            self.SetupGrid()

    def Open(self) -> None:
        file_dialog = QFileDialog()
        file_paths, _ = file_dialog.getOpenFileNames(
            self,
            "Open Log file",
            "",
            "log files (*.mi2log);;All files (*.*)")
        
        if file_paths:
            print(f'Selected {file_paths}')
            try:
                self.grid.clearContents()
                self.grid.setRowCount(0)

                t = Thread(target=self.openFile, args=(file_paths, self.selectedTypes))
                self.progressDialog = ProgressDialog(self)
                t.start()
                self.progressDialog.exec()

                if len(file_paths) == 1:
                    self.setWindowTitle(file_paths[0])
                else:
                    self.setWindowTitle(f"Multiple files in {os.path.dirname(file_paths[0])}")

            except Exception as e:
                print(f"Error while opening file: {e}")

    def OnFilter(self) -> None:
        types = list(self._log_analyzer.supported_types)
        checkboxDialog = MyMCD(self, "Filter", "", types)
        if checkboxDialog.exec() == QDialog.DialogCode.Accepted:
            selections = checkboxDialog.GetSelections()
            self.selectedTypes = [types[x] for x in selections]
            if self.data:
                self.data_view = [x for x in self.data if x["TypeID"] in self.selectedTypes]
                self.SetupGrid()

    def OnTime(self) -> None:
        timewindowDialog = TimeWindowDialog(self, self.min_time, self.max_time)
        if timewindowDialog.exec() == QDialog.DialogCode.Accepted:
            select_start = timewindowDialog.cur_start
            select_end = timewindowDialog.cur_end
            if self.data_view is not None:
                self.data_view = [
                    x for x in self.data_view if datetime.strptime(
                        x["Timestamp"],
                        '%Y-%m-%d  %H:%M:%S.%f') >= select_start and datetime.strptime(
                        x["Timestamp"],
                        '%Y-%m-%d  %H:%M:%S.%f') <= select_end]
                self.SetupGrid()

    def OnReset(self) -> None:
        if self.data:
            self.data_view = self.data
            self.SetupGrid()

    def openFile(self, Paths: List[str], selectedTypes: Optional[List[str]]) -> None:
        self._log_analyzer.AnalyzeFile(Paths, selectedTypes)

    def OnSearch(self) -> None:
        text, ok = QInputDialog.getText(self, "Search", "Search for:")
        if ok and text and self.data_view is not None:
            self.data_view = [x for x in self.data_view if text in x["Payload"]]
            self.SetupGrid()

    def OnAbout(self) -> None:
        about_text = (
                'MobileInsight GUI\n\n\n' +
                'Copyright (c) 2014-2025 MobileInsight Team\n\n' +
                'Developers:\n    Moustafa Alzantot,\n' +
                '    Priyanka Avinash Kachare,\n' +
                '    Michael Ivan,\n' +
                '    Yuanjie Li\n' +
                '    Yekai Dong')
        QMessageBox.information(self, "About MobileInsight GUI", about_text)

    def OnGridSelect(self, row: int, column: int) -> None:
        if self.data_view is not None and row < len(self.data_view):
            self.status_text.setText(
                f"Time Stamp : {self.data_view[row]['Timestamp']}    Type : {self.data_view[row]['TypeID']}")
            
            self.content = {}
            r = ET.fromstring(str(self.data_view[row]["Payload"]))
            print(r.tag)
            for child in r:
                k = child.get("key")
                if k is not None:
                    if child.get("type")=="list" and len(child)==0:
                        self.content[k]={}
                    elif child.get("type") == "list" and child[0].tag == "list":
                        list_content = self.parse_list(child, k)
                        self.content[k] = list_content
                    elif child.get("type") == "list" and child[0].tag == "msg":  # xml from wireshark
                        list_content = self.parse_msg(child)
                        self.content[k] = list_content
                    elif child.get("type")=="dict":
                        self.content[k]=self.parse_dict(child)
                    else:
                        self.content[k] = child.text
                    
            self.details_text.clear()
            root = QTreeWidgetItem(self.details_text)
            root.setText(0, 'payload')
            self.create_tree(self.content, root)
            self.details_text.expandAll()

    def parse_list(self, listroot: ET.Element, attrib_key: str) -> Optional[Dict[str, Any]]:
        '''
        convert list from .xml to standard dict
        :param listroot: XML element containing the list
        :param attrib_key: attribute key name
        :return: dict or None
        '''
        list_content: Dict[str, Any] = {}
        if len(listroot) == 0:
            return None
        listroot = listroot[0]  # <pair key="CA Combos" type="list">   <list>
        i = 0
        for xml_list in listroot:
            if xml_list.tag == "item" and xml_list.get("type") == "dict":  # The only subclass of list is dict
                dist_content = self.parse_dict(xml_list)
                key = xml_list.get("key")
                if key is None:
                    list_content[attrib_key + "[" + str(i) + "]"] = dist_content 
                    i += 1
                else:
                    list_content[key] = dist_content 
        return list_content

    def parse_dict(self, dictroot: ET.Element) -> Dict[str, Any]:
        '''
        convert dict from .xml to standard dict
        :param dictroot: XML element containing the dict
        :return: dict
        '''
        dictroot = dictroot[0]  # <item type="dict">  <dict>
        dict_content: Dict[str, Any] = {}
        for d in dictroot:
            k = d.get("key")
            if k is not None:
                if d.get("type") == "list":  # list in dict
                    list_content = self.parse_list(d, k)
                    dict_content[k] = list_content
                elif d.get("type") == "dict":
                    nested_dict_content = self.parse_dict(d)
                    dict_content[k] = nested_dict_content
                else:
                    dict_content[k] = d.text  # key-value
        return dict_content

    def split_key_value(self, input_str: str) -> tuple[str, str]:
        '''
        e.g. "a:b"->"a","b"
        :param input_str: string to split
        :return: tuple of key and value
        '''
        start = input_str.find(":")
        if start != -1:
            key = input_str[0:start]
            val = input_str[start+1:]
            return key, val
        else:
            return input_str, "none"
            
    def parse_msg(self, msgroot: ET.Element) -> Dict[str, Any]:
        '''
        parse xml file which is conveyed by wireshark
        :param msgroot: XML element containing the message
        :return: dict
        '''
        proto = msgroot.findall(".//proto")
        dict_msg: Dict[str, Any] = {}
        skip_context = ["geninfo", "frame", "user_dlt"]  # proto which is useless
        for p in proto:
            if (p.get("hide") != "yes" and p.get("name") not in skip_context):
                dict_msg.update(self.parse_msg_field(p))
            else:
                continue
        return dict_msg

    def parse_msg_field(self, msgroot: ET.Element) -> Dict[str, Any]:
        msg_dict: Dict[str, Any] = {}
        for field in msgroot:
            if field.get("hide") == "yes":
                continue
            elif len(field) != 0 and field.get("showname") is not None:
                k = field.get("showname")
                if k is not None:
                    k, _ = self.split_key_value(k)
                    val_dict = self.parse_msg_field(field)
                    if len(val_dict) == 0:
                        msg_dict[k] = "skip"
                    else:
                        msg_dict[k] = val_dict
            elif len(field) != 0:
                msg_dict.update(self.parse_msg_field(field))
            else:
                dict_msg = field.get("showname")
                if dict_msg is not None:
                    k, v = self.split_key_value(dict_msg)
                    msg_dict[k] = v
        return msg_dict

    def create_tree(self, payload_dict: Dict[str, Any], root: QTreeWidgetItem) -> None:
        for k, v in payload_dict.items():
            if isinstance(v, dict):
                subroot = QTreeWidgetItem(root)
                subroot.setText(0, str(k))
                self.create_tree(v, subroot)
            else:
                if v != "skip":
                    item = QTreeWidgetItem(root)
                    item.setText(0, f"{k}:{v}")
                else:
                    item = QTreeWidgetItem(root)
                    item.setText(0, str(k))

    def show_satellite_identification(self) -> None:
        """Show the satellite identification dialog."""
        if self.satellite_id_dialog is None:
            self.satellite_id_dialog = SatelliteIdentificationDialog(self)
        self.satellite_id_dialog.show()
        self.satellite_id_dialog.raise_()
        self.satellite_id_dialog.activateWindow()
    
    def show_satellite_orbit(self) -> None:
        """Show the satellite orbit and service dialog."""
        if self.satellite_orbit_dialog is None:
            self.satellite_orbit_dialog = SatelliteOrbitServiceDialog(self)
        self.satellite_orbit_dialog.show()
        self.satellite_orbit_dialog.raise_()
        self.satellite_orbit_dialog.activateWindow()
    
    def show_realtime_visualization(self) -> None:
        """Show the real-time data visualization dialog."""
        if self.realtime_viz_dialog is None:
            self.realtime_viz_dialog = RealTimeDataVisualizationDialog(self)
        self.realtime_viz_dialog.show()
        self.realtime_viz_dialog.raise_()
        self.realtime_viz_dialog.activateWindow()

    def closeEvent(self, a0) -> None:
        if a0:
            a0.accept()

    def OnReadComplete(self) -> None:
        # Instead of using wx events, we'll use a simple variable
        self.pending_result = ResultEvent(self._log_analyzer.msg_logs)

    def SetupGrid(self) -> None:
        if self.data_view is None:
            return
            
        self.min_time = datetime.strptime("3000 Jan 1", '%Y %b %d')
        self.max_time = datetime.strptime("1900 Jan 1", '%Y %b %d')

        n = len(self.data_view)
        
        # Set the number of rows
        self.grid.setRowCount(n)
        
        # Clear existing content
        self.grid.clearContents()
        
        # Set headers
        self.grid.setHorizontalHeaderLabels(["Timestamp", "Type ID"])
        
        for i in range(n):
            try:
                cur_time = datetime.strptime(
                    self.data_view[i]["Timestamp"],
                    '%Y-%m-%d  %H:%M:%S.%f')
            except Exception as e:
                cur_time = datetime.strptime(
                    self.data_view[i]["Timestamp"], '%Y-%m-%d  %H:%M:%S')
            self.min_time = min(self.min_time, cur_time)
            self.max_time = max(self.max_time, cur_time)
            
            # Set cell values
            timestamp_item = QTableWidgetItem(str(self.data_view[i]["Timestamp"]))
            timestamp_item.setFlags(timestamp_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.grid.setItem(i, 0, timestamp_item)
            
            typeid_item = QTableWidgetItem(str(self.data_view[i]["TypeID"]))
            typeid_item.setFlags(typeid_item.flags() & ~Qt.ItemFlag.ItemIsEditable)
            self.grid.setItem(i, 1, typeid_item)


def main() -> None:
    app = QApplication(sys.argv)
    # Set application/dialog icon from the icons directory if available
    try:
        icon_path = ICONS_DIR / "mobileinsight.png"
        if icon_path.exists():
            app.setWindowIcon(QIcon(str(icon_path)))
    except Exception:
        # Silently ignore icon errors
        pass

    window = WindowClass()
    # Ensure main window also uses the same icon
    try:
        window.setWindowIcon(app.windowIcon())
    except Exception:
        pass

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
