#!/usr/bin/env python3
"""
Entry point for Dyn AI Data Manager
"""

import sys
from PyQt5.QtWidgets import QApplication

from gui_data_manager import DynAIDataManager
from gui_common import setup_dark_theme


def main():
    app = QApplication(sys.argv)
    setup_dark_theme(app)
    
    window = DynAIDataManager()
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
