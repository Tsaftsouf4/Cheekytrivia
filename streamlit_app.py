import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime

# =============== PAGE ===============
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",
    layout="wide",
)

# =============== CSS ===============
st.markdown("""
<style>
/* Background */
[data-testid="stAppViewContainer"] > .main {
  background: linear-gradient(135deg,#0b0f14 0%,#111826 60%,#001a2c 100%);
  background-attachment: fixed;
}
body:before{
  content:""; position:fixed; inset:0;
  background:url('cheeky_bg.jpg') center/cover no-repeat;
  opacity:.15; pointer-events:none; z-index:-1;
}

/* Layout */
.block-container{ padding-top:6rem; padding-bottom:2rem; max-width:1180px; }

/* Neon panel */
.neon-panel{
  border-radius:18px; padding:24px; background:rgba(10,14,20,.68);
  box-shadow:0 0 0 1px rgba(255,255,255,.04) inset,
             0 0 28px rgba(255,214,10,.14),
             0 0 48px rgba(255,51,204,.10);
  backdrop-filter:blur(6px); -webkit-backdrop-filter:blur(6px);
}

/* Name tile */
.name-tile{
  display:inline-flex; flex-direction:column; align-items:center; justify-content:center;
  min-width:160px; padding:.65rem 1rem; border-radius:12px;
  background:rgba(255,214,10,.10); border:1px solid rgba(255,214,10,.40);
  box-shadow:0 0 12px rgba(255,214,10,.28), inset 0 0 8px rgba(255,214,10,.15);
  color:#fff; text-align:center;
}
.name-tile .label{ font-size:.7rem; font-weight:600; letter-spacing:.8px; color:rgba(255,255,255,.75); margin-bottom:.15rem; }
.name-tile .value{ font-size:1.2rem; font-weight:800; color:#FFD60A; text-shadow:0 0 6px rgba(255,214,10,.45); }

/* Progress glow */
[data-testid="stProgress"] > div > div{
  box-shadow:0 0 16px rgba(255,214,10,.35);
  background:linear-gradient(90deg,#FFD60A,#FF33CC);
}

/* Put progresses nicely inside a rounded box */
.progress-wrap{
  padding:12px 14px; border-radius:14px;
  background:rgba(255,255,255,.02);
  box-shadow: inset 0 0 0 1px rgba(255,255,255,.03);
  margin-bottom:14px;
}

/* Question reveal */
.q-reveal{ animation:qslide .55s ease-out; color:#f1f4f8; }
@keyframes qslide{
  0%{ transform:translateY(8px); opacity:0; filter:drop-shadow(0 0 0 rgba(255,51,204,0)); }
  60%{ transform:translateY(0); opacity:1; filter:drop-shadow(0 0 8px rgba(255,51,204,.45)); }
  100%{ filter:drop-shadow(0 0 0 rgba(255,51,204,0)); }
}
</style>
""", unsafe_allow_html=True)

# =============== HELPERS ===============
REQUIRED = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def norm(x:str)->str:
    return str(x).strip().lower().replace("’","'").replace("“","\"").replace("”","\"")

def build_quiz(df: pd.DataFrame, n=15):
    sample = df.sample(n=min(n,len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    out=[]
    for _,r in sample.iterrows():
        opts=[str(r["Answer 1"]), str(r["Answer 2"]), str(r["Answer 3"]), str(r["Answer 4"])]
        random.shuffle(opts)
        out.append({
            "q": str(r["Question"]),
            "opts": opts,
            "correct": str(r["Correct Answer"]),
            "correct_norm": norm(r["Correct Answer"]),
        })
    return out

def add_score_row(player:str, score:int, total:int):
    percent = round(100*score/max(1,total), 2)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if "leaderboard" not in st.session_state: st.session_state.leaderboard=[]
    st.session_state.leaderboard.append(
        {"timestamp":ts, "player":player or "Anonymous", "score":score, "total":total, "percent":percent}
    )

def _rerun():
    if hasattr(st,"rerun"): st.rerun()
    else: st.experimental_rerun()

# =============== SIDEBAR (player) ===============
with st.sidebar:
    st.session_state.player = st.text_input(
        "Player name", value=st.session_state.get("player",""), placeholder="e.g., Tsaf / Saro / SlotMamba"
    )
    st.caption("Scores are stored in session memory.")

# =============== HEADER ===============
left, right = st.columns([0.75,0.25], vertical_alignment="center")
with left:
    c1, c2 = st.columns([0.08, 0.92])
    with c1:
        try: st.image("cheeky_logo.png", use_container_width=True)
        except: st.markdown("🎰")
    with c2:
        st.markdown("### Cheeky Gamblers Trivia")
        st.caption("15 random questions per round • Multiple choice • Stream-safe")
with right:
    st.markdown(
        f"<div class='name-tile'><span class='label'>PLAYER</span><span class='value'>{(st.session_state.get('player') or '—')}</span></div>",
        unsafe_allow_html=True
    )

# =============== UPLOAD ===============
uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"], key="uploader")

if uploaded is None:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
    if st.session_state.get("leaderboard"):
        st.markdown("### ")
        with st.container(border=True):
            st.subheader("🏆 Leaderboard (session)")
            lb = pd.DataFrame(st.session_state.leaderboard)
            lb = lb.sort_values(by=["score","percent","timestamp"], ascending=[False,False,True])
            st.dataframe(lb, use_container_width=True, hide_index=True)
    st.stop()

# read & validate
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

# =============== STATE ===============
if "started" not in st.session_state:
    st.session_state.started = False

def reset_round(keep_upload=True):
    """Full reset for Next player (keeps leaderboard, optionally keeps upload)."""
    for j in list(st.session_state.keys()):
        if j.startswith("q") or j.startswith("locked_") or j in {
            "quiz","current_i","last_q","deadlines"
        }:
            st.session_state.pop(j, None)
    st.session_state.started = False
    st.session_state.player = ""
    # keep upload by default; if you want to force re-upload uncomment next line
    # st.session_state.uploader = None

# Show Start screen if not started
if not st.session_state.started:
    # Small panel with instructions + Start
    with st.container(border=True):
        st.subheader("Ready to start?")
        st.write("• Write a **player name** and press **Start** to begin a new 15-question round.")
        start_disabled = not bool(st.session_state.get("player","").strip())
        if st.button("🚀 Start", disabled=start_disabled, use_container_width=True, type="primary"):
            # init a new quiz
            st.session_state.quiz = build_quiz(df)
            st.session_state.current_i = 1
            for j in range(1, len(st.session_state.quiz)+1):
                st.session_state.pop(f"q{j}", None)
                st.session_state.pop(f"q{j}_temp", None)
            st.session_state.last_q = None
            st.session_state.deadlines = {}
            st.session_state.started = True
            _rerun()

    # leaderboard
    st.markdown("### ")
    with st.container(border=True):
        st.subheader("🏆 Leaderboard (session)")
        if not st.session_state.get("leaderboard"):
            st.info("No scores yet.")
        else:
            lb = pd.DataFrame(st.session_state.leaderboard)
            lb = lb.sort_values(by=["score","percent","timestamp"], ascending=[False,False,True])
            st.dataframe(lb, use_container_width=True, hide_index=True)

    st.stop()

# =============== QUIZ RUNNING ===============
quiz = st.session_state.quiz
total_q = len(quiz)
cur = max(1, min(total_q, st.session_state.get("current_i", 1)))

# Per-question timer
SECONDS_PER_Q = 45
if st.session_state.get("last_q") != cur:
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

# ===== MAIN PANEL =====
st.markdown("<div class='neon-panel'>", unsafe_allow_html=True)

# Progress (wrapped so it sits inside the box)
answered = sum(1 for j in range(1, total_q+1) if st.session_state.get(f"q{j}") is not None)
st.markdown("<div class='progress-wrap'>", unsafe_allow_html=True)
st.progress(answered/max(1,total_q), text=f"Answered {answered}/{total_q}")
st.markdown("</div>", unsafe_allow_html=True)

st.subheader(f"Question {cur}/{total_q}")
# Timer summary + timer bar (also inside wrapper)
timer_col1, timer_col2 = st.columns([0.18, 0.82])
with timer_col1:
    st.markdown(f"**⏱️ {remaining}s**")
with timer_col2:
    st.markdown("<div class='progress-wrap'>", unsafe_allow_html=True)
    st.progress(remaining/max(1,SECONDS_PER_Q))
    st.markdown("</div>", unsafe_allow_html=True)

q = quiz[cur-1]
st.markdown(f"<div class='q-reveal'><h3 style='margin-top:0'>{q['q']}</h3></div>", unsafe_allow_html=True)

disabled_radio = st.session_state.get(f"locked_{cur}", False)
choice_temp = st.radio("Pick your answer:", q["opts"], index=None, key=f"q{cur}_temp", disabled=disabled_radio)
if choice_temp is not None and not disabled_radio:
    st.session_state[f"q{cur}"] = choice_temp
if disabled_radio and st.session_state.get(f"q{cur}") is None:
    st.warning("Time's up — no answers accepted for this question.")

st.markdown("---")

# Nav
nav_prev, nav_next, nav_finish = st.columns([0.2, 0.2, 0.6])
with nav_prev:
    if st.button("⬅️ Previous", disabled=(cur==1)):
        st.session_state.current_i = max(1, cur-1); _rerun()

with nav_next:
    next_enabled = (st.session_state.get(f"q{cur}") is not None) or disabled_radio
    next_disabled = (cur==total_q) or (not next_enabled)
    if st.button("➡️ Next", disabled=next_disabled):
        st.session_state.current_i = min(total_q, cur+1); _rerun()

with nav_finish:
    all_done = True
    for j in range(1, total_q+1):
        if (st.session_state.get(f"q{j}") is None) and (not st.session_state.get(f"locked_{j}", False)):
            all_done = False; break
    if st.button("✅ Finish round", disabled=not all_done):
        score = 0
        for j in range(1, total_q+1):
            ans = st.session_state.get(f"q{j}")
            if ans is None: continue
            if norm(ans) == quiz[j-1]["correct_norm"]:
                score += 1
        if score == total_q:
            st.subheader(f"Perfect score: {score}/{total_q} 🎉 $250!"); st.balloons()
        else:
            st.info(f"Round complete. Score: {score}/{total_q}")
        add_score_row(st.session_state.get("player",""), score, total_q)

        # -------- FULL RESET for next player --------
        if st.button("🎲 Next player", type="primary"):
            reset_round(keep_upload=True)
            _rerun()

st.markdown("</div>", unsafe_allow_html=True)

# Leaderboard (always visible)
st.markdown("### ")
with st.container(border=True):
    st.subheader("🏆 Leaderboard (session)")
    if not st.session_state.get("leaderboard"):
        st.info("No scores yet.")
    else:
        lb = pd.DataFrame(st.session_state.leaderboard)
        lb = lb.sort_values(by=["score","percent","timestamp"], ascending=[False,False,True])
        st.dataframe(lb, use_container_width=True, hide_index=True)

# Auto-refresh 1s while countdown is running
if remaining > 0:
    time.sleep(1); _rerun()
