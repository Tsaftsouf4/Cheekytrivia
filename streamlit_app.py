import streamlit as st
import pandas as pd
import random
from datetime import datetime

# ---------- PAGE / BRANDING ----------
PAGE_ICON_PATH = "cheeky_logo.png"  # βάλε αρχείο logo με αυτό το όνομα στο repo (ή θα δείξει emoji)
st.set_page_config(page_title="Cheeky Gamblers Trivia – $250 Challenge", page_icon=PAGE_ICON_PATH)

BRAND_GOLD = "#FFD60A"
CUSTOM_CSS = f"""
<style>
.block-container {{ padding-top: 2rem; padding-bottom: 2.5rem; }}
/* primary buttons */
button[kind="primary"] {{
  background: linear-gradient(90deg, {BRAND_GOLD} 0%, #ffef80 100%) !important;
  color: #000 !important; border: 0; font-weight: 800;
}}
/* badge */
.badge {{
  display:inline-block;background:{BRAND_GOLD};color:#000;
  padding:.25rem .6rem;border-radius:.5rem;font-weight:900;letter-spacing:.3px
}}
</style>
"""
st.markdown(CUSTOM_CSS, unsafe_allow_html=True)

col_logo, col_title, col_badge = st.columns([0.18, 0.62, 0.20])
with col_logo:
    try:
        st.image(PAGE_ICON_PATH, use_container_width=True)
    except Exception:
        st.markdown("### 🎰")
with col_title:
    st.markdown("## Cheeky Gamblers Trivia", unsafe_allow_html=True)
    st.caption("15 random questions per round • Multiple choice • Stream-safe")
with col_badge:
    st.markdown("<div style='text-align:right;margin-top:.25rem'><span class='badge'>$250</span> for 15/15</div>", unsafe_allow_html=True)

# ---------- CONTROLS ----------
with st.sidebar:
    player = st.text_input("Player name", placeholder="e.g., Tsaf / Saro / SlotMamba")
    shuffle_answers = st.checkbox("🔀 Shuffle answers inside each question?", value=False)
    st.caption("Leaderboard is stored in session memory.")

uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"])

REQUIRED = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def build_quiz(df, shuffle=False):
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, row in sample.iterrows():
        options = [row["Answer 1"], row["Answer 2"], row["Answer 3"], row["Answer 4"]]
        if shuffle:
            random.shuffle(options)
        quiz.append({"q": str(row["Question"]), "opts": options, "correct": str(row["Correct Answer"])})
    return quiz

def add_score(player_name, score, total_q):
    if "leaderboard" not in st.session_state:
        st.session_state.leaderboard = []
    st.session_state.leaderboard.append({
        "timestamp": datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        "player": player_name or "Anonymous",
        "score": score,
        "total_questions": total_q,
        "percent": round(100 * score / max(1, total_q), 2),
    })

def get_leaderboard_df():
    return pd.DataFrame(st.session_state.get("leaderboard", []))

# ---------- MAIN ----------
if uploaded:
    try:
        df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read Excel: {e}")
        st.stop()

    if not all(c in df.columns for c in REQUIRED):
        st.error(f"Missing columns. Required: {REQUIRED}")
        st.stop()

    if "quiz" not in st.session_state:
        st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)

    answers = []
    for i, item in enumerate(st.session_state.quiz, start=1):
        choice = st.radio(f"{i}. {item['q']}", item["opts"], index=None, key=f"q{i}")
        answers.append(choice)

    c1, c2, c3 = st.columns([1,1,1])
    with c1:
        if st.button("✅ Submit", use_container_width=True):
            score = sum((ans == q["correct"]) for ans, q in zip(answers, st.session_state.quiz))
            total_q = len(st.session_state.quiz)
            st.subheader(f"Score this round: {score}/{total_q}")
            if score == total_q:
                st.success("Perfect score! Claim your $250 on stream! 🏆")
            add_score(player, score, total_q)
            with st.expander("📘 Show answers"):
                for i, (ans, q) in enumerate(zip(answers, st.session_state.quiz), start=1):
                    st.markdown(f"**{i}. {q['q']}**")
                    st.write(f"Your answer: {ans if ans else '—'}")
                    st.write(f"Correct: {q['correct']}")
                    st.write("---")
    with c2:
        if st.button("🎲 New Random 15", use_container_width=True):
            for i in range(1, len(st.session_state.quiz)+1):
                st.session_state.pop(f"q{i}", None)
            st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)
            (st.rerun() if hasattr(st, "rerun") else st.experimental_rerun())
    with c3:
        if st.button("🧹 Reset Leaderboard (session)", use_container_width=True):
            st.session_state["leaderboard"] = []
            st.success("Leaderboard cleared.")

    st.markdown("---")
    st.subheader("🏆 Leaderboard")
    lb = get_leaderboard_df()
    if not lb.empty:
        lb = lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True])
        st.dataframe(lb, use_container_width=True, hide_index=True)
    else:
        st.info("No scores yet. Submit a round to appear here.")
else:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
