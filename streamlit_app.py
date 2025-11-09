# ==============================
# Cheeky Gamblers Trivia (One-by-one)
# ==============================

import streamlit as st
import pandas as pd
import random
from datetime import datetime

# ------------------ Page / Theme ------------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",   # βάλε το αρχείο στο root του repo
    layout="wide",
)

BRAND_GOLD = "#FFD60A"

st.markdown(f"""
<style>
/* Δώσε χώρο επάνω για OBS/browser ώστε να μη κόβεται */
.block-container {{
    padding-top: 8rem;         /* ↑ ρύθμισε το (π.χ. 10rem) αν θέλεις περισσότερο */
    padding-bottom: 2rem;
}}

/* Header */
.badge {{
  display:inline-block; background:{BRAND_GOLD}; color:#000;
  padding:.28rem .6rem; border-radius:.55rem; font-weight:900; letter-spacing:.3px
}}
.app-title {{ font-size:1.9rem; font-weight:800; margin:0; }}
.logo img {{ height:38px; width:auto; }}

/* Λίγο πιο καθαρά τα radios */
.stRadio > div{{ gap:.5rem; }}
</style>
""", unsafe_allow_html=True)

# Header (logo + τίτλος + badge)
left, right = st.columns([0.86, 0.14])
with left:
    c1, c2 = st.columns([0.06, 0.94])
    with c1:
        try:
            st.image("cheeky_logo.png", use_container_width=True)
        except Exception:
            st.markdown("🎰")
    with c2:
        st.markdown("<div class='app-title'>Cheeky Gamblers Trivia</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div style='text-align:right'><span class='badge'>$250</span> for 15/15</div>", unsafe_allow_html=True)

st.caption("15 random questions per round • Multiple choice • Stream-safe")

# ------------------ Constants / Helpers ------------------
REQUIRED_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def build_quiz(df: pd.DataFrame):
    """Φτιάχνει σετ 15 ερωτήσεων από το Excel (χωρίς shuffle)."""
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, r in sample.iterrows():
        opts = [str(r["Answer 1"]), str(r["Answer 2"]), str(r["Answer 3"]), str(r["Answer 4"])]
        quiz.append({
            "q": str(r["Question"]),
            "opts": opts,
            "correct": str(r["Correct Answer"])
        })
    return quiz

def add_score_row(player: str, score: int, total: int):
    """Απλός leaderboard σε session."""
    percent = round(100 * score / max(1, total), 2)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if "leaderboard" not in st.session_state:
        st.session_state.leaderboard = []
    st.session_state.leaderboard.append(
        {"timestamp": ts, "player": player or "Anonymous", "score": score, "total": total, "percent": percent}
    )

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# ------------------ Sidebar ------------------
with st.sidebar:
    player = st.text_input("Player name", placeholder="e.g., Tsaf / Saro / SlotMamba")
    st.caption("Leaderboard αποθηκεύεται προσωρινά (session only).")

# ------------------ Upload ------------------
uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"])

if uploaded is None:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
    # δείξε leaderboard αν υπάρχει
    if "leaderboard" in st.session_state and st.session_state.leaderboard:
        st.markdown("---")
        st.subheader("🏆 Leaderboard (session)")
        df_lb = pd.DataFrame(st.session_state.leaderboard)
        df_lb = df_lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True])
        st.dataframe(df_lb, use_container_width=True, hide_index=True)
    st.stop()

# ------------------ Read Excel ------------------
try:
    df = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Could not read Excel: {e}")
    st.stop()

if not all(c in df.columns for c in REQUIRED_COLS):
    st.error(f"Missing columns. Required: {REQUIRED_COLS}")
    st.stop()

# Δημιούργησε quiz μία φορά
if "quiz" not in st.session_state:
    st.session_state.quiz = build_quiz(df)
    st.session_state.current_i = 1  # 1-based index
    # καθάρισε τυχόν προηγούμενες απαντήσεις
    for j in range(1, len(st.session_state.quiz) + 1):
        st.session_state.pop(f"q{j}", None)

quiz = st.session_state.quiz
total_q = len(quiz)
cur = st.session_state.get("current_i", 1)
cur = max(1, min(total_q, cur))

# ------------------ Progress header ------------------
answered = sum(1 for j in range(1, total_q+1) if st.session_state.get(f"q{j}") is not None)
progress = answered / max(1, total_q)
st.progress(progress, text=f"Answered {answered}/{total_q}")

st.markdown("---")

# ------------------ Render single question ------------------
q = quiz[cur - 1]
st.subheader(f"Question {cur}/{total_q}")
choice = st.radio(q["q"], q["opts"], index=None, key=f"q{cur}")

nav_prev, nav_next, nav_finish = st.columns([0.2, 0.2, 0.6])

with nav_prev:
    if st.button("⬅️ Previous", disabled=(cur == 1)):
        st.session_state.current_i = max(1, cur - 1)
        _rerun()

with nav_next:
    # next ενεργό μόνο αν απαντήθηκε η τρέχουσα
    next_disabled = st.session_state.get(f"q{cur}") is None or cur == total_q
    if st.button("➡️ Next", disabled=next_disabled):
        st.session_state.current_i = min(total_q, cur + 1)
        _rerun()

with nav_finish:
    # επιτρέπουμε finish όταν έχουν απαντηθεί όλες
    all_answered = all(st.session_state.get(f"q{j}") is not None for j in range(1, total_q+1))
    if st.button("✅ Finish round", disabled=not all_answered):
        # υπολογισμός σκορ
        answers = [st.session_state.get(f"q{j}") for j in range(1, total_q+1)]
        score = sum((ans == quiz[j-1]["correct"]) for j, ans in enumerate(answers, start=1))
        st.subheader(f"Score this round: {score}/{total_q}")
        if score == total_q:
            st.success("Perfect score! Claim your $250! 🏆")

        add_score_row(player, score, total_q)

        with st.expander("📘 Show answers"):
            for j in range(1, total_q+1):
                st.markdown(f"**{j}. {quiz[j-1]['q']}**")
                st.write(f"Your answer: {st.session_state.get(f'q{j}') or '—'}")
                st.write(f"Correct: {quiz[j-1]['correct']}")
                st.write("---")

# ------------------ New set ------------------
st.markdown("---")
col_new, col_jump = st.columns([0.3, 0.7])
with col_new:
    if st.button("🎲 New Random 15"):
        # καθάρισε επιλογές & ξαναφτιάξε 15άδα
        for j in range(1, len(quiz)+1):
            st.session_state.pop(f"q{j}", None)
        st.session_state.quiz = build_quiz(df)
        st.session_state.current_i = 1
        _rerun()

# ------------------ Leaderboard (session) ------------------
st.markdown("---")
st.subheader("🏆 Leaderboard (session)")
if "leaderboard" not in st.session_state or not st.session_state.leaderboard:
    st.info("No scores yet.")
else:
    df_lb = pd.DataFrame(st.session_state.leaderboard)
    df_lb = df_lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True])
    st.dataframe(df_lb, use_container_width=True, hide_index=True)
