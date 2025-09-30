#!/usr/bin/env python3
"""
Simple test script to verify WebEngine functionality
"""

import sys
from PyQt6.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QWidget
from PyQt6.QtCore import QUrl

# Try to import WebEngine
try:
    from PyQt6.QtWebEngineWidgets import QWebEngineView
    from PyQt6.QtWebEngineCore import QWebEngineSettings
    WEB_ENGINE_AVAILABLE = True
    print("✓ WebEngine is available")
except ImportError as e:
    WEB_ENGINE_AVAILABLE = False
    print(f"✗ WebEngine not available: {e}")

class TestWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("WebEngine Test")
        self.setGeometry(100, 100, 800, 600)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        if WEB_ENGINE_AVAILABLE:
            # Create WebEngine view
            self.web_view = QWebEngineView()
            
            # Configure settings
            try:
                settings = self.web_view.settings()
                if settings:
                    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalContentCanAccessRemoteUrls, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.JavascriptEnabled, True)
                    settings.setAttribute(QWebEngineSettings.WebAttribute.LocalStorageEnabled, True)
                    print("✓ WebEngine settings configured")
            except Exception as e:
                print(f"⚠ WebEngine settings error: {e}")
            
            # Connect signals for debugging
            self.web_view.loadStarted.connect(lambda: print("Load started"))
            self.web_view.loadProgress.connect(lambda progress: print(f"Load progress: {progress}%"))
            self.web_view.loadFinished.connect(lambda success: print(f"Load finished: {success}"))
            
            # Test with simple HTML first
            simple_html = """
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="utf-8">
                <title>Test</title>
                <style>
                    body { font-family: Arial, sans-serif; padding: 20px; }
                    .box { background: #e8f4f8; padding: 20px; border-radius: 5px; margin: 10px 0; }
                </style>
            </head>
            <body>
                <h1>WebEngine Test</h1>
                <div class="box">
                    <p>If you can see this, WebEngine is working!</p>
                    <p>Time: <span id="time"></span></p>
                </div>
                <script>
                    console.log('JavaScript is working!');
                    document.getElementById('time').textContent = new Date().toLocaleTimeString();
                </script>
            </body>
            </html>
            """
            
            layout.addWidget(self.web_view)
            self.web_view.setHtml(simple_html)
            print("✓ Simple HTML loaded")
            
        else:
            from PyQt6.QtWidgets import QLabel
            label = QLabel("WebEngine is not available. Cannot test web content.")
            layout.addWidget(label)

def main():
    app = QApplication(sys.argv)
    
    print("Testing WebEngine functionality...")
    print(f"Qt platform: {app.platformName()}")
    
    window = TestWindow()
    window.show()
    
    return app.exec()

if __name__ == "__main__":
    sys.exit(main())