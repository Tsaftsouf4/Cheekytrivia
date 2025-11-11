# ==============================
# Cheeky Gamblers Trivia (One-by-one + Shuffled options) — FIXED PROGRESS + 60s TIMER
# ==============================

import streamlit as st
import pandas as pd
import random
import time   # >>> για timer
from datetime import datetime
from io import BytesIO

# ------------------ Page / Theme ------------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",
    layout="wide",
)

BRAND_GOLD = "#FFD60A"
QUESTION_TIME_SEC = 60  # >>> 60’’ ανά ερώτηση

st.markdown(f"""
<style>
.block-container {{ padding-top: 8rem; padding-bottom: 2rem; }}
.badge {{
  display:inline-block; background:{BRAND_GOLD}; color:#000;
  padding:.28rem .6rem; border-radius:.55rem; font-weight:900; letter-spacing:.3px
}}
.app-title {{ font-size:1.9rem; font-weight:800; margin:0; }}
.logo img {{ height:38px; width:auto; }}
.stRadio > div{{ gap:.5rem; }}
.timer {{ font-weight:800; }}
</style>
""", unsafe_allow_html=True)

# ------------------ Helpers ------------------
REQUIRED_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def _norm(x):
    return str(x).strip().lower().replace("’","'").replace("“","\"").replace("”","\"")

def build_quiz(df: pd.DataFrame):
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, r in sample.iterrows():
        opts = [str(r["Answer 1"]), str(r["Answer 2"]), str(r["Answer 3"]), str(r["Answer 4"])]
        random.shuffle(opts)
        quiz.append({
            "q": str(r["Question"]),
            "opts": opts,
            "correct": str(r["Correct Answer"]),
            "correct_norm": _norm(r["Correct Answer"])
        })
    return quiz

def add_score_row(player: str, score: int, total: int):
    percent = round(100 * score / max(1, total), 2)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if "leaderboard" not in st.session_state:
        st.session_state.leaderboard = []
    st.session_state.leaderboard.append(
        {"timestamp": ts, "player": player or "Anonymous", "score": score, "total": total, "percent": percent}
    )

def _rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

def _clear_answers():
    if "quiz" in st.session_state:
        for j in range(1, len(st.session_state.quiz) + 1):
            st.session_state.pop(f"q{j}", None)
            st.session_state.pop(f"q{j}_locked", None)     # >>> καθάρισε locks
    st.session_state.pop("deadlines", None)                 # >>> καθάρισε deadlines

def _reset_quiz(df):
    st.session_state.quiz = build_quiz(df)
    st.session_state.current_i = 1
    _clear_answers()

# >>> helpers για timer
def _ensure_deadlines():
    if "deadlines" not in st.session_state:
        st.session_state.deadlines = {}  # {index(int): epoch_deadline(float)}

def _get_deadline(i):
    _ensure_deadlines()
    return st.session_state.deadlines.get(i)

def _start_deadline_if_absent(i):
    """Αν δεν υπάρχει deadline για την ερώτηση i, βάλε τώρα + 60s."""
    _ensure_deadlines()
    if i not in st.session_state.deadlines:
        st.session_state.deadlines[i] = time.time() + QUESTION_TIME_SEC

def _remaining_secs(i):
    dl = _get_deadline(i)
    if dl is None: return QUESTION_TIME_SEC
    return max(0, int(round(dl - time.time())))

def _lock_question(i):
    st.session_state[f"q{i}_locked"] = True

def _is_locked(i):
    return bool(st.session_state.get(f"q{i}_locked", False))

# ------------------ Header ------------------
left, right = st.columns([0.86, 0.14])
with left:
    c1, c2 = st.columns([0.06, 0.94])
    with c1:
        try: st.image("cheeky_logo.png", use_container_width=True)
        except Exception: st.markdown("🎰")
    with c2:
        st.markdown("<div class='app-title'>Cheeky Gamblers Trivia</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div style='text-align:right'><span class='badge'>$250</span> for 15/15</div>", unsafe_allow_html=True)
st.caption("15 random questions per round • Multiple choice • Stream-safe")

# ------------------ Sidebar ------------------
with st.sidebar:
    prev_player = st.session_state.get("prev_player", "")
    player = st.text_input("Player name", placeholder="e.g., Tsaf / Saro / SlotMamba", key="player")
    st.caption("Leaderboard αποθηκεύεται προσωρινά (session only).")

# ------------------ Upload (Persist file in session) ------------------
uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"], key="uploader")
if uploaded is not None:
    st.session_state["xlsx_bytes"] = uploaded.getvalue()
    st.session_state["xlsx_name"] = uploaded.name

if "xlsx_bytes" not in st.session_state:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
    if "leaderboard" in st.session_state and st.session_state.leaderboard:
        st.markdown("---"); st.subheader("🏆 Leaderboard (session)")
        df_lb = pd.DataFrame(st.session_state.leaderboard).sort_values(
            by=["score","percent","timestamp"], ascending=[False, False, True]
        )
        st.dataframe(df_lb, use_container_width=True, hide_index=True)
    st.stop()

try:
    df = pd.read_excel(BytesIO(st.session_state["xlsx_bytes"]))
except Exception as e:
    st.error(f"Could not read Excel: {e}")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]
df = df.fillna("")
missing = [c for c in REQUIRED_COLS if c not in df.columns]
if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

# ------------------ Init quiz state ------------------
if "quiz" not in st.session_state:
    _reset_quiz(df)

# >>> reset αν αλλάξει παίκτης (και δεν είναι κενό)
if player and player != prev_player:
    _reset_quiz(df)
    st.session_state["prev_player"] = player

if "prev_player" not in st.session_state:
    st.session_state["prev_player"] = player or ""

quiz = st.session_state.quiz
total_q = len(quiz)
cur = st.session_state.get("current_i", 1)
cur = max(1, min(total_q, cur))

st.markdown("---")

# ------------------ TIMER: start/track για την τρέχουσα ------------------
_start_deadline_if_absent(cur)  # >>> ξεκινάει timer όταν μπαίνεις στην ερώτηση
remaining = _remaining_secs(cur)

# Αν ο χρόνος έληξε και δεν υπάρχει απάντηση, κλείδωσε και πήγαινε αυτόματα στην επόμενη
if remaining == 0 and st.session_state.get(f"q{cur}") is None and not _is_locked(cur):
    _lock_question(cur)
    if cur < total_q:
        st.session_state.current_i = cur + 1
        _rerun()

# ------------------ Render single question + LIVE progress ------------------
q = quiz[cur - 1]
st.subheader(f"Question {cur}/{total_q}")

# Εμφάνιση timer
timer_holder = st.empty()
if not _is_locked(cur) and st.session_state.get(f"q{cur}") is None:
    # ζωντανή αντίστροφη μέτρηση
    timer_holder.markdown(f"⏳ <span class='timer'>Time left: {remaining}s</span>", unsafe_allow_html=True)
    if remaining > 0:
        time.sleep(1)   # >>> περίμενε 1s και ξανατρέξε
        _rerun()
else:
    # είτε κλειδωμένο είτε απαντημένο
    if _is_locked(cur) and st.session_state.get(f"q{cur}") is None:
        timer_holder.markdown("⌛ **Time’s up!** (locked)", unsafe_allow_html=True)
    else:
        timer_holder.markdown("✅ Answered", unsafe_allow_html=True)

# Radio: disabled όταν κλειδωθεί ή όταν έχει ήδη απαντηθεί
radio_disabled = _is_locked(cur) or (st.session_state.get(f"q{cur}") is not None)

choice_temp = st.radio(
    q["q"], q["opts"], index=None, key=f"q{cur}_temp", disabled=radio_disabled
)

if choice_temp is not None and not radio_disabled:
    st.session_state[f"q{cur}"] = choice_temp

# Progress
answered = sum(1 for j in range(1, total_q+1) if st.session_state.get(f"q{j}") is not None)
progress = answered / max(1, total_q)
st.progress(progress, text=f"Answered {answered}/{total_q}")

st.markdown("---")

# ------------------ Navigation ------------------
nav_prev, nav_next, nav_finish = st.columns([0.2, 0.2, 0.6])

with nav_prev:
    if st.button("⬅️ Previous", disabled=(cur == 1)):
        st.session_state.current_i = max(1, cur - 1)
        _rerun()

with nav_next:
    next_disabled = st.session_state.get(f"q{cur}") is None or cur == total_q
    if st.button("➡️ Next", disabled=next_disabled):
        st.session_state.current_i = min(total_q, cur + 1)
        _rerun()

with nav_finish:
    all_answered = all(st.session_state.get(f"q{j}") is not None for j in range(1, total_q+1))
    if st.button("✅ Finish round", disabled=not all_answered):
        answers = [st.session_state.get(f"q{j}") for j in range(1, total_q+1)]
        score = 0
        for j, ans in enumerate(answers, start=1):
            if ans is None: continue
            if _norm(ans) == quiz[j-1]["correct_norm"]:
                score += 1

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
col_new, _ = st.columns([0.3, 0.7])
with col_new:
    if st.button("🎲 New Random 15"):
        _reset_quiz(df)
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
