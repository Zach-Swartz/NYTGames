"""
Wordle Solver - Core Logic

This module contains all the constraint logic and analysis needed for the Wordle solver.
It handles:
- Loading valid words
- Computing constraints from guess feedback
- Filtering possible answers
- Analyzing and scoring guesses
"""

from collections import defaultdict, Counter
import math


# ==========================================
# WORD LOADING
# ==========================================

def load_words(filepath):
    """Load 5-letter words from a file"""
    with open(filepath, "r") as f:
        return [line.strip().lower() for line in f if len(line.strip()) == 5]


try:
    valid_guesses = load_words("valid-wordle-guesses.txt")
    valid_answers = load_words("valid-wordle-answers.txt")
    print(f"Loaded {len(valid_guesses)} guesses and {len(valid_answers)} answers.")
except FileNotFoundError as e:
    print(f"Warning: Could not load word lists: {e}")
    valid_guesses = []
    valid_answers = []


# ==========================================
# CONSTRAINT COMPUTATION
# ==========================================

def compute_constraints(guess_history):
    """
    Compute all constraints based on guess history.
    
    Args:
        guess_history: List of tuples (guess, feedback) where feedback is a 5-char string
                      with G (green), Y (yellow), or B (black) for each letter
    
    Returns:
        Tuple of (green_positions, yellow_positions, min_counts, max_counts, excluded_letters)
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
            min_counts[letter] = max(min_counts[letter], gy_count)
        
        # Now handle black letters
        for i, (letter, fb) in enumerate(zip(guess, feedback)):
            if fb == "B":
                gy_count = green_yellow_count[letter]
                
                if gy_count == 0:
                    # This letter doesn't appear as green/yellow in this guess
                    if min_counts[letter] == 0:
                        # Never seen this letter as green/yellow
                        max_counts[letter] = 0
                        excluded_letters.add(letter)
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


# ==========================================
# FEEDBACK GENERATION
# ==========================================

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


# ==========================================
# GUESS ANALYSIS (for backward compatibility)
# ==========================================

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
    
    This measures how many answers are eliminated on average.
    A high confidence means this guess will significantly narrow down the possibilities.
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


def analyze_guess(guess, possible_answers):
    """
    Analyze a guess in detail, returning multiple metrics.

    Returns:
        dict with keys: entropy, confidence, elimination_rate, best_case,
        worst_case, expected_remaining, is_answer, pattern_groups
    """
    if len(possible_answers) == 0:
        return None

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

    if total == 1:
        conf = 1.0
    else:
        expected_remaining = sum(
            (count / total) * count for count in pattern_groups.values()
        ) / total
        conf = 1.0 - (expected_remaining / total)

    best_case = min(pattern_groups.values())
    worst_case = max(pattern_groups.values())
    expected_remaining = sum(
        (count / total) * count for count in pattern_groups.values()
    ) / total
    elimination_rate = 1.0 - (expected_remaining / total)

    return {
        'entropy': entropy,
        'confidence': conf,
        'elimination_rate': elimination_rate,
        'best_case': best_case,
        'worst_case': worst_case,
        'expected_remaining': expected_remaining,
        'is_answer': guess in possible_answers,
        'pattern_groups': dict(pattern_groups),
    }


def get_best_guesses(possible_answers, guess_list=None, top_n=5):
    """
    Find the best guesses sorted by confidence (highest first).

    Args:
        possible_answers: List of possible remaining answers
        guess_list: List of guesses to consider. Defaults to possible_answers.
        top_n: Return top N guesses

    Returns:
        List of tuples: (guess, analysis_dict)
    """
    if not possible_answers:
        return []

    if guess_list is None:
        guess_list = possible_answers

    scored_guesses = []
    for guess in guess_list:
        analysis = analyze_guess(guess, possible_answers)
        if analysis:
            scored_guesses.append((guess, analysis))

    scored_guesses.sort(key=lambda x: x[1]['confidence'], reverse=True)
    return scored_guesses[:top_n]


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
