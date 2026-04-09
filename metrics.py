"""
Enhanced metrics for the Wordle solver

The original "confidence score" was misleading because it measures
"expected remaining words" rather than "how well balanced is the guess".

This module provides better metrics:
1. ENTROPY - How evenly the guess splits the answer space (BEST for selection)
2. ELIMINATION RATE - How many answers are eliminated on average
3. BEST CASE / WORST CASE - Range of outcomes
"""

from collections import defaultdict, Counter
import math


def generate_feedback(guess, answer):
    """Generate feedback for a guess against an answer."""
    feedback = ["B"] * 5
    answer_letters = list(answer)
    for i in range(5):
        if guess[i] == answer[i]:
            feedback[i] = "G"
            answer_letters[i] = None
    for i in range(5):
        if feedback[i] == "B" and guess[i] in answer_letters:
            feedback[i] = "Y"
            answer_letters[answer_letters.index(guess[i])] = None
    return "".join(feedback)


def analyze_guess(guess, possible_answers):
    """
    Analyze a guess in detail, returning multiple metrics.
    
    Returns:
        dict with keys:
        - entropy: Information gain (higher = better, max ~3.3 for 10 answers)
        - elimination_rate: % of answers eliminated on average
        - best_case: Fewest answers remaining in best outcome
        - worst_case: Most answers remaining in worst outcome
        - expected_remaining: Average answers remaining
        - is_answer: Whether the guess is one of the possible answers
        - pattern_groups: Dict mapping patterns to counts
    """
    if len(possible_answers) == 0:
        return None
    
    pattern_groups = defaultdict(int)
    for answer in possible_answers:
        pattern = generate_feedback(guess, answer)
        pattern_groups[pattern] += 1
    
    total = len(possible_answers)
    
    # Calculate entropy
    entropy = 0.0
    for count in pattern_groups.values():
        if count > 0:
            probability = count / total
            entropy -= probability * math.log2(probability)
    
    # Calculate metrics
    best_case = min(pattern_groups.values())
    worst_case = max(pattern_groups.values())
    expected_remaining = sum(
        (count / total) * count for count in pattern_groups.values()
    ) / total
    
    elimination_rate = 1.0 - (expected_remaining / total)
    
    is_answer = guess in possible_answers
    
    return {
        'entropy': entropy,
        'elimination_rate': elimination_rate,
        'best_case': best_case,
        'worst_case': worst_case,
        'expected_remaining': expected_remaining,
        'is_answer': is_answer,
        'pattern_groups': dict(pattern_groups),
    }


def format_confidence_explanation(guess_analysis, possible_count):
    """
    Create a detailed explanation of why a guess has a certain confidence.
    
    Args:
        guess_analysis: Result from analyze_guess()
        possible_count: Total number of possible answers
    
    Returns:
        String with detailed explanation
    """
    entropy = guess_analysis['entropy']
    elimination_rate = guess_analysis['elimination_rate']
    best_case = guess_analysis['best_case']
    worst_case = guess_analysis['worst_case']
    expected_remaining = guess_analysis['expected_remaining']
    is_answer = guess_analysis['is_answer']
    pattern_groups = guess_analysis['pattern_groups']
    
    # Determine if this is a good guess
    is_in_answers = " ✓ (Also a possible answer)" if is_answer else ""
    
    # Entropy interpretation
    max_entropy = math.log2(possible_count) if possible_count > 1 else 0
    entropy_ratio = entropy / max_entropy if max_entropy > 0 else 0
    
    if entropy_ratio >= 0.9:
        entropy_quality = "🟢 EXCELLENT - Nearly perfect split"
    elif entropy_ratio >= 0.75:
        entropy_quality = "🟢 VERY GOOD - Well-balanced split"
    elif entropy_ratio >= 0.6:
        entropy_quality = "🟡 GOOD - Reasonable split"
    elif entropy_ratio >= 0.4:
        entropy_quality = "🟠 FAIR - Could be better"
    else:
        entropy_quality = "🔴 POOR - Very unbalanced"
    
    explanation = f"""
**Detailed Breakdown:**

**Entropy: {entropy:.4f}** {entropy_quality}
→ Measures how evenly this guess splits the remaining answers
→ Higher entropy = more information = better guess
→ (Maximum possible: {max_entropy:.2f} with {possible_count} answers)

**Information Gain:**
→ {int(elimination_rate * 100)}% of answers eliminated on average
→ Expected remaining: {expected_remaining:.1f} answers

**Outcome Range:**
→ Best case: Only {best_case} answer(s) would remain
→ Worst case: {worst_case} answer(s) would remain
→ Spread: {worst_case - best_case} (lower is better)

**Number of Distinct Outcomes:** {len(pattern_groups)} different feedback patterns
→ More distinct outcomes = more informative

**Is Valid Answer:** {is_answer}{is_answer}
"""
    
    return explanation


def get_best_guesses(possible_answers, guess_list=None, top_n=5):
    """
    Find the best guesses sorted by entropy (most informative first).
    
    Args:
        possible_answers: List of possible remaining answers
        guess_list: List of guesses to consider. If None, uses possible_answers
                   (i.e., only suggests words that could be the answer)
        top_n: Return top N guesses
    
    Returns:
        List of tuples: (guess, analysis_dict)
    """
    if not possible_answers:
        return []
    
    # Default to suggesting only from possible answers if no guess list provided
    if guess_list is None:
        guess_list = possible_answers
    
    # Score all guesses
    scored_guesses = []
    for guess in guess_list:
        analysis = analyze_guess(guess, possible_answers)
        if analysis:
            scored_guesses.append((guess, analysis))
    
    # Sort by entropy (highest first)
    scored_guesses.sort(key=lambda x: x[1]['entropy'], reverse=True)
    
    return scored_guesses[:top_n]


def get_top_guess(possible_answers, guess_list=None):
    """Get the single best guess (highest entropy)."""
    top_guesses = get_best_guesses(possible_answers, guess_list, top_n=1)
    if top_guesses:
        return top_guesses[0]
    return None, None