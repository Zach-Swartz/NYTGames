# NYTGames
A repository containing work associated with solving various NYT games.

# How It Works
Each time you enter a guess and its feedback, the solver:

1. Parses your feedback into constraints (green/yellow/black)
2. Filters the full answer list down to only words that are still possible
3. Runs each remaining candidate through the ML model to predict how well it eliminates answers
4. Suggests the highest-ranked word as your next guess

The ML model is a Random Forest trained to predict elimination_rate (the fraction of remaining answers a guess is expected to eliminate) using features like entropy, letter frequency, and unique letter count.

# Project Structure
.
├── app.py                      # Streamlit UI
├── solver.py                   # Core logic, takes care of constraints and filtering
├── mlFeatures.py               # Feature extraction for the ML model
├── train_guess_ranker.py       # Script to (re)train the ML model
├── guess_ranker.pkl            # Pre-trained Random Forest model
├── valid-wordle-guesses.txt    # All valid 5-letter Wordle guesses
└── valid-wordle-answers.txt    # All valid Wordle answers

# Setup
1. Requires Python 3.8+
2. Install dependencies:
pip install streamlit scikit-learn joblib python-dotenv 
3. Run the app:
streamlit run app.py
4. If you want to retrain the model (like with more games for better accuracy) run:
python trainGuessRanker.py
