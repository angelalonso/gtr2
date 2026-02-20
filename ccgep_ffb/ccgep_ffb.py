#!/usr/bin/env python3
"""
FFB Simulator - Stiff Parking FFB Visualization
Main entry point for the application
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QFont
from ffb_simulator_gui import FFBSimulatorWidget


def main():
    app = QApplication(sys.argv)
    app.setStyle('Fusion')
    
    # Dark theme
    app.setStyleSheet("""
        QMainWindow, QDialog {
            background-color: #2b2b2b;
        }
        QGroupBox {
            color: #ffffff;
            border: 1px solid #555;
            border-radius: 5px;
            margin-top: 1ex;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
            color: #4CAF50;
        }
        QLabel {
            color: #ffffff;
        }
        QCheckBox {
            color: #ffffff;
            font-size: 12px;
        }
        QStatusBar {
            color: #ffffff;
            background-color: #3c3c3c;
        }
    """)
    
    window = FFBSimulatorWidget()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
