import random
import joblib
from sklearn.ensemble import RandomForestRegressor
from solver import valid_answers, valid_guesses, filter_possible_answers, analyze_guess
from mlFeatures import extract_features

X = []
y = []

NUM_GAMES = 500  # increase to 2000+ if you want

for _ in range(NUM_GAMES):
    answer = random.choice(valid_answers)
    guess_history = []
    possible = valid_answers.copy()

    for _ in range(6):
        # sample guesses instead of brute-forcing everything
        sampled_guesses = random.sample(valid_guesses, 30)

        for guess in sampled_guesses:
            analysis = analyze_guess(guess, possible)
            if analysis is None:
                continue

            features = extract_features(guess, possible)
            X.append(features)
            y.append(analysis["elimination_rate"])

        # play a random guess to move game forward
        guess = random.choice(sampled_guesses)
        feedback = __import__("solver").generate_feedback(guess, answer)
        guess_history.append((guess, feedback))
        possible = filter_possible_answers(possible, guess_history)

        if feedback == "GGGGG":
            break

print(f"Training samples: {len(X)}")

model = RandomForestRegressor(
    n_estimators=100,
    max_depth=10,
    random_state=42
)
model.fit(X, y)

joblib.dump(model, "guess_ranker.pkl")
print("Model saved as guess_ranker.pkl")