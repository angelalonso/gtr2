#!/usr/bin/env python3
"""
Unit tests for GUI dialogs including ManualLapTimeDialog
"""

import sys
from pathlib import Path

# Add parent directory to path so we can import application modules
sys.path.insert(0, str(Path(__file__).parent.parent))

import unittest
from PyQt5.QtWidgets import QApplication, QDialog, QPushButton
from PyQt5.QtCore import Qt
from PyQt5.QtTest import QTest

from test_base import BaseTestCase
from gui_common_dialogs import ManualLapTimeDialog, ManualEditDialog


class TestManualLapTimeDialog(BaseTestCase):
    """Test ManualLapTimeDialog functionality"""
    
    def setUp(self):
        super().setUp()
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
    
    def test_dialog_creation_with_current_time(self):
        """Test dialog creation with existing time"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        
        self.assertEqual(dialog.session_type, "qual")
        self.assertEqual(dialog.current_time, 95.5)
        self.assertAlmostEqual(dialog.time_spin.value(), 95.5)
        dialog.close()
    
    def test_dialog_creation_without_current_time(self):
        """Test dialog creation without existing time"""
        dialog = ManualLapTimeDialog(None, "race", None)
        
        self.assertEqual(dialog.session_type, "race")
        self.assertIsNone(dialog.current_time)
        self.assertEqual(dialog.time_spin.value(), 90.0)
        dialog.close()
    
    def test_enter_key_accepts_dialog(self):
        """Test that pressing Enter key accepts (saves) the dialog"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        dialog.time_spin.setValue(88.0)
        
        QTest.keyPress(dialog, Qt.Key_Return)
        
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.new_time, 88.0)
        dialog.close()
    
    def test_enter_key_on_numpad_accepts_dialog(self):
        """Test that numpad Enter key accepts the dialog"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        dialog.time_spin.setValue(88.0)
        
        QTest.keyPress(dialog, Qt.Key_Enter)
        
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.new_time, 88.0)
        dialog.close()
    
    def test_escape_key_rejects_dialog(self):
        """Test that Escape key rejects (cancels) the dialog"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        original_value = dialog.time_spin.value()
        
        dialog.time_spin.setValue(88.0)
        
        QTest.keyPress(dialog, Qt.Key_Escape)
        
        self.assertEqual(dialog.result(), QDialog.Rejected)
        self.assertIsNone(dialog.new_time)
        dialog.close()
    
    def test_apply_button_has_default_property(self):
        """Test that Apply button is the default button (Enter triggers it)"""
        dialog = ManualLapTimeDialog(None, "qual", 95.5)
        
        apply_button = None
        for child in dialog.findChildren(QPushButton):
            if child.text() == "Apply":
                apply_button = child
                break
        
        self.assertIsNotNone(apply_button)
        self.assertTrue(apply_button.isDefault())
        dialog.close()
    
    def test_accept_saves_new_time(self):
        """Test that accept() saves the current spinbox value"""
        dialog = ManualLapTimeDialog(None, "race", 100.0)
        dialog.time_spin.setValue(92.5)
        
        dialog.accept()
        
        self.assertEqual(dialog.new_time, 92.5)
        dialog.close()
    
    def test_reject_does_not_save_time(self):
        """Test that reject() does not save a new time"""
        dialog = ManualLapTimeDialog(None, "race", 100.0)
        dialog.time_spin.setValue(92.5)
        
        dialog.reject()
        
        self.assertIsNone(dialog.new_time)
        dialog.close()


class TestManualEditDialog(BaseTestCase):
    """Test ManualEditDialog functionality"""
    
    def setUp(self):
        super().setUp()
        self.app = QApplication.instance()
        if self.app is None:
            self.app = QApplication([])
    
    def test_dialog_creation(self):
        """Test dialog creation with ratio name and current value"""
        dialog = ManualEditDialog(None, "QualRatio", 1.234567, None, 0.5, 1.5)
        
        self.assertEqual(dialog.ratio_name, "QualRatio")
        self.assertAlmostEqual(dialog.current_ratio, 1.234567)
        self.assertAlmostEqual(dialog.ratio_spin.value(), 1.234567)
        self.assertEqual(dialog.ratio_spin.minimum(), 0.5)
        self.assertEqual(dialog.ratio_spin.maximum(), 1.5)
        dialog.close()
    
    def test_enter_key_accepts_dialog(self):
        """Test that pressing Enter key accepts the dialog"""
        dialog = ManualEditDialog(None, "QualRatio", 1.0, None, 0.5, 1.5)
        dialog.ratio_spin.setValue(1.2)
        
        QTest.keyPress(dialog, Qt.Key_Return)
        
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.new_ratio, 1.2)
        dialog.close()
    
    def test_enter_key_on_numpad_accepts_dialog(self):
        """Test that numpad Enter key accepts the dialog"""
        dialog = ManualEditDialog(None, "QualRatio", 1.0, None, 0.5, 1.5)
        dialog.ratio_spin.setValue(1.2)
        
        QTest.keyPress(dialog, Qt.Key_Enter)
        
        self.assertEqual(dialog.result(), QDialog.Accepted)
        self.assertEqual(dialog.new_ratio, 1.2)
        dialog.close()
    
    def test_escape_key_rejects_dialog(self):
        """Test that Escape key rejects the dialog"""
        dialog = ManualEditDialog(None, "QualRatio", 1.0, None, 0.5, 1.5)
        dialog.ratio_spin.setValue(1.2)
        
        QTest.keyPress(dialog, Qt.Key_Escape)
        
        self.assertEqual(dialog.result(), QDialog.Rejected)
        self.assertIsNone(dialog.new_ratio)
        dialog.close()
    
    def test_apply_button_has_default_property(self):
        """Test that Apply button is the default button"""
        dialog = ManualEditDialog(None, "QualRatio", 1.0, None, 0.5, 1.5)
        
        apply_button = None
        for child in dialog.findChildren(QPushButton):
            if child.text() == "Apply":
                apply_button = child
                break
        
        self.assertIsNotNone(apply_button)
        self.assertTrue(apply_button.isDefault())
        dialog.close()
    
    def test_accept_saves_new_ratio(self):
        """Test that accept() saves the current spinbox value"""
        dialog = ManualEditDialog(None, "QualRatio", 1.0, None, 0.5, 1.5)
        dialog.ratio_spin.setValue(0.8)
        
        dialog.accept()
        
        self.assertEqual(dialog.new_ratio, 0.8)
        dialog.close()
    
    def test_reject_does_not_save_ratio(self):
        """Test that reject() does not save a new ratio"""
        dialog = ManualEditDialog(None, "QualRatio", 1.0, None, 0.5, 1.5)
        dialog.ratio_spin.setValue(0.8)
        
        dialog.reject()
        
        self.assertIsNone(dialog.new_ratio)
        dialog.close()
    
    def test_range_enforcement(self):
        """Test that spinbox enforces min/max range"""
        dialog = ManualEditDialog(None, "QualRatio", 1.0, None, 0.5, 1.5)
        
        dialog.ratio_spin.setValue(0.3)
        self.assertGreaterEqual(dialog.ratio_spin.value(), 0.5)
        
        dialog.ratio_spin.setValue(2.0)
        self.assertLessEqual(dialog.ratio_spin.value(), 1.5)
        dialog.close()


def run_dialog_tests():
    """Run all dialog tests"""
    print("\n" + "=" * 60)
    print("GUI DIALOG TESTS")
    print("=" * 60)
    
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    suite.addTests(loader.loadTestsFromTestCase(TestManualLapTimeDialog))
    suite.addTests(loader.loadTestsFromTestCase(TestManualEditDialog))
    
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    return result


if __name__ == "__main__":
    run_dialog_tests()
