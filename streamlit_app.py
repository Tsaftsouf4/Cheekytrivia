import io
import os
import time
import random
from pathlib import Path
from datetime import datetime

import pandas as pd
import streamlit as st

# =============================================================================
# Page / Global
# =============================================================================
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",  # βάλε το αρχείο στο root του repo
    layout="wide",
)

# -----------------------------------------------------------------------------
# Cache paths (για να μη χρειάζεται νέο upload σε κάθε refresh)
# -----------------------------------------------------------------------------
CACHE_DIR = Path("_cache")
CACHE_DIR.mkdir(exist_ok=True)
CACHE_PATH = CACHE_DIR / "last.xlsx"

def save_cached_file(file_bytes: bytes):
    try:
        CACHE_PATH.write_bytes(file_bytes)
    except Exception as e:
        st.warning(f"Couldn't write cache file: {e}")

def load_cached_file() -> bytes | None:
    try:
        if CACHE_PATH.exists():
            return CACHE_PATH.read_bytes()
    except Exception as e:
        st.warning(f"Couldn't read cache file: {e}")
    return None

def rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()


# =============================================================================
# CSS
# =============================================================================
st.markdown(
    """
<style>
/* Background */
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
.block-container { padding-top: 5rem; max-width: 1180px; }

/* Neon panel + shadow box για progress που περιέχει το st.progress */
.neon-panel {
  border-radius: 18px;
  padding: 20px 22px;
  background: rgba(10, 14, 20, .68);
  box-shadow:
    0 0 0 1px rgba(255,255,255,.04) inset,
    0 0 28px rgba(255, 214, 10, .14),
    0 0 48px rgba(255, 51, 204, .10);
  backdrop-filter: blur(6px);
  -webkit-backdrop-filter: blur(6px);
}

/* Progress container "κουτί" */
.progress-box {
  border-radius: 14px;
  padding: 10px 12px 6px 12px;
  background: rgba(0,0,0,.35);
  box-shadow: inset 0 0 10px rgba(255,214,10,.18);
}

/* Progress glow + gradient fill */
[data-testid="stProgress"] > div > div {
  height: 10px;
  border-radius: 999px;
  box-shadow: 0 0 16px rgba(255,214,10,.35);
  background: linear-gradient(90deg, #FFD60A, #FF33CC);
}

/* Player tile */
.name-tile {
  display: inline-flex; flex-direction: column; align-items: center; justify-content: center;
  min-width: 160px; padding: .6rem 1rem; border-radius: 12px;
  background: rgba(255, 214, 10, 0.10);
  border: 1px solid rgba(255, 214, 10, 0.40);
  box-shadow: 0 0 12px rgba(255, 214, 10, 0.28), inset 0 0 8px rgba(255, 214, 10, 0.15);
  color: #fff; text-align: center;
}
.name-tile .label { font-size: .70rem; font-weight: 600; letter-spacing: .8px; color: rgba(255,255,255,.75); margin-bottom: .15rem; }
.name-tile .value { font-size: 1.2rem; font-weight: 800; color: #FFD60A; text-shadow: 0 0 6px rgba(255,214,10,.45); }

/* Question reveal animation */
.q-reveal { animation: qslide .55s ease-out; color: #f1f4f8; }
@keyframes qslide {
  0%   { transform: translateY(8px); opacity: 0; filter: drop-shadow(0 0 0 rgba(255,51,204,0)); }
  60%  { transform: translateY(0);   opacity: 1; filter: drop-shadow(0 0 8px rgba(255,51,204,.45)); }
  100% { filter: drop-shadow(0 0 0 rgba(255,51,204,0)); }
}

/* Little badge */
.badge { display:inline-block; background:#FFD60A; color:#000; padding:.32rem .7rem;
  border-radius:.55rem; font-weight:900; letter-spacing:.3px }
</style>
""",
    unsafe_allow_html=True,
)


# =============================================================================
# Helpers
# =============================================================================
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

def reset_everything(keep_file: bool = True):
    """Πλήρες reset (για Next player). Αν keep_file=False, απαιτεί νέο upload."""
    keys_to_keep = set()
    if keep_file and "uploaded_bytes" in st.session_state:
        keys_to_keep.update({"uploaded_bytes", "uploaded_name"})
    # Αν ΘΕΣ να απαιτεί νέο upload σε κάθε Next player, σχολίασε την επόμενη γραμμή
    # και αφαίρεσε τα uploaded_* από keys_to_keep.
    # keep_file = False

    for k in list(st.session_state.keys()):
        if k not in keys_to_keep and k != "leaderboard":
            st.session_state.pop(k, None)

    # (Προαιρετικό) Μηδένισε και το file_uploader ώστε να φαίνεται "άδειο"
    # st.session_state.uploader = None

    rerun()


# =============================================================================
# Sidebar / Header
# =============================================================================
with st.sidebar:
    player = st.text_input("Player name", placeholder="e.g., Tsaf / Saro / SlotMamba")
    st.caption("Scores are stored in session memory.")

left, right = st.columns([0.78, 0.22], vertical_alignment="center")
with left:
    c1, c2 = st.columns([0.08, 0.92])
    with c1:
        try:
            st.image("cheeky_logo.png", use_container_width=True)
        except Exception:
            st.markdown("🎰")
    with c2:
        st.markdown("## Cheeky Gamblers Trivia")
        st.caption("15 random questions per round • Multiple choice • Stream-safe")
with right:
    st.markdown(
        f"<div class='name-tile'><span class='label'>PLAYER</span><span class='value'>{(player or '—')}</span></div>",
        unsafe_allow_html=True
    )


# =============================================================================
# UPLOAD / CACHE
# =============================================================================
uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"], key="uploader")

file_bytes = None
file_name = None

if uploaded is not None:
    file_bytes = uploaded.getvalue()
    file_name = uploaded.name
    st.session_state.uploaded_bytes = file_bytes
    st.session_state.uploaded_name = file_name
    save_cached_file(file_bytes)

elif "uploaded_bytes" in st.session_state:
    file_bytes = st.session_state.uploaded_bytes
    file_name = st.session_state.get("uploaded_name", "last.xlsx")

else:
    cached = load_cached_file()
    if cached:
        file_bytes = cached
        file_name = "last.xlsx"

# quick actions
a1, a2, a3 = st.columns([0.12, 0.14, 0.74])
with a1:
    if st.button("🔄 Refresh"):
        rerun()
with a2:
    if st.button("🧹 Forget file"):
        st.session_state.pop("uploaded_bytes", None)
        st.session_state.pop("uploaded_name", None)
        try:
            if CACHE_PATH.exists():
                CACHE_PATH.unlink()
        except:
            pass
        rerun()

# file guard
if not file_bytes:
    st.info("Upload an Excel (ή πάτα Refresh αν έχεις ήδη κάνει upload παλιότερα).")
    if "leaderboard" in st.session_state and st.session_state.leaderboard:
        st.markdown("### ")
        with st.container(border=True):
            st.subheader("🏆 Leaderboard (session)")
            df_lb = pd.DataFrame(st.session_state.leaderboard)
            df_lb = df_lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True])
            st.dataframe(df_lb, use_container_width=True, hide_index=True)
    st.stop()

# read excel
try:
    df = pd.read_excel(io.BytesIO(file_bytes))
except Exception as e:
    st.error(f"Could not read Excel: {e}")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]
df = df.fillna("")
missing = [c for c in REQUIRED if c not in df.columns]
if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()


# =============================================================================
# Init session state
# =============================================================================
if "quiz" not in st.session_state:
    st.session_state.quiz = build_quiz(df)
    st.session_state.current_i = 1
    for j in range(1, len(st.session_state.quiz) + 1):
        st.session_state.pop(f"q{j}", None)
        st.session_state.pop(f"q{j}_temp", None)
        st.session_state.pop(f"locked_{j}", None)
    st.session_state.last_q = None
    st.session_state.deadlines = {}

quiz = st.session_state.quiz
total_q = len(quiz)
cur = max(1, min(total_q, st.session_state.get("current_i", 1)))

# =============================================================================
# Timer per question
# =============================================================================
SECONDS_PER_Q = 45
# start/refresh timer όταν αλλάζει ερώτηση
if st.session_state.last_q != cur:
    st.session_state.last_q = cur
    now = time.time()
    st.session_state.deadlines[cur] = now + SECONDS_PER_Q
    st.session_state[f"locked_{cur}"] = False
    st.session_state.pop(f"q{cur}_temp", None)

now = time.time()
deadline = st.session_state.deadlines.get(cur, now + SECONDS_PER_Q)
remaining = max(0, int(deadline - now))
time_up = remaining <= 0
if time_up and not st.session_state.get(f"locked_{cur}", False):
    st.session_state[f"locked_{cur}"] = True


# =============================================================================
# MAIN PANEL
# =============================================================================
st.markdown("<div class='neon-panel'>", unsafe_allow_html=True)

# Progress (μέσα σε κουτί)
answered = sum(1 for j in range(1, total_q + 1) if st.session_state.get(f"q{j}") is not None)
st.markdown("<div class='progress-box'>", unsafe_allow_html=True)
st.progress(answered / max(1, total_q), text=f"Answered {answered}/{total_q}")
st.markdown("</div>", unsafe_allow_html=True)

st.markdown("---")

# Ερώτηση + timer
q = quiz[cur - 1]
st.subheader(f"Question {cur}/{total_q}")

t1, t2 = st.columns([0.16, 0.84])
with t1:
    st.markdown(f"**⏱️ {remaining}s**")
with t2:
    st.progress(remaining / SECONDS_PER_Q)

st.markdown(f"<div class='q-reveal'><h3 style='margin-top:0'>{q['q']}</h3></div>", unsafe_allow_html=True)

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
        rerun()

with nav_next:
    next_enabled = (st.session_state.get(f"q{cur}") is not None) or disabled_radio
    next_disabled = (cur == total_q) or (not next_enabled)
    if st.button("➡️ Next", disabled=next_disabled):
        st.session_state.current_i = min(total_q, cur + 1)
        rerun()

with nav_finish:
    # all_done = answered για όσες είναι answered ή ληγμένες χωρίς απάντηση δεν χρειάζεται να περιμένεις
    all_done = True
    for j in range(1, total_q + 1):
        if (st.session_state.get(f"q{j}") is None) and (not st.session_state.get(f"locked_{j}", False)):
            all_done = False
            break

    if st.button("✅ Finish round", disabled=not all_done):
        score = 0
        for j in range(1, total_q + 1):
            ans = st.session_state.get(f"q{j}")
            if ans is None:
                continue
            if norm(ans) == quiz[j - 1]["correct_norm"]:
                score += 1

        if score == total_q:
            st.subheader(f"Perfect score: {score}/{total_q} 🎉 $250!")
            st.balloons()
        else:
            st.info(f"Round complete. Score: {score}/{total_q}")

        add_score_row(player, score, total_q)

        c1, c2 = st.columns([0.25, 0.75])
        with c1:
            # Full reset (ζητάει νέο όνομα). Αν θέλεις να απαιτεί νέο upload, άλλαξε keep_file=False
            if st.button("🎲 Next player (full reset)"):
                reset_everything(keep_file=True)

st.markdown("</div>", unsafe_allow_html=True)  # close neon-panel

# Leaderboard
st.markdown("### ")
with st.container(border=True):
    st.subheader("🏆 Leaderboard (session)")
    if "leaderboard" not in st.session_state or not st.session_state.leaderboard:
        st.info("No scores yet.")
    else:
        df_lb = pd.DataFrame(st.session_state.leaderboard)
        df_lb = df_lb.sort_values(by=["score", "percent", "timestamp"], ascending=[False, False, True])
        st.dataframe(df_lb, use_container_width=True, hide_index=True)

# Auto refresh κάθε 1s για να δουλεύει οπτικά το timer
if remaining > 0:
    time.sleep(1)
    rerun()
