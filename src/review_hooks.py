from aqt.reviewer import Reviewer
import json
import datetime
import os
from aqt import gui_hooks, mw
from aqt.utils import tr
from aqt.theme import theme_manager

dir_path = os.path.dirname(os.path.realpath(__file__))
os.makedirs(os.path.join(dir_path, "user_files"), exist_ok=True)
calibration_data_path = os.path.join(dir_path, "user_files", "calibration_data.txt")

# Configuration setup
config = mw.addonManager.getConfig(__name__)

def _showAnswerButton(self) -> None:
    slider_only = config['slider_only']
    default_percentage = config['default_percentage']

    is_dark_mode = theme_manager.night_mode

    # Slider styling for both modes
    background_color = "#333" if is_dark_mode else "#f7f7f7"
    text_color = "#ccc" if is_dark_mode else "#333"
    slider_background = "#555" if is_dark_mode else "#ddd"
    slider_track = "#aaa" if is_dark_mode else "#555"

    slider_html = f"""
    <div style="width: 300px; margin: 20px auto; padding: 10px; background-color: {background_color}; border-radius: 10px; box-shadow: 0 4px 8px rgba(0, 0, 0, 0.1);">
        <input type="range" min="0" max="100" value="{default_percentage}" class="slider" id="confidenceSlider" 
        oninput="document.getElementById('sliderValue').textContent = this.value + '%';" onchange='pycmd("ans");' 
        style="width: 100%; height: 8px; -webkit-appearance: none; appearance: none; background: {slider_background}; 
        outline: none; border-radius: 5px; cursor: pointer;">
        
        <div style="display: flex; justify-content: space-between; margin-top: 5px; font-size: 12px; color: {text_color};">
            <span>0%</span>
            <span>25%</span>
            <span>50%</span>
            <span>75%</span>
            <span>100%</span>
        </div>

        <div style="text-align: center; margin-top: 10px; font-size: 16px; font-weight: bold; color: {text_color};">
            <span id="sliderValue">{default_percentage}%</span>
        </div>
    </div>
    """

    if slider_only:
        middle = f"<table cellpadding=0><tr><td class=stat2 align=center>{slider_html}</td></tr></table>"
    else:
        button_html = """
        <button title="{}" id="ansbut" onclick='pycmd("ans");'>{}<span class=stattxt>{}</span></button>""".format(
            tr.actions_shortcut_key(val=tr.studying_space()),
            tr.studying_show_answer(),
            self._remaining(),
        )
        
        middle = (
            f"<table cellpadding=0><tr><td class=stat2 align=center>{slider_html}</td></tr><tr><td class=stat2 align=center>{button_html}</td></tr></table>"
        )

    if self.card.should_show_timer():
        maxTime = self.card.time_limit() / 1000
    else:
        maxTime = 0
    self.bottom.web.eval("showQuestion(%s,%d);" % (json.dumps(middle), maxTime))


def _onConfidence(self, val: None) -> None:
    self.guessedProb = val or ""
    self._showAnswer()

def _onTypedAnswer(self, val: None) -> None:
    self.typedAnswer = val or ""
    self.bottom.web.evalWithCallback('(function() { return document.getElementById("confidenceSlider").value; })()', self._onGuessedProb)


def review_Hook(reviewer, card, ease):
    if hasattr(reviewer, 'guessedProb'):
        guessed_correctly = ease >= 2
        data_to_save = {
            'guessedProb': int(reviewer.guessedProb),
            'ease': ease,
            'has_guessed_correctly': guessed_correctly,
            'timestamp': datetime.datetime.now().timestamp(),
            'card_id': card.id
        }
        with open(calibration_data_path, "a+") as f:
            f.write(json.dumps(data_to_save) + "\n")

def setup_review_hooks():
    Reviewer._showAnswerButton = _showAnswerButton
    Reviewer._onGuessedProb = _onConfidence
    Reviewer._onTypedAnswer = _onTypedAnswer
    gui_hooks.reviewer_did_answer_card.append(review_Hook)
