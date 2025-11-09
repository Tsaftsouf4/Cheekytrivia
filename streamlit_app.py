# ==============================
# Cheeky Gamblers Trivia (One-by-one + Shuffled + Visuals)
# ==============================

import streamlit as st
import pandas as pd
import random
from datetime import datetime
import time

# ------------------ Page / Theme ------------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",   # βάλε το αρχείο στο root του repo
    layout="wide",
)

BRAND_GOLD = "#FFD60A"
BRAND_NEON = "#FF33CC"
BRAND_DARK = "#0b0f14"

# Global CSS: background, neon panel frame, progress glow, question reveal anim, small name tile
st.markdown(f"""
<style>
/* ====== BACKGROUND (image + fallback gradient) ====== */
[data-testid="stAppViewContainer"] > .main {{
  background: linear-gradient(135deg, #0b0f14 0%, #111826 60%, #001a2c 100%);
  background-attachment: fixed;
}}
/* If bg image exists, overlay it softly */
body:before {{
  content: "";
  position: fixed; inset: 0;
  background: url('cheeky_bg.jpg') center/cover no-repeat;
  opacity: .15; pointer-events: none; z-index: -1;
}}

/* ====== LAYOUT SPACING ====== */
.block-container {{
    padding-top: 8rem;            /* ↑ προσαρμογή αν θες */
    padding-bottom: 2rem;
    max-width: 1200px;
}}

/* ====== NEON PANEL FRAME ====== */
.panel {{
  border-radius: 18px;
  padding: 24px 24px;
  background: rgba(10,14,20,.65);
  box-shadow:
    0 0 0 1px rgba(255,255,255,.04) inset,
    0 0 24px rgba(255, 214, 10, .12),            /* gold glow */
    0 0 48px rgba(255, 51, 204, .10);            /* neon pink glow */
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

/* ====== HEADER BADGE ====== */
.badge {{
  display:inline-block; background:{BRAND_GOLD}; color:#000;
  padding:.32rem .7rem; border-radius:.55rem; font-weight:900; letter-spacing:.3px
}}
.app-title {{ font-size:1.9rem; font-weight:800; margin:0; color:#f5f6f8; }}
.logo img {{ height:38px; width:auto; }}

/* ====== NAME TILE (top-right mini scoreboard) ====== */
.name-tile {{
  display:inline-block; min-width: 180px; text-align:right;
  padding:.55rem .8rem; border-radius:10px;
  background: linear-gradient(180deg, rgba(255,214,10,.22), rgba(255,214,10,.05));
  color:#fff; font-weight:800; letter-spacing:.3px;
  box-shadow: 0 0 18px rgba(255,214,10,.18), inset 0 0 0 1px rgba(255,214,10,.35);
}}
.name-tile .label {{ font-size:.72rem; opacity:.75; display:block; }}
.name-tile .value {{ font-size:1.05rem; color:#fff; }}

/* ====== PROGRESS BAR glow ====== */
[data-testid="stProgress"] > div > div {{
  box-shadow: 0 0 16px rgba(255,214,10,.35);
  background: linear-gradient(90deg, {BRAND_GOLD}, {BRAND_NEON});
}}

/* ====== RADIO SPACING ====== */
.stRadio > div{{ gap:.6rem; }}

/* ====== QUESTION REVEAL (animation on question change) ====== */
.q-reveal {{
  animation: qslide .55s ease-out;
  color: #f1f4f8;
}}
@keyframes qslide {{
  0%   {{ transform: translateY(8px); opacity: 0; filter: drop-shadow(0 0 0 rgba(255,51,204,0)); }}
  60%  {{ transform: translateY(0);   opacity: 1; filter: drop-shadow(0 0 8px rgba(255,51,204,.45)); }}
  100% {{ filter: drop-shadow(0 0 0 rgba(255,51,204,0)); }}
}}
</style>
""", unsafe_allow_html=True)

# ------------------ Helpers ------------------
REQUIRED_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def _norm(x):
    """Ομογενοποίηση κειμένου για ασφαλή σύγκριση (αποφυγή κενών/ειδικών)."""
    return str(x).strip().lower().replace("’","'").replace("“","\"").replace("”","\"")

def build_quiz(df: pd.DataFrame):
    """Φτιάχνει 15άδα και SHUFFLE τις επιλογές κάθε ερώτησης (κρατάμε correct ως κείμενο+normalized)."""
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, r in sample.iterrows():
        opts = [str(r["Answer 1"]), str(r["Answer 2"]), str(r["Answer 3"]), str(r["Answer 4"])]
        random.shuffle(opts)  # τυχαία σειρά απαντήσεων
        quiz.append({
            "q": str(r["Question"]),
            "opts": opts,                         # για εμφάνιση
            "correct": str(r["Correct Answer"]),  # raw για εμφάνιση
            "correct_norm": _norm(r["Correct Answer"])  # normalized για check
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

# ------------------ Header (logo + title + name tile) ------------------
left, right = st.columns([0.75, 0.25], vertical_alignment="center")
with left:
    c1, c2 = st.columns([0.08, 0.92])
    with c1:
        try:
            st.image("cheeky_logo.png", use_container_width=True)
        except Exception:
            st.markdown("🎰")
    with c2:
        st.markdown("<div class='app-title'>Cheeky Gamblers Trivia</div>", unsafe_allow_html=True)
with right:
    st.markdown(
        f"<div class='name-tile'><span class='label'>PLAYER</span><span class='value'>{(player or '—')}</span></div>",
        unsafe_allow_html=True
    )

st.caption("15 random questions per round • Multiple choice • Stream-safe")

# ------------------ Upload ------------------
uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"], key="uploader")

if uploaded is None:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
    # Leaderboard (αν υπάρχει) μέσα σε πάνελ για να φαίνεται ωραίο
    if "leaderboard" in st.session_state and st.session_state.leaderboard:
        st.markdown("### ")
        with st.container(border=True):
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

# καθάρισε headers/NaN για σιγουριά
df.columns = [str(c).strip() for c in df.columns]
df = df.fillna("")

missing = [c for c in REQUIRED_COLS if c not in df.columns]
if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

# ------------------ Init quiz state ------------------
if "quiz" not in st.session_state:
    st.session_state.quiz = build_quiz(df)
    st.session_state.current_i = 1  # 1-based index
    # καθάρισε τυχόν προηγούμενες απαντήσεις
    for j in range(1, len(st.session_state.quiz) + 1):
        st.session_state.pop(f"q{j}", None)
    # για animation reset
    st.session_state.last_q = None

quiz = st.session_state.quiz
total_q = len(quiz)
cur = st.session_state.get("current_i", 1)
cur = max(1, min(total_q, cur))

# ------------------ MAIN PANEL WRAPPER ------------------
st.markdown("<div class='panel'>", unsafe_allow_html=True)

# -------- Progress header (live) --------
answered_now = sum(1 for j in range(1, total_q+1) if st.session_state.get(f"q{j}") is not None)
progress = answered_now / max(1, total_q)
st.progress(progress, text=f"Answered {answered_now}/{total_q}")

st.markdown("---")

# -------- Render single question with reveal animation --------
q = quiz[cur - 1]

# trigger animation όταν αλλάζει η ερώτηση
if st.session_state.last_q != cur:
    st.session_state.last_q = cur
    # βάζουμε ένα micro-delay ώστε το DOM να ξαναχτιστεί και να τρέξει η anim
    time.sleep(0.03)

st.subheader(f"Question {cur}/{total_q}")
st.markdown(f"<div class='q-reveal'><h3 style='margin-top:0'>{q['q']}</h3></div>", unsafe_allow_html=True)

# Radio με temporary key + άμεση αποθήκευση στο μόνιμο για σωστό progress
choice_temp = st.radio("Pick your answer:", q["opts"], index=None, key=f"q{cur}_temp")
if choice_temp is not None:
    st.session_state[f"q{cur}"] = choice_temp

st.markdown("---")

# ------------------ Navigation ------------------
nav_prev, nav_next, nav_finish = st.columns([0.2, 0.2, 0.6])

with nav_prev:
    if st.button("⬅️ Previous", disabled=(cur == 1)):
        st.session_state.current_i = max(1, cur - 1)
        _rerun()

with nav_next:
    # Next ενεργό μόνο αν απαντήθηκε η τρέχουσα
    next_disabled = st.session_state.get(f"q{cur}") is None or cur == total_q
    if st.button("➡️ Next", disabled=next_disabled):
        st.session_state.current_i = min(total_q, cur + 1)
        _rerun()

with nav_finish:
    # Finish όταν έχουν απαντηθεί όλες
    all_answered = all(st.session_state.get(f"q{j}") is not None for j in range(1, total_q+1))
    if st.button("✅ Finish round", disabled=not all_answered):
        answers = [st.session_state.get(f"q{j}") for j in range(1, total_q+1)]
        score = 0
        for j, ans in enumerate(answers, start=1):
            if ans is None:
                continue
            if _norm(ans) == quiz[j-1]["correct_norm"]:
                score += 1

        # Perfect = μόνο εκεί κάνουμε celebrate (αν θες stealth)
        if score == total_q:
            st.subheader(f"Perfect score: {score}/{total_q} 🎉 $250!")
            st.balloons()
            add_score_row(player, score, total_q)
            with st.expander("📘 Show answers"):
                for j in range(1, total_q+1):
                    st.markdown(f"**{j}. {quiz[j-1]['q']}**")
                    st.write(f"Your answer: {st.session_state.get(f'q{j}') or '—'}")
                    st.write(f"Correct: {quiz[j-1]['correct']}")
                    st.write("---")
        else:
            # stealth: προαιρετικά μπορείς να μη δείξεις τίποτα—εδώ κρατάω ουδέτερο μήνυμα
            add_score_row(player, score, total_q)
            st.info("Round complete.")
            if st.button("🎲 Next player (new 15)"):
                for j in range(1, total_q+1):
                    st.session_state.pop(f"q{j}", None)
                st.session_state.quiz = build_quiz(df)
                st.session_state.current_i = 1
                _rerun()

# κλείσιμο neon panel
st.markdown("</div>", unsafe_allow_html=True)

# ------------------ Leaderboard (session) ------------------
st.markdown("### ")
with st.container(border=True):
    st.subheader("🏆 Leaderboard (session)")
    if "leaderboard" not in st.session_state or not st.session_state.leaderboard:
        st.info("No scores yet.")
    else:
        df_lb = pd.DataFrame(st.session_state.leaderboard)
        df_lb = df_lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True])
        st.dataframe(df_lb, use_container_width=True, hide_index=True)
