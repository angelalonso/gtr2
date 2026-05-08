#!/usr/bin/env python3
"""
Helper for waiting on Qt signals with timeout
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from PyQt5.QtCore import QTimer, QEventLoop


class WaitForSignal:
    """Helper to wait for Qt signals with timeout"""
    
    def __init__(self, signal, timeout_ms=5000):
        self.signal = signal
        self.timeout_ms = timeout_ms
        self.received = False
        self.result = None
        
    def wait(self):
        loop = QEventLoop()
        
        def on_signal(*args):
            self.received = True
            self.result = args if len(args) > 1 else (args[0] if args else None)
            loop.quit()
        
        self.signal.connect(on_signal)
        QTimer.singleShot(self.timeout_ms, loop.quit)
        loop.exec_()
        self.signal.disconnect(on_signal)
        
        return self.received
