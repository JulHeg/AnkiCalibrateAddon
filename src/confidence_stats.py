import os
from typing import Optional

from aqt.qt import (
    QDialog,
    QVBoxLayout,
    QWebEngineView,
)
from aqt.deckchooser import DeckChooser
from aqt import mw
import aqt

import json
import math
import requests

def wald_interval_simple_50(k, n, eps = 0.02):
    """Returns a 50% Wald interval and clips to [eps, 1-eps]."""
    if n == 0:
        return (0.0, 1.0)
    
    p_hat = k / n
    z = 0.674 # For a 50% confidence level
    se = math.sqrt(p_hat * (1 - p_hat) / n)
    
    lower_bound = max(eps, p_hat - z * se)
    upper_bound = min(1 - eps, p_hat + z * se)
    
    return (lower_bound, upper_bound)

class ConfidenceStatsDialog(QDialog):
    def __init__(
        self, calibration_data_path
    ):
        super().__init__()

        self.calibration_data_path = calibration_data_path
        self.form = aqt.forms.stats.Ui_Dialog()
        self.deckArea = aqt.QWidget()

        # self.form.setupUi(self)
        self.deck_chooser = DeckChooser(
            mw,
            self.deckArea,
            on_deck_changed=self.on_deck_changed,
        )

        self.web_view = QWebEngineView()
        html_content = self.update_chart()
        self.web_view.setHtml(html_content)
        self.setMinimumWidth(800)
        self.setMinimumHeight(900)
        top_box = QVBoxLayout()
        self.setWindowTitle("Calibration Statistics")

        top_box.addWidget(self.web_view, stretch=20)  # Add the web view to the dialog
        top_box.addWidget(self.deckArea, stretch=1)
        self.setLayout(top_box)

    def on_deck_changed(self, deck_id: int) -> None:
        html_content = self.update_chart(deck_id=deck_id)
        self.web_view.setHtml(html_content)

    def update_chart(self, deck_id: Optional[int] = None) -> str:
        if not os.path.exists(self.calibration_data_path):
            return "Study some cards and quantify your confidence first to gather some data."

        with open(self.calibration_data_path, "r") as f:
            lines = f.readlines()

        if len(lines) == 0:
            return "Study some cards and quantify your confidence first to gather some data."

        answers = [json.loads(line.strip()) for line in lines if line != ""]

        brier_score = 0
        card_ids = set()

        if deck_id is not None:
            # Filter by deck and its subdecks. I don't know how to do it more idiomatic :()
            deck_name = mw.col.decks.get(deck_id)['name']
            answers = [answer for answer in answers if mw.col.decks.get(mw.col.get_card(answer["card_id"]).did)['name'].startswith(deck_name)]
        if len(answers) == 0:
            return ""

        for answer in answers:
            ground_truth = 1 if answer["has_guessed_correctly"] else 0
            brier_score += (answer["guessedProb"] / 100 - ground_truth) ** 2
            card_ids.add(answer["card_id"])
        brier_score /= len(answers)

        bucket_count = 10
        bucket_outcomes = {}
        for i in range(bucket_count):
            bucket_outcomes[i] = []

        total_correct = 0
        total_expected_correct = 0

        for answer in answers:
            bucket = int(answer["guessedProb"] / 10)
            bucket = min(bucket, bucket_count - 1)
            ground_truth = 1 if answer["has_guessed_correctly"] else 0
            bucket_outcomes[bucket].append(ground_truth)
            total_correct += ground_truth
            total_expected_correct += answer["guessedProb"] / 100
        
        average_correct = total_correct / len(answers)
        average_expected_correct = total_expected_correct / len(answers)

        bucket_averages = {}
        bucket_guess_count = {}
        bucket_correct_outcomes = {}
        bucket_wald_lower = {}
        bucket_wald_upper = {}

        for i in range(bucket_count):
            if len(bucket_outcomes[i]) == 0:
                bucket_averages[i] = 0.5
            else:
                bucket_averages[i] = sum(bucket_outcomes[i]) / len(bucket_outcomes[i])
            bucket_guess_count[i] = len(bucket_outcomes[i])
            bucket_correct_outcomes[i] = sum(bucket_outcomes[i])
            wald_lower, wald_upper = wald_interval_simple_50(bucket_correct_outcomes[i], bucket_guess_count[i])
            bucket_wald_lower[i] = wald_lower
            bucket_wald_upper[i] = wald_upper
            # bucket_string += f"Bucket {i / bucket_count:%} - {(i + 1) / bucket_count:%}: {bucket_averages[i]:.3f}\n"
        
        total_guesses = sum([bucket_guess_count[i] for i in range(bucket_count)])
        unique_cards = len(card_ids)

        # Metaculus' overconfidence score, see here for an explanation: https://manifold.markets/1941159478/why-does-metaculus-calculate-their
        # Modified to only look at forecats in (confidence_score_cutoff, 1-confidence_score_cutoff) because knowing you definietly don't know a card is not really impressive in this case
        config = mw.addonManager.getConfig(__name__)
        confidence_score_cutoff = config['confidence_score_cutoff']
        sum_1 = 0
        sum_2 = 0
        for answer in answers:
            probability_of_correct = answer["guessedProb"] / 100 if answer["has_guessed_correctly"] else 1 - answer["guessedProb"] / 100 # p(r_i) in the above link
            if probability_of_correct >= confidence_score_cutoff and 1 - probability_of_correct >= confidence_score_cutoff:
                sum_1 += (probability_of_correct - 1) * (probability_of_correct - 1/2)
                sum_2 += (probability_of_correct - 1/2) ** 2
        
        if sum_2 == 0:
            overconfidence_score = 0
        else:
            overconfidence_score = sum_1 / sum_2

        overconfidence_explanation = f"Overconfidence Score: {overconfidence_score:.2%}. You are "

        if abs(overconfidence_score) < 0.1:
            overconfidence_explanation += "approximately well calibrated!"
        else:
            if abs(overconfidence_score) < 0.2:
                overconfidence_explanation += "slightly "
            if overconfidence_score < 0:
                overconfidence_explanation += "underconfident. Try to be more sure of yourself!"
            else:
                overconfidence_explanation += "overconfident. Try to be less sure of yourself!"
        


        
        
        dir_path = os.path.dirname(os.path.realpath(__file__))
        chart_html_path = os.path.join(dir_path, "web", "chart.html")
        d3_path = os.path.join(dir_path, "web", "d3_7.js")
        with open(chart_html_path, "r") as f:
            html_content = f.read()
            # web_view.load(QUrl.fromLocalFile(html_text))

        # Beautiful dependency management to ensure d3 is actually there. It's downloaded in the bundling step for the .ankiaddon version
        if os.path.exists(d3_path):
            with open(d3_path, "r") as f:
                d3_js = f.read()
        else:
            URL = "https://cdn.jsdelivr.net/npm/d3@7"
            r = requests.get(URL)
            with open(d3_path, "w") as f:
                f.write(r.text)
            with open(d3_path, "r") as f:
                d3_js = f.read()
        
        values = {
            "overconfidence": overconfidence_score,
            "averages": list(bucket_averages.values()),
            "lower_ci": list(bucket_wald_lower.values()),
            "upper_ci": list(bucket_wald_upper.values()),
            "average_correct": f"{average_correct:.1%}",
            "average_expected_correct": f"{average_expected_correct:.1%}",
            "brier_score": f"{brier_score:.1%}",
            "total_guesses": total_guesses,
            "unique_cards": unique_cards,
            "d3_js": d3_js,
            "overconfidence_explanation": overconfidence_explanation
        }

        for k, v in values.items():
            html_content = html_content.replace("{" + k + "}", str(v))
            
        return html_content