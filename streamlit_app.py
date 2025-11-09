# ==============================
# Cheeky Gamblers Trivia (Player)
# ==============================

import streamlit as st
import pandas as pd
import random
from datetime import datetime

# ------------------ Page / Theme ------------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",   # Βάλε το αρχείο στο root του repo
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
    """Φτιάχνει σετ 15 ερωτήσεων από το Excel, χωρίς shuffle στις επιλογές."""
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, r in sample.iterrows():
        opts = [r["Answer 1"], r["Answer 2"], r["Answer 3"], r["Answer 4"]]
        quiz.append({
            "q": str(r["Question"]),
            "opts": [str(x) for x in opts],
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

st.markdown("---")

# ------------------ Questions ------------------
answers = []
for i, item in enumerate(st.session_state.quiz, start=1):
    choice = st.radio(
        f"{i}. {item['q']}",
        item["opts"],
        index=None,
        key=f"q{i}",
    )
    answers.append(choice)

# ------------------ Actions (Submit / New Random 15) ------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Submit"):
        score = sum((ans == q["correct"]) for ans, q in zip(answers, st.session_state.quiz))
        total = len(st.session_state.quiz)
        st.subheader(f"Score this round: {score}/{total}")
        if score == total:
            st.success("Perfect score! Claim your $250! 🏆")

        add_score_row(player, score, total)

        with st.expander("📘 Show answers"):
            for j, (ans, q) in enumerate(zip(answers, st.session_state.quiz), start=1):
                st.markdown(f"**{j}. {q['q']}**")
                st.write(f"Your answer: {ans if ans else '—'}")
                st.write(f"Correct: {q['correct']}")
                st.write("---")

with col2:
    if st.button("🎲 New Random 15"):
        # καθάρισε επιλογές & ξαναφτιάξε 15άδα
        for j in range(1, len(st.session_state.quiz)+1):
            st.session_state.pop(f"q{j}", None)
        st.session_state.quiz = build_quiz(df)
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
