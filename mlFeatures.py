from collections import Counter
import math

def extract_features(guess, possible_answers):
    """
    Convert (guess, possible_answers) into numeric ML features.
    Returns a list of floats.
    """

    total = len(possible_answers)

    # Safety check
    if total == 0:
        return [0]*6

    # Letter frequency across remaining answers
    letter_freq = Counter()
    for word in possible_answers:
        letter_freq.update(set(word))

    # Normalize frequencies
    for k in letter_freq:
        letter_freq[k] /= total

    # Features
    unique_letters = len(set(guess))
    duplicate_letters = 5 - unique_letters

    avg_letter_freq = sum(letter_freq.get(c, 0) for c in set(guess)) / unique_letters

    overlap = sum(
        1 for w in possible_answers if any(c in w for c in guess)
    ) / total

    # Entropy (reuse logic conceptually)
    entropy = 0.0
    pattern_counts = {}
    from solver import generate_feedback
    for answer in possible_answers:
        pattern = generate_feedback(guess, answer)
        pattern_counts[pattern] = pattern_counts.get(pattern, 0) + 1

    for count in pattern_counts.values():
        p = count / total
        entropy -= p * math.log2(p)

    return [
        total,              # remaining answers
        entropy,            # info gain
        unique_letters,     # coverage
        duplicate_letters,  # redundancy
        avg_letter_freq,    # common letters
        overlap,            # relevance
    ]