import streamlit as st
import pandas as pd
import random

st.set_page_config(page_title="Cheeky Gamblers Trivia – $250 Challenge", page_icon="🎰")

st.title("Cheeky Gamblers Trivia – $250 Challenge")
st.caption("Upload your Excel file below. Each run generates 15 random questions.")

uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"])
shuffle_answers = st.checkbox("🔀 Shuffle answers inside each question?", value=False)

required_cols = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def build_quiz(df, shuffle=False):
    sample = df.sample(n=min(15, len(df)), random_state=42).reset_index(drop=True)
    import random as _r
    quiz = []
    for _, row in sample.iterrows():
        options = [row["Answer 1"], row["Answer 2"], row["Answer 3"], row["Answer 4"]]
        if shuffle:
            _r.shuffle(options)
        quiz.append({
            "q": str(row["Question"]),
            "opts": options,
            "correct": str(row["Correct Answer"])
        })
    return quiz

if uploaded:
    try:
        df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read Excel: {e}")
        st.stop()

    if not all(c in df.columns for c in required_cols):
        st.error(f"Missing columns. Required: {required_cols}")
        st.stop()

    if "quiz" not in st.session_state:
        st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)

    answers = []
    for i, item in enumerate(st.session_state.quiz, start=1):
        choice = st.radio(f"{i}. {item['q']}", item["opts"], index=None, key=f"q{i}")
        answers.append(choice)

    col1, col2 = st.columns(2)
    with col1:
        if st.button("✅ Submit"):
            score = sum((ans == q["correct"]) for ans, q in zip(answers, st.session_state.quiz))
            st.subheader(f"Score: {score}/15")
            if score == 15:
                st.success("Perfect score! Claim your $250 on stream! 🏆")
            with st.expander("📘 Show answers"):
                for i, (ans, q) in enumerate(zip(answers, st.session_state.quiz), start=1):
                    st.markdown(f"**{i}. {q['q']}**")
                    st.write(f"Your answer: {ans if ans else '—'}")
                    st.write(f"Correct: {q['correct']}")
                    st.write("---")
    with col2:
        if st.button("🎲 New Random 15"):
            if "quiz" in st.session_state:
                del st.session_state["quiz"]
            st.experimental_rerun()
else:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
