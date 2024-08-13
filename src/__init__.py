from aqt import QAction, mw
from aqt.utils import qconnect
from aqt import gui_hooks
import os

from .review_hooks import setup_review_hooks, calibration_data_path
from .confidence_stats import ConfidenceStatsDialog

# Ensure the user files directory exists
os.makedirs(os.path.join(os.path.dirname(os.path.realpath(__file__)), "user_files"), exist_ok=True)

# Setup the review hooks and logic
setup_review_hooks()

# Add a window to the toolbar to show the calibration chart
def printScores():
    dialog = ConfidenceStatsDialog(calibration_data_path=calibration_data_path)
    dialog.exec()

# Add the Calibration action to the Tools menu
action = QAction("Calibration", mw)
qconnect(action.triggered, printScores)
mw.form.menuTools.addAction(action)