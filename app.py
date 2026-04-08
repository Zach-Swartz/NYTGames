import streamlit as st
from solver import valid_guesses, valid_answers, filter_possible_answers, best_guess, confidence_score, compute_constraints

st.set_page_config(page_title="Wordle AI Solver", layout="wide")
st.title("Wordle AI Solver 🟩🟨⬛")

st.markdown("""
### How to use:
1. Enter your Wordle guess (e.g., "STARE")
2. Enter the feedback you received:
   - **G** = Green (correct position)
   - **Y** = Yellow (wrong position)  
   - **B** = Black (not in word)
3. Repeat for each guess
4. Click "Get AI Suggestion" to see the best next guess
""")

st.divider()

# Input multiple guesses
guess_history = []
col1, col2 = st.columns(2)

with col1:
    st.subheader("📝 Enter Your Guesses")
    
for i in range(6):
    col_guess, col_feedback = st.columns([1, 1])
    
    with col_guess:
        guess = st.text_input(
            f"Guess {i+1}",
            key=f"guess_{i}",
            max_chars=5,
            placeholder="e.g., STARE"
        ).lower().strip()
    
    with col_feedback:
        feedback = st.text_input(
            f"Feedback {i+1}",
            key=f"feedback_{i}",
            max_chars=5,
            placeholder="e.g., GBBBY"
        ).upper().strip()

    # Validate and add to history
    if guess and feedback:
        if len(guess) != 5:
            st.error(f"❌ Guess {i+1}: Must be exactly 5 letters (got {len(guess)})")
            continue
        if len(feedback) != 5:
            st.error(f"❌ Feedback {i+1}: Must be exactly 5 letters (got {len(feedback)})")
            continue
        if not all(c in "GYB" for c in feedback):
            st.error(f"❌ Feedback {i+1}: Must only contain G, Y, or B")
            continue
        if guess not in valid_guesses:
            st.warning(f"⚠️ Guess {i+1} '{guess.upper()}' not in valid guesses list (but continuing anyway)")
        
        guess_history.append((guess, feedback))

st.divider()

# Button to get suggestion
if st.button("🎯 Get AI Suggestion", use_container_width=True):
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
            st.error("❌ **Contradictory Constraints Detected!**")
            st.error("The feedback you entered is inconsistent:")
            for msg in contradiction_letters:
                st.error(f"  • {msg}")
            st.info("Please check your feedback entries and try again.")
        else:
            # Filter possible answers
            possible = filter_possible_answers(valid_answers, guess_history)

            if not possible:
                st.error("❌ **No possible answers remain.**")
                st.info("This could mean:")
                st.info("  • Your feedback entries have a typo")
                st.info("  • The actual Wordle answer is not in the standard word list")
                st.info("  • There's an inconsistency in your feedback")
                
                # Show diagnostic info
                with st.expander("🔍 Diagnostic Information"):
                    st.write("**Constraints:**")
                    st.write(f"Green positions: {[f'{i}: {g}' for i, g in enumerate(green) if g]}")
                    st.write(f"Yellow letters: {dict(yellow)}")
                    st.write(f"Min counts: {dict(min_counts)}")
                    st.write(f"Max counts: {dict(max_counts)}")
                    st.write(f"Excluded letters: {excluded}")
            else:
                # Get AI suggestion
                ai_guess, entropy = best_guess(possible, valid_guesses)
                confidence = confidence_score(ai_guess, possible)

                # Display results
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("AI Suggestion", ai_guess.upper())
                
                with col2:
                    st.metric("Remaining Answers", len(possible))
                
                with col3:
                    confidence_pct = confidence * 100
                    st.metric("Confidence", f"{confidence_pct:.1f}%")

                st.success(f"✅ Try guessing **{ai_guess.upper()}** next!")
                
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
                        st.write("**Green Positions (Exact Matches):**")
                        green_info = {i: g for i, g in enumerate(green) if g}
                        if green_info:
                            for pos, letter in green_info.items():
                                st.write(f"  Position {pos}: **{letter.upper()}**")
                        else:
                            st.write("  (none yet)")
                        
                        st.write("\n**Excluded Letters:**")
                        if excluded:
                            st.write(f"  {', '.join(sorted(excluded)).upper()}")
                        else:
                            st.write("  (none yet)")
                    
                    with col2:
                        st.write("**Yellow Letters (Wrong Position):**")
                        if yellow:
                            for letter, bad_positions in sorted(yellow.items()):
                                pos_str = ", ".join(str(p) for p in sorted(bad_positions))
                                st.write(f"  **{letter.upper()}** can't be at position {pos_str}")
                        else:
                            st.write("  (none yet)")
                        
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
                            st.write("  (none yet)")

st.divider()

# Footer with instructions
st.markdown("""
---
### 💡 Tips for using the Wordle solver:
- **Start with common words** like STARE, SLATE, or RAISE
- **The AI suggests guesses** that maximize information gain
- **Green letters** are locked in place
- **Yellow letters** must appear but in different positions
- **Black letters** won't appear in the final answer
- Pay attention to **letter counts** - if E appears twice with different colors, the constraints matter!

Made with ❤️ using Streamlit
""")