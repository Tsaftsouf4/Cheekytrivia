# ==============================
# Cheeky Gamblers Trivia (Player)
# ==============================

import streamlit as st
import pandas as pd
import random
from datetime import datetime, timezone

# ------------------ Page / Theme ------------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",   # βάλε το αρχείο στο root του repo
    layout="wide",
)

BRAND_GOLD = "#FFD60A"

st.markdown(f"""
<style>
/* Δώσε χώρο επάνω για OBS/browser */
.block-container {{
    padding-top: 8rem;            /* ↑ αύξησέ το αν θέλεις (π.χ. 10rem) */
    padding-bottom: 2rem;
}}

/* Header */
.badge {{
  display:inline-block; background:{BRAND_GOLD}; color:#000;
  padding:.28rem .6rem; border-radius:.55rem; font-weight:900; letter-spacing:.3px
}}
.app-title {{ font-size:1.9rem; font-weight:800; margin:0; }}
.logo img {{ height:38px; width:auto; }}

/* Timer */
.timer {{
  font-size:2.0rem; font-weight:900; letter-spacing:.5px;
}}
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

# ------------------ Helpers ------------------
REQUIRED_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]
ROUND_SECONDS = 60  # ⏱️ συνολικός χρόνος γύρου (άλλαξέ το όπως θες)

def _now_ts() -> float:
    return datetime.now(timezone.utc).timestamp()

def _rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

def build_quiz(df: pd.DataFrame, shuffle: bool = False):
    """Φτιάχνει 15άδα από το Excel με optional shuffle στις επιλογές."""
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, r in sample.iterrows():
        opts = [r["Answer 1"], r["Answer 2"], r["Answer 3"], r["Answer 4"]]
        if shuffle:
            random.shuffle(opts)
        quiz.append({"q": str(r["Question"]), "opts": opts, "correct": str(r["Correct Answer"])})
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

# ------------------ Sidebar ------------------
with st.sidebar:
    player = st.text_input("Player name", placeholder="e.g., Tsaf / Saro / SlotMamba")
    shuffle_answers = st.checkbox("🔀 Shuffle answers inside each question?", value=False)
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
    st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)

# ------------------ Round Timer (Player only) ------------------
if "round_deadline" not in st.session_state:
    st.session_state.round_deadline = None  # unix ts ή None

cA, cB, cC = st.columns([0.5, 0.25, 0.25])
with cA:
    b1, b2 = st.columns([0.55, 0.45])
    with b1:
        if st.session_state.round_deadline is None and st.button("▶️ Start round"):
            st.session_state.round_deadline = _now_ts() + ROUND_SECONDS
            _rerun()
    with b2:
        if st.button("🔁 Reset timer"):
            st.session_state.round_deadline = None
            # καθάρισε τυχόν επιλογές
            for j in range(1, 16):
                st.session_state.pop(f"q{j}", None)
            _rerun()

with cB:
    st.metric("Round length", f"{ROUND_SECONDS}s")

# auto-refresh όσο τρέχει ο γύρος (χωρίς st.autorefresh)
import time  # αν δεν υπάρχει ήδη επάνω
if st.session_state.round_deadline:
    time.sleep(1)   # περίμενε 1s
    _rerun()        # ξανατρέξε το app (χρησιμοποιεί το helper σου)


remaining = None
locked = False
if st.session_state.round_deadline:
    remaining = int(st.session_state.round_deadline - _now_ts())
    if remaining <= 0:
        remaining = 0
        locked = True

with cC:
    if st.session_state.round_deadline:
        st.markdown(f"<div class='timer'>⏱️ {remaining}s</div>", unsafe_allow_html=True)
    else:
        st.markdown("<div class='timer'>⏱️ —</div>", unsafe_allow_html=True)

st.markdown("---")

# ------------------ Questions ------------------
answers = []
for i, item in enumerate(st.session_state.quiz, start=1):
    choice = st.radio(
        f"{i}. {item['q']}",
        item["opts"],
        index=None,
        key=f"q{i}",
        disabled=locked,        # κλειδώνει όταν ο χρόνος μηδενίσει
    )
    answers.append(choice)

# ------------------ Actions (Submit / New Random 15) ------------------
col1, col2 = st.columns(2)

with col1:
    if st.button("✅ Submit", disabled=(st.session_state.round_deadline is None)):
        if locked:
            st.warning("⏳ Ο χρόνος έληξε! Ο γύρος έκλεισε.")
        else:
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
        st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)
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
