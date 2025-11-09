import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime

# ------------------ Page ------------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",   # προαιρετικό αρχείο στο repo
    layout="wide",
)

# ------------------ CSS (neon + tile + animation) ------------------
st.markdown("""
<style>
/* Background (gradient + optional image overlay) */
[data-testid="stAppViewContainer"] > .main {
  background: linear-gradient(135deg, #0b0f14 0%, #111826 60%, #001a2c 100%);
  background-attachment: fixed;
}
body:before {
  content: "";
  position: fixed; inset: 0;
  background: url('cheeky_bg.jpg') center/cover no-repeat;
  opacity: .15; pointer-events: none; z-index: -1;
}

/* Layout spacing */
.block-container {
  padding-top: 6rem;
  padding-bottom: 2rem;
  max-width: 1180px;
}

/* Neon panel */
.neon-panel {
  border-radius: 18px;
  padding: 24px 24px;
  background: rgba(10, 14, 20, .68);
  box-shadow:
    0 0 0 1px rgba(255,255,255,.04) inset,
    0 0 28px rgba(255, 214, 10, .14),
    0 0 48px rgba(255, 51, 204, .10);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

/* Name tile (small scoreboard) */
.name-tile {
  display: inline-flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  min-width: 160px;
  padding: 0.65rem 1rem;
  border-radius: 12px;
  background: rgba(255, 214, 10, 0.10);
  border: 1px solid rgba(255, 214, 10, 0.40);
  box-shadow: 0 0 12px rgba(255, 214, 10, 0.28), inset 0 0 8px rgba(255, 214, 10, 0.15);
  color: #fff;
  text-align: center;
}
.name-tile .label {
  font-size: 0.70rem;
  font-weight: 600;
  letter-spacing: 0.8px;
  color: rgba(255, 255, 255, 0.75);
  margin-bottom: 0.15rem;
}
.name-tile .value {
  font-size: 1.2rem;
  font-weight: 800;
  color: #FFD60A;
  text-shadow: 0 0 6px rgba(255, 214, 10, 0.45);
}

/* Progress glow */
[data-testid="stProgress"] > div > div {
  box-shadow: 0 0 16px rgba(255,214,10,.35);
  background: linear-gradient(90deg, #FFD60A, #FF33CC);
}

/* Radio spacing */
.stRadio > div { gap: .6rem; }

/* Question reveal animation */
.q-reveal {
  animation: qslide .55s ease-out;
  color: #f1f4f8;
}
@keyframes qslide {
  0%   { transform: translateY(8px); opacity: 0; filter: drop-shadow(0 0 0 rgba(255,51,204,0)); }
  60%  { transform: translateY(0);   opacity: 1; filter: drop-shadow(0 0 8px rgba(255,51,204,.45)); }
  100% { filter: drop-shadow(0 0 0 rgba(255,51,204,0)); }
}

/* Little badge */
.badge {
  display:inline-block; background:#FFD60A; color:#000;
  padding:.32rem .7rem; border-radius:.55rem; font-weight:900; letter-spacing:.3px
}
</style>
""", unsafe_allow_html=True)

# ------------------ Helpers ------------------
REQUIRED = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def norm(x: str) -> str:
    return str(x).strip().lower().replace("’","'").replace("“","\"").replace("”","\"")

def build_quiz(df: pd.DataFrame, n=15):
    sample = df.sample(n=min(n, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    out = []
    for _, r in sample.iterrows():
        opts = [str(r["Answer 1"]), str(r["Answer 2"]), str(r["Answer 3"]), str(r["Answer 4"])]
        random.shuffle(opts)
        out.append({
            "q": str(r["Question"]),
            "opts": opts,
            "correct": str(r["Correct Answer"]),
            "correct_norm": norm(r["Correct Answer"]),
        })
    return out

def add_score_row(player: str, score: int, total: int):
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
    st.caption("Scores are stored in session memory.")

# ------------------ Header row ------------------
left, right = st.columns([0.75, 0.25], vertical_alignment="center")
with left:
    c1, c2 = st.columns([0.08, 0.92])
    with c1:
        try:
            st.image("cheeky_logo.png", use_container_width=True)
        except Exception:
            st.markdown("🎰")
    with c2:
        st.markdown("### Cheeky Gamblers Trivia")
        st.caption("15 random questions per round • Multiple choice • Stream-safe")
with right:
    st.markdown(
        f"<div class='name-tile'><span class='label'>PLAYER</span><span class='value'>{(player or '—')}</span></div>",
        unsafe_allow_html=True
    )

# ------------------ Upload ------------------
uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"], key="uploader")

if uploaded is None:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
    if "leaderboard" in st.session_state and st.session_state.leaderboard:
        st.markdown("### ")
        with st.container(border=True):
            st.subheader("🏆 Leaderboard (session)")
            df_lb = pd.DataFrame(st.session_state.leaderboard)
            df_lb = df_lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True])
            st.dataframe(df_lb, use_container_width=True, hide_index=True)
    st.stop()

# ------------------ Read/validate ------------------
try:
    df = pd.read_excel(uploaded)
except Exception as e:
    st.error(f"Could not read Excel: {e}")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]
df = df.fillna("")
missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

# ------------------ Init state ------------------
if "quiz" not in st.session_state:
    st.session_state.quiz = build_quiz(df)
    st.session_state.current_i = 1
    # καθαρισμός απαντήσεων
    for j in range(1, len(st.session_state.quiz)+1):
        st.session_state.pop(f"q{j}", None)
    st.session_state.last_q = None
    # timers store per question
    st.session_state.deadlines = {}

quiz = st.session_state.quiz
total_q = len(quiz)
cur = max(1, min(total_q, st.session_state.get("current_i", 1)))

# ------------------ Timer per question (45s) ------------------
SECONDS_PER_Q = 45

# Αν άλλαξε ερώτηση -> ξεκίνα από την αρχή το timer και ξεκλείδωσε
if st.session_state.last_q != cur:
    st.session_state.last_q = cur
    now = time.time()
    st.session_state.deadlines[cur] = now + SECONDS_PER_Q
    st.session_state[f"locked_{cur}"] = False
    # reset temp key για να μην κουβαλάει παλιό selection
    st.session_state.pop(f"q{cur}_temp", None)

# Υπολόγισε πόσο μένει
now = time.time()
deadline = st.session_state.deadlines.get(cur, now + SECONDS_PER_Q)
remaining = max(0, int(deadline - now))
time_up = remaining <= 0

# Αν τελείωσε ο χρόνος -> κλείδωσε
if time_up and not st.session_state.get(f"locked_{cur}", False):
    st.session_state[f"locked_{cur}"] = True

# ------------------ MAIN PANEL ------------------
st.markdown("<div class='neon-panel'>", unsafe_allow_html=True)
st.markdown("### ")  # μικρό κενό για οπτικό χώρο
st.markdown("**Progress**")

with st.container(border=False):
    answered = sum(1 for j in range(1, total_q+1) if st.session_state.get(f"q{j}") is not None)
    st.progress(answered / max(1, total_q), text=f"Answered {answered}/{total_q}")


# Ερώτηση
q = quiz[cur - 1]
st.subheader(f"Question {cur}/{total_q}")

# Countdown οπτικά
timer_col1, timer_col2 = st.columns([0.18, 0.82])
with timer_col1:
    st.markdown(f"**⏱️ {remaining}s**")
with timer_col2:
    st.progress(remaining / SECONDS_PER_Q)

# Reveal animation
st.markdown(f"<div class='q-reveal'><h3 style='margin-top:0'>{q['q']}</h3></div>", unsafe_allow_html=True)

# Επιλογές (κλειδώνουν όταν μηδενίσει ο χρόνος)
disabled_radio = st.session_state.get(f"locked_{cur}", False)
choice_temp = st.radio("Pick your answer:", q["opts"], index=None, key=f"q{cur}_temp", disabled=disabled_radio)
if choice_temp is not None and not disabled_radio:
    st.session_state[f"q{cur}"] = choice_temp

if disabled_radio and st.session_state.get(f"q{cur}") is None:
    st.warning("Time's up — no answers accepted for this question.")

st.markdown("---")

# Navigation
nav_prev, nav_next, nav_finish = st.columns([0.2, 0.2, 0.6])

with nav_prev:
    if st.button("⬅️ Previous", disabled=(cur == 1)):
        st.session_state.current_i = max(1, cur - 1)
        _rerun()

with nav_next:
    # Next ενεργό αν:
    # - υπάρχει απάντηση, ή
    # - έχει λήξει ο χρόνος
    next_enabled = (st.session_state.get(f"q{cur}") is not None) or disabled_radio
    next_disabled = (cur == total_q) or (not next_enabled)
    if st.button("➡️ Next", disabled=next_disabled):
        st.session_state.current_i = min(total_q, cur + 1)
        _rerun()

with nav_finish:
    # Finish όταν έχουν απαντηθεί όλες (ή έχουν λήξει) για όλες
    all_done = True
    for j in range(1, total_q+1):
        if (st.session_state.get(f"q{j}") is None) and (not st.session_state.get(f"locked_{j}", False)):
            all_done = False
            break
    if st.button("✅ Finish round", disabled=not all_done):
        # Υπολογισμός score μόνο σε όσες έχουν answer
        score = 0
        for j in range(1, total_q+1):
            ans = st.session_state.get(f"q{j}")
            if ans is None:
                continue
            if norm(ans) == quiz[j-1]["correct_norm"]:
                score += 1

        # Perfect only celebrate
        if score == total_q:
            st.subheader(f"Perfect score: {score}/{total_q} 🎉 $250!")
            st.balloons()
        else:
            st.info(f"Round complete. Score: {score}/{total_q}")

        add_score_row(player, score, total_q)

        if st.button("🎲 Next player (new 15)"):
            # reset round
            st.session_state.quiz = build_quiz(df)
            st.session_state.current_i = 1
            for j in range(1, total_q+1):
                st.session_state.pop(f"q{j}", None)
                st.session_state.pop(f"q{j}_temp", None)
                st.session_state.pop(f"locked_{j}", None)
            st.session_state.deadlines = {}
            _rerun()

st.markdown("</div>", unsafe_allow_html=True)

# Leaderboard
st.markdown("### ")
with st.container(border=True):
    st.subheader("🏆 Leaderboard (session)")
    if "leaderboard" not in st.session_state or not st.session_state.leaderboard:
        st.info("No scores yet.")
    else:
        df_lb = pd.DataFrame(st.session_state.leaderboard)
        df_lb = df_lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True])
        st.dataframe(df_lb, use_container_width=True, hide_index=True)

# -------- Auto refresh ανά 1s για να μετράει ορατά το timer --------
# (χωρίς experimental apis, απλά επανατρέχει το script ανά δευτερόλεπτο)
if remaining > 0:
    time.sleep(1)
    _rerun()
