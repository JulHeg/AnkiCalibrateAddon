from aqt import QAction, mw
from aqt.utils import qconnect
import os

from .review_hooks import setup_review_hooks, calibration_data_path
from .confidence_stats import ConfidenceStatsDialog

# Replace the "Show Answer" button with a slider
setup_review_hooks()

# Add the Calibration window to the toolbar to show the calibration chart
def printScores():
    dialog = ConfidenceStatsDialog(calibration_data_path=calibration_data_path)
    dialog.exec()

# Add the Calibration action to the Tools menu
action = QAction("Calibration", mw)
qconnect(action.triggered, printScores)
mw.form.menuTools.addAction(action)