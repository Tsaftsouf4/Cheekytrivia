import time
import random
from datetime import datetime
import pandas as pd
import streamlit as st

# ====================================================
# PAGE SETUP
# ====================================================
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="🦝",
    layout="wide",
)

CSS = """
<style>
body, .stApp {
  background-color: #0e1117;
  color: #fff;
  font-family: 'Inter', sans-serif;
}
.glow-logo {
  display: flex;
  align-items: center;
  gap: 0.6rem;
}
.glow-logo img {
  width: 42px;
  height: 42px;
  filter: drop-shadow(0 0 10px rgba(255, 215, 0, .4));
}
.glow-logo h2 {
  color: #ffd54a;
  text-shadow: 0 0 10px rgba(255,215,0,.4);
  margin: 0;
}

.glow-card {
  background: #0e1117;
  border-radius: 18px;
  padding: 10px 14px;
  box-shadow: 0 0 25px rgba(255, 214, 10, 0.05);
  border: 1px solid rgba(255,255,255,0.06);
}

.meter {
  background: rgba(255,255,255,0.05);
  border-radius: 14px;
  height: 36px;
  position: relative;
  overflow: hidden;
  box-shadow: inset 0 0 10px rgba(0,0,0,0.5), 0 0 20px rgba(255,255,0,0.06);
}
.meter__fill {
  height: 100%;
  width: 0%;
  border-radius: 14px;
  background: linear-gradient(90deg, #ffd54a 0%, #ffa44a 50%, #ff4ad8 100%);
  box-shadow: 0 0 20px rgba(255, 214, 10, 0.35);
  transition: width .35s ease;
}
.meter__label {
  position: absolute;
  left: 10px;
  top: 50%;
  transform: translateY(-50%);
  font-weight: 700;
  color: #fff;
  text-shadow: 0 1px 2px rgba(0,0,0,0.6);
  font-size: 14px;
}

.timerbar {
  margin-top: 8px;
  height: 6px;
  background: rgba(255,255,255,0.08);
  border-radius: 6px;
  overflow: hidden;
  position: relative;
  box-shadow: inset 0 0 8px rgba(0,0,0,0.5);
}
.timerbar__fill {
  height: 100%;
  width: 100%;
  background: #ffd54a;
  box-shadow: 0 0 14px rgba(255, 214, 10, 0.8);
  transition: width .35s linear;
}

.timer-big {
  text-align: center;
  font-size: 32px;
  font-weight: 800;
  color: #ffd54a;
  text-shadow: 0 0 15px rgba(255,215,0,.5);
  margin: 0.6rem 0 1rem 0;
}

.badge {
  display:inline-block;
  padding: .35rem .75rem;
  border-radius: 999px;
  background: rgba(255,255,255,0.08);
  border: 1px solid rgba(255,255,255,0.12);
  color: #ffd54a;
  font-weight: 700;
}
</style>
"""
st.markdown(CSS, unsafe_allow_html=True)

# ====================================================
# STATE / CONSTANTS
# ====================================================
REQUIRED_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]
ROUND_SIZE = 15
PER_QUESTION_SECONDS = 45

def init_state():
    ss = st.session_state
    ss.setdefault("started", False)
    ss.setdefault("df", None)
    ss.setdefault("order", [])
    ss.setdefault("qi", 0)
    ss.setdefault("score", 0)
    ss.setdefault("answered_this", False)
    ss.setdefault("selected", None)
    ss.setdefault("player", "")
    ss.setdefault("deadline", None)
    ss.setdefault("leaderboard", [])

# ====================================================
# CORE FUNCTIONS
# ====================================================
def load_excel(file):
    df = pd.read_excel(file)
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return df.reset_index(drop=True)

def start_game():
    ss = st.session_state
    n = min(ROUND_SIZE, len(ss.df))
    ss.order = random.sample(list(range(len(ss.df))), n)
    ss.qi = 0
    ss.score = 0
    ss.answered_this = False
    ss.selected = None
    ss.started = True
    ss.deadline = time.time() + PER_QUESTION_SECONDS
    st.rerun()

def next_question():
    ss = st.session_state
    ss.qi += 1
    ss.answered_this = False
    ss.selected = None
    if ss.qi >= len(ss.order):
        finish_round()
        st.stop()
    ss.deadline = time.time() + PER_QUESTION_SECONDS
    st.rerun()

def reset_for_next_player():
    ss = st.session_state
    ss.started = False
    ss.order = []
    ss.qi = 0
    ss.score = 0
    ss.answered_this = False
    ss.selected = None
    ss.deadline = None
    st.rerun()

# ====================================================
# UI COMPONENTS
# ====================================================
def render_header():
    left, mid, right = st.columns([1,5,2])
    with left:
        st.markdown(
            "<div class='glow-logo'><img src='https://i.ibb.co/jLgbjCg/cheeky-gamblers-logo.png'/><h2>Cheeky Gamblers Trivia</h2></div>",
            unsafe_allow_html=True
        )
    with right:
        st.text_input("Type name…", key="player", placeholder="Player name")
        player_show = st.session_state.player or "—"
        st.markdown(f"**PLAYER**  <span class='badge'>{player_show}</span>", unsafe_allow_html=True)

def render_loader():
    st.subheader("Upload your Excel (.xlsx) file")
    file = st.file_uploader("Drag and drop file here", type=["xlsx"], label_visibility="collapsed")
    if file:
        try:
            st.session_state.df = load_excel(file)
            st.success(f"Loaded file with {len(st.session_state.df)} rows. Using {min(ROUND_SIZE, len(st.session_state.df))} randomized questions.")
        except Exception as e:
            st.error(str(e))

def render_start():
    disabled = not (st.session_state.df is not None and st.session_state.player.strip())
    st.button("🚀 Start", type="primary", use_container_width=True, disabled=disabled, on_click=start_game)
    if disabled:
        st.info("• Upload Excel **και** βάλε player name για να ξεκινήσεις.")

def progress_and_timer_box():
    ss = st.session_state
    total = len(ss.order) if ss.order else 1
    answered = ss.qi if ss.started else 0
    progress_pct = int(100 * answered / total)
    rem = 0
    if ss.deadline:
        rem = max(0, int(round(ss.deadline - time.time())))
    timer_pct = max(0.0, min(1.0, (ss.deadline - time.time()) / PER_QUESTION_SECONDS)) * 100.0 if ss.deadline else 0
    st.markdown('<div class="glow-card">', unsafe_allow_html=True)
    st.markdown(
        f"""
        <div class="meter">
          <div class="meter__fill" style="width:{progress_pct}%"></div>
          <div class="meter__label">Answered {answered}/{total}</div>
        </div>
        <div class="timerbar">
          <div class="timerbar__fill" style="width:{timer_pct}%"></div>
        </div>
        """,
        unsafe_allow_html=True
    )
    st.markdown("</div>", unsafe_allow_html=True)
    return rem

def render_live_timer(rem):
    """Big visible countdown (live refresh every 1s)."""
    ph = st.empty()
    while rem > 0:
        mins, secs = divmod(rem, 60)
        ph.markdown(f"<div class='timer-big'>⏱️ {mins:02d}:{secs:02d}</div>", unsafe_allow_html=True)
        time.sleep(1)
        rem = max(0, int(round(st.session_state.deadline - time.time())))
        if rem <= 0:
            ph.markdown(f"<div class='timer-big'>⏱️ 00:00</div>", unsafe_allow_html=True)
            break

def render_question():
    ss = st.session_state
    df = ss.df
    idx = ss.order[ss.qi]
    row = df.iloc[idx]

    st.markdown(f"### Question {ss.qi+1}/{len(ss.order)}")
    st.write(row["Question"])

    # live countdown
    rem = max(0, int(round(ss.deadline - time.time())))
    render_live_timer(rem)

    options = [row["Answer 1"], row["Answer 2"], row["Answer 3"], row["Answer 4"]]
    random.seed(f"{idx}-{ss.qi}")
    random.shuffle(options)
    ss.selected = st.radio("Choose an answer:", options, index=None, label_visibility="collapsed")

    can_submit = (ss.selected is not None) and (not ss.answered_this) and (rem > 0)
    col1, col2 = st.columns([1,1])
    with col1:
        submit = st.button("✅ Submit", use_container_width=True, disabled=not can_submit)
    with col2:
        next_btn = st.button("➡️ Next", use_container_width=True, disabled=not (ss.answered_this or rem == 0))

    if submit and can_submit:
        correct = str(row["Correct Answer"]).strip()
        if str(ss.selected).strip() == correct:
            ss.score += 1
            st.success("Correct!")
        else:
            st.error(f"Wrong. Correct answer: **{correct}**")
        ss.answered_this = True
        st.stop()

    if next_btn and (ss.answered_this or rem == 0):
        next_question()

def finish_round():
    ss = st.session_state
    st.success(f"Round finished! Score: **{ss.score}/{len(ss.order)}**")
    if ss.player.strip():
        ss.leaderboard.append((ss.player.strip(), ss.score, datetime.now().strftime("%Y-%m-%d %H:%M")))
    if ss.leaderboard:
        st.markdown("### Leaderboard (session)")
        lb = pd.DataFrame(ss.leaderboard, columns=["Player", "Score", "When"])
        lb = lb.sort_values(["Score", "When"], ascending=[False, True], ignore_index=True)
        st.dataframe(lb, use_container_width=True, height=220)
    st.button("🔁 Next Player", on_click=reset_for_next_player, use_container_width=True, type="primary")

# ====================================================
# MAIN
# ====================================================
def main():
    init_state()
    render_header()
    st.divider()
    render_loader()

    if not st.session_state.started:
        st.divider()
        render_start()
        return

    remaining = progress_and_timer_box()
    st.divider()
    render_question()

if __name__ == "__main__":
    main()
