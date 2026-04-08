from collections import defaultdict, Counter
import math

def load_words(filepath):
    """Load 5-letter words from a file"""
    with open(filepath, "r") as f:
        return [line.strip().lower() for line in f if len(line.strip()) == 5]

valid_guesses = load_words("valid-wordle-guesses.txt")
valid_answers = load_words("valid-wordle-answers.txt")

print(f"Loaded {len(valid_guesses)} guesses and {len(valid_answers)} answers.")


# -------------------------------
# FIXED: Robust constraint solver
# -------------------------------

def compute_constraints(guess_history):
    """
    Fixed constraint computation that properly handles:
    1. Letters that appear in multiple guesses
    2. Mixed feedback (green + yellow + black for same letter)
    3. Contradictory constraints
    """
    green_positions = [None] * 5          # letters in exact positions
    yellow_positions = defaultdict(set)   # letter -> indices it cannot be
    min_counts = defaultdict(int)         # letter -> min occurrences needed
    max_counts = defaultdict(lambda: 5)   # letter -> max occurrences allowed
    excluded_letters = set()              # letters definitely not in answer

    for guess, feedback in guess_history:
        # Count how many times each letter appears with G or Y feedback
        green_yellow_count = Counter()
        
        for i, (letter, fb) in enumerate(zip(guess, feedback)):
            if fb == "G":
                green_positions[i] = letter
                green_yellow_count[letter] += 1
            elif fb == "Y":
                yellow_positions[letter].add(i)
                green_yellow_count[letter] += 1
        
        # Now update min_counts based on green/yellow feedback
        for letter, gy_count in green_yellow_count.items():
            # A letter marked as yellow or green must appear at least gy_count times
            # (since each marking corresponds to one instance of the letter)
            min_counts[letter] = max(min_counts[letter], gy_count)
        
        # Now handle black letters
        for i, (letter, fb) in enumerate(zip(guess, feedback)):
            if fb == "B":
                gy_count = green_yellow_count[letter]
                
                if gy_count == 0:
                    # This letter doesn't appear as green/yellow in this guess
                    # It might appear in previous guesses, so we need to check
                    # If it's purely black here with no green/yellow history,
                    # then max_counts[letter] should be 0
                    if min_counts[letter] == 0:
                        # Never seen this letter as green/yellow
                        max_counts[letter] = 0
                        excluded_letters.add(letter)
                    # else: letter was green/yellow in a previous guess,
                    # so max_counts already set correctly
                else:
                    # This letter appears green/yellow elsewhere in this guess
                    # So the max count is exactly the green/yellow count
                    max_counts[letter] = min(max_counts[letter], gy_count)
    
    return green_positions, yellow_positions, min_counts, max_counts, excluded_letters


def word_matches(word, green, yellow, min_counts, max_counts, excluded):
    """
    Check if a word matches all constraints.
    
    Args:
        word: the candidate word
        green: list of required letters at each position (None if unconstrained)
        yellow: dict mapping letter -> set of positions it cannot be
        min_counts: dict mapping letter -> minimum occurrences
        max_counts: dict mapping letter -> maximum occurrences
        excluded: set of letters that must not appear
    
    Returns:
        True if word satisfies all constraints, False otherwise
    """
    wc = Counter(word)
    
    # Check excluded letters
    for letter in excluded:
        if letter in word:
            return False
    
    # Check green positions
    for i, letter in enumerate(green):
        if letter is not None and word[i] != letter:
            return False
    
    # Check yellow positions (letter in word but not at these positions)
    for letter, bad_positions in yellow.items():
        if letter not in word:
            return False
        for pos in bad_positions:
            if word[pos] == letter:
                return False
    
    # Check min/max counts
    for letter, min_count in min_counts.items():
        if wc[letter] < min_count:
            return False
    
    for letter, max_count in max_counts.items():
        if wc[letter] > max_count:
            return False
    
    return True


def filter_possible_answers(possible_words, guess_history):
    """Filter words based on all constraints from guess history"""
    green, yellow, min_counts, max_counts, excluded = compute_constraints(guess_history)
    return [w for w in possible_words if word_matches(w, green, yellow, min_counts, max_counts, excluded)]


# -------------------------------
# Guess scoring (entropy)
# -------------------------------

def generate_feedback(guess, answer):
    """
    Generate feedback for a guess against an answer.
    
    Feedback codes:
    - 'G': letter is green (correct position)
    - 'Y': letter is yellow (in word, wrong position)
    - 'B': letter is black (not in word)
    
    This implements Wordle's actual logic:
    - Mark all correct positions first
    - Then mark yellows, being careful with duplicates
    """
    feedback = ["B"] * 5
    answer_letters = list(answer)

    # First pass: mark all greens
    for i in range(5):
        if guess[i] == answer[i]:
            feedback[i] = "G"
            answer_letters[i] = None

    # Second pass: mark yellows
    for i in range(5):
        if feedback[i] == "B" and guess[i] in answer_letters:
            feedback[i] = "Y"
            # Remove this letter from answer_letters so we don't double-count
            answer_letters[answer_letters.index(guess[i])] = None

    return "".join(feedback)


def score_guess(guess, possible_answers):
    """
    Calculate entropy of a guess.
    
    Higher entropy = guess splits answer space more evenly = better guess
    """
    if len(possible_answers) == 0:
        return 0.0
    
    pattern_groups = defaultdict(int)
    for answer in possible_answers:
        pattern = generate_feedback(guess, answer)
        pattern_groups[pattern] += 1
    
    total = len(possible_answers)
    entropy = 0.0
    for count in pattern_groups.values():
        if count > 0:
            probability = count / total
            entropy -= probability * math.log2(probability)
    
    return entropy


def confidence_score(guess, possible_answers):
    """
    Calculate confidence score for a guess (0 to 1).
    
    Higher score = more likely to narrow down the answer significantly
    
    Score is based on: how many words would be eliminated in the worst case?
    Perfect score (1.0) = any outcome eliminates all but one word
    Worst score (0.0) = no progress made
    """
    if len(possible_answers) == 0:
        return 0.0
    
    if len(possible_answers) == 1:
        return 1.0  # If only one word left, confidence is perfect
    
    pattern_groups = defaultdict(int)
    for answer in possible_answers:
        pattern = generate_feedback(guess, answer)
        pattern_groups[pattern] += 1
    
    total = len(possible_answers)
    
    # Calculate expected number of remaining candidates
    # after this guess across all possible outcomes
    expected_remaining = sum(
        (count / total) * count for count in pattern_groups.values()
    ) / total
    
    # Confidence: 1 - (expected remaining / total possible)
    confidence = 1.0 - (expected_remaining / total)
    
    return confidence


def best_guess(possible_answers, all_guesses):
    """
    Find the guess with highest entropy from the available guess list.
    
    Returns:
        (best_word, entropy_score)
    """
    if len(possible_answers) == 0:
        return None, 0.0
    
    # If only 1-2 words left, just return the first one
    if len(possible_answers) <= 2:
        return possible_answers[0], 1.0
    
    best_word = None
    best_score = -1
    
    for guess in all_guesses:
        score = score_guess(guess, possible_answers)
        if score > best_score:
            best_score = score
            best_word = guess
    
    return best_word, best_score