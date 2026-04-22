import streamlit as st
import joblib
from solver import (
    valid_guesses,
    valid_answers,
    filter_possible_answers,
    compute_constraints,
)
from solver import (
    analyze_guess,
    get_best_guesses,
)
from mlFeatures import extract_features

# Load ML model (trained offline)
try:
    ml_model = joblib.load("guess_ranker.pkl")
    ML_AVAILABLE = True
except Exception:
    ml_model = None
    ML_AVAILABLE = False

# Streamlit UI setup
st.set_page_config(page_title="Wordle Solver", layout="wide")
st.title("Wordle Solver 🟩🟨⬛")

st.markdown("""
### How to use:
1. Enter your Wordle guess
2. Enter the feedback you received (Pay attention to letter counts, if E appears twice with different colors, the constraints matter):
   - **G** = Green (correct position)
   - **Y** = Yellow (wrong position, but still included in the word)  
   - **B** = Black (not in word)
3. Repeat for each guess
4. Click "Get AI Suggestion" to see the best next best guess from a trained model!
""")

st.divider()

# Guess input
guess_history = []
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Enter Your Guesses")
    
for i in range(6):
    col_guess, col_feedback = st.columns([1, 1])
    
    with col_guess:
        guess = st.text_input(
            f"Guess #{i+1}",
            key=f"guess_{i}",
            max_chars=5,
            placeholder="e.g., CRANE"
        ).lower().strip()
    
    with col_feedback:
        feedback = st.text_input(
            f"Feedback #{i+1}",
            key=f"feedback_{i}",
            max_chars=5,
            placeholder="e.g., GBBBY"
        ).upper().strip()

    # Validate and add to history
    if guess and feedback:
        if len(guess) != 5:
            st.error(f"❌ Guess #{i+1}: Must be exactly 5 letters (only input {len(guess)})")
            continue
        if len(feedback) != 5:
            st.error(f"❌ Feedback #{i+1}: Must be exactly 5 letters (only input {len(feedback)})")
            continue
        if not all(c in "GYB" for c in feedback):
            st.error(f"❌ Feedback #{i+1}: Must only contain G, Y, or B")
            continue
        if guess not in valid_guesses:
            st.warning(f"⚠️ Guess #{i+1} '{guess.upper()}' not in Wordle's valid guesses list (but continuing anyway)")
        
        guess_history.append((guess, feedback))

st.divider()

# Solver button
if st.button("Get AI Suggestion", use_container_width=True):
    if not guess_history:
        st.warning("⚠️ Please enter at least one guess and its feedback.")
    else:
        # Compute constraints to check for issues
        green, yellow, min_counts, max_counts, excluded = compute_constraints(guess_history)
        
        # Check for contradictions
        has_contradiction = False
        contradiction_letters = []
        
        for letter, min_c in min_counts.items():
            max_c = max_counts.get(letter, 5)
            if min_c > max_c:
                has_contradiction = True
                contradiction_letters.append(
                    f"{letter.upper()}: must appear ≥{min_c} times but can appear ≤{max_c} times"
                )
        
        if has_contradiction:
            st.error("**Contradictory Constraints Detected!** The feedback you entered is inconsistent.")
            for msg in contradiction_letters:
                st.error(f"  • {msg}")
            st.info("Please check your feedback entries and try again.")
        else:
            # Filter possible answers
            possible = filter_possible_answers(valid_answers, guess_history)

            if not possible:
                st.error("**No possible answers remain.**")
                st.info("This could mean the actual Wordle answer is not in the standard word list, your feedback entries have a typo, or there's an issue with your feedback.")
                
                # Show diagnostic info
                with st.expander("🔍 Constraint Details"):
                    st.write("**Constraints:**")
                    st.write(f"Green positions: {[f'{i}: {g}' for i, g in enumerate(green) if g]}")
                    st.write(f"Yellow letters: {dict(yellow)}")
                    st.write(f"Minimum counts: {dict(min_counts)}")
                    st.write(f"Maximum counts: {dict(max_counts)}")
                    st.write(f"Excluded letters: {excluded}")
            else:

                if ML_AVAILABLE:
                    # scored = []
                    # for guess in possible:
                    #     features = extract_features(guess, possible)
                    #     score = ml_model.predict([features])[0]
                    #     scored.append((guess, score))

                    # scored.sort(key=lambda x: x[1], reverse=True)
                    # ai_guess = scored[0][0]
                    scored = []
                    for guess in possible:
                        features = extract_features(guess, possible)
                        ml_score = ml_model.predict([features])[0]
                        scored.append((guess, ml_score))

                    scored.sort(key=lambda x: x[1], reverse=True)
                    ai_guess = scored[0][0]

                    # Build a richer score using factors that actually differ between candidates
                    import numpy as np
                    from collections import Counter

                    # Letter frequency across ALL valid answers (not just remaining)
                    all_letter_freq = Counter()
                    for word in valid_answers:
                        for c in word:
                            all_letter_freq[c] += 1
                    total_letters = sum(all_letter_freq.values())
                    for k in all_letter_freq:
                        all_letter_freq[k] /= total_letters

                    # Position frequency across remaining answers
                    position_freq = [Counter() for _ in range(5)]
                    for word in possible:
                        for i, c in enumerate(word):
                            position_freq[i][c] += 1

                    combined_scores = []
                    for word, ml_score in scored:
                        # How common are this word's letters globally
                        letter_score = sum(all_letter_freq.get(c, 0) for c in set(word))

                        # How well do its letters match position patterns in remaining words
                        position_score = sum(
                            position_freq[i].get(c, 0) / len(possible)
                            for i, c in enumerate(word)
                        )

                        # Penalize duplicate letters (less information)
                        unique_bonus = len(set(word)) / 5.0

                        # Combine: ml_score anchors it, others differentiate
                        final_score = (
                            ml_score * 0.4 +
                            letter_score * 0.2 +
                            position_score * 0.3 +
                            unique_bonus * 0.1
                        )
                        combined_scores.append((word, final_score))

                    combined_scores.sort(key=lambda x: x[1], reverse=True)
                    ai_guess = combined_scores[0][0]

                    raw = np.array([s for _, s in combined_scores])
                    shifted = raw - raw.max()
                    exp_scores = np.exp(shifted / 0.05)  # low temp = decisive
                    probabilities = exp_scores / exp_scores.sum()
                    prob_map = {word: float(prob) for (word, _), prob in zip(combined_scores, probabilities)}
                    top_ranked = sorted(combined_scores[:5], key=lambda x: prob_map.get(x[0], 0), reverse=True)
                else:
                    # Fallback to rule-based solver
                    ai_guess, _ = get_best_guesses(possible, top_n=1)[0]

                # Analyze guess
                analysis = analyze_guess(ai_guess, possible)

                # Display results
                # Keep ML's top ranked guesses for later display

                # # Display results
                # top_ranked = scored[:5] if ML_AVAILABLE else [(ai_guess, 0)]

                col1, col2, col3 = st.columns(3)
                with col1:
                    st.metric("🎯 AI Suggestion", ai_guess.upper())
                with col2:
                    st.metric("📊 Remaining Answers", len(possible))
                with col3:
                    top_prob = prob_map.get(ai_guess, 0)
                    st.metric("🤖 Answer Probability", f"{top_prob:.1%}")

                st.success(f"✅ Try guessing **{ai_guess.upper()}** next!")

                st.subheader("📈 Candidate Probabilities (AI-ranked)")
                for word, _ in top_ranked:
                    prob = prob_map.get(word, 0)
                    col_w, col_b, col_p = st.columns([1, 4, 1])
                    with col_w:
                        st.code(word.upper())
                    with col_b:
                        st.progress(prob)
                    with col_p:
                        st.write(f"{prob:.1%}")

                # top_ranked = scored[:5] if ML_AVAILABLE else [(ai_guess, 0)]
                # col1, col2, col3 = st.columns(3)
                
                # with col1:
                #     st.metric("🎯 AI Suggestion", ai_guess.upper())
                    
                # with col2:
                #     st.metric("📊 Remaining Answers", len(possible))

                # st.success(f"✅ Try guessing **{ai_guess.upper()}** next!")
                                
                # Show some of the possible answers if there aren't too many
                if len(possible) <= 20:
                    with st.expander(f"📋 All {len(possible)} Possible Answers"):
                        # Display in a nice grid
                        cols = st.columns(5)
                        for idx, word in enumerate(sorted(possible)):
                            with cols[idx % 5]:
                                st.code(word.upper(), language="text")
                
                # Show diagnostic info
                with st.expander("🔍 Constraint Details"):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        st.write("**Green Positions:**")
                        green_info = {i: g for i, g in enumerate(green) if g}
                        if green_info:
                            for pos, letter in green_info.items():
                                st.write(f"  Position {pos + 1}: **{letter.upper()}**")
                        else:
                            st.write("  None yet")
                        
                        st.write("\n**Excluded Letters:**")
                        if excluded:
                            st.write(f"  {', '.join(sorted(excluded)).upper()}")
                        else:
                            st.write("  None yet")
                    
                    with col2:
                        st.write("**Yellow Letters:**")
                        if yellow:
                            for letter, bad_positions in sorted(yellow.items()):
                                pos_str = ", ".join(str(p + 1) for p in sorted(bad_positions))
                                st.write(f"  **{letter.upper()}** can't be at position {pos_str}")
                        else:
                            st.write("  None yet")
                        
                        st.write("\n**Letter Count Constraints:**")
                        if min_counts or max_counts:
                            for letter in sorted(set(list(min_counts.keys()) + list(max_counts.keys()))):
                                min_c = min_counts.get(letter, 0)
                                max_c = max_counts.get(letter, 5)
                                if min_c == max_c:
                                    st.write(f"  **{letter.upper()}**: exactly {min_c}")
                                else:
                                    st.write(f"  **{letter.upper()}**: {min_c}-{max_c} times")
                        else:
                            st.write("  None yet")

st.divider()

# Footer with instructions
st.markdown("""
---
Created by Caroline Wales, Zach Swartz, and Cole Barclay
""")
