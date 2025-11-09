# ==============================
# Cheeky Gamblers Trivia — clean build
# ==============================

import streamlit as st
import pandas as pd
import random
from datetime import datetime, timedelta

# --------------- Settings ---------------
APP_TITLE = "Cheeky Gamblers Trivia"
SAMPLE_SIZE = 15
ENABLE_TIMER = False          # Αν θες timer 45s/ερώτηση, βάλτο True
QUESTION_SECONDS = 45
LOGO_FILE = "cheeky_logo.png"  # φρόντισε το αρχείο να υπάρχει στο root


# --------------- Styling ---------------
st.set_page_config(
    page_title=APP_TITLE,
    page_icon=LOGO_FILE,
    layout="wide",
)

NEON_CSS = """
<style>
:root {
  --brand: #FFD06A;
  --brand2:#ff4fd1;
  --panel:#0f1218;
  --panel-soft:#10131a;
  --text:#EDEEF2;
}

/* global */
html, body, [class*="css"]  {
  font-family: ui-sans-serif, system-ui, -apple-system, "Segoe UI", Roboto, "Helvetica Neue";
}

/* hide default header padding */
.block-container {
  padding-top: 1.2rem !important;
}

/* top bar */
.header-wrap {
  display:flex; align-items:center; gap:.8rem;
}
.header-title {
  font-size:1.5rem; font-weight:800; letter-spacing:.3px; color:var(--text);
}
.logo {
  width:38px; height:38px; border-radius:12px;
  box-shadow:0 0 18px rgba(255,208,106,.25);
}

/* player tag */
.player-tag {
  display:inline-flex; align-items:center; gap:.5rem;
  background:rgba(255,255,255,.05);
  border:1px solid rgba(255,208,106,.25);
  color:var(--text);
  padding:.45rem .75rem; border-radius:14px;
  box-shadow: 0 0 18px rgba(255,208,106,.2) inset;
}

/* neon panel */
.neon-panel {
  background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.08));
  border:1px solid rgba(255,255,255,.06);
  border-radius:18px;
  padding:18px 18px 14px;
  box-shadow:
    0 0 0 1px rgba(255,255,255,.03) inset,
    0 10px 35px rgba(0,0,0,.55),
    0 0 28px rgba(255,79,209,.08);
}

/* metric-like label left of timer/progress */
.badge {
  display:inline-block; font-weight:700; letter-spacing:.2px;
  font-size:.8rem; color:#20242c; background: var(--brand);
  padding:.28rem .6rem; border-radius:.55rem;
  box-shadow: 0 0 24px rgba(255,208,106,.35);
}

/* gradient progress wrapper */
.progress-wrap {
  background: #0e1015; border-radius: 18px;
  box-shadow: 0 0 24px rgba(255,208,106,.12) inset;
  padding: 12px 12px 18px 12px;
}

.progress-title {
  margin: 2px 6px 8px 6px; color: var(--text); font-weight:700;
}

/* fade for disabled options */
.choice-disabled label {
  opacity: .55;
}

/* Buttons width nicer */
button[kind="primary"] {
  width: 100%;
}
</style>
"""
st.markdown(NEON_CSS, unsafe_allow_html=True)


# --------------- Helpers ---------------
REQ_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def _now():
    return datetime.utcnow()

def _init_state():
    if "df" not in st.session_state:
        st.session_state.df = None
    if "player" not in st.session_state:
        st.session_state.player = ""
    if "quiz" not in st.session_state:
        st.session_state.quiz = None
    if "current_i" not in st.session_state:
        st.session_state.current_i = 1
    if "answers" not in st.session_state:
        st.session_state.answers = {}       # q_index -> chosen text
    if "locks" not in st.session_state:
        st.session_state.locks = {}         # q_index -> True/False
    if "deadlines" not in st.session_state:
        st.session_state.deadlines = {}     # q_index -> datetime
    if "leaderboard" not in st.session_state:
        st.session_state.leaderboard = []   # list of dicts {player, score, when}

def _clear_round(reset_file=False):
    """Καθαρισμός για νέο παίκτη/γύρο."""
    file_keep = st.session_state.df if not reset_file else None
    st.session_state.clear()
    _init_state()
    st.session_state.df = file_keep

def _load_df(upload) -> pd.DataFrame | None:
    try:
        df = pd.read_excel(upload)
        missing = [c for c in REQ_COLS if c not in df.columns]
        if missing:
            st.error(f"Missing columns. Required: {REQ_COLS}")
            return None
        # καθαρισμοί/trim
        for c in df.columns:
            if df[c].dtype == object:
                df[c] = df[c].astype(str).str.strip()
        return df
    except Exception as e:
        st.error(f"Could not read Excel: {e}")
        return None

def _build_quiz(df: pd.DataFrame):
    sample = df.sample(min(SAMPLE_SIZE, len(df)), random_state=None)
    out = []
    for _, row in sample.iterrows():
        q = str(row["Question"]).strip()
        answers = [str(row["Answer 1"]), str(row["Answer 2"]), str(row["Answer 3"]), str(row["Answer 4"])]
        correct = str(row["Correct Answer"]).strip()
        random.shuffle(answers)  # randomized order every time
        out.append({
            "question": q,
            "answers": answers,
            "correct": correct
        })
    return out

def _score_now():
    score = 0
    if not st.session_state.quiz:
        return 0
    for i, item in enumerate(st.session_state.quiz, start=1):
        sel = st.session_state.answers.get(i)
        if sel and sel == item["correct"]:
            score += 1
    return score


# --------------- Header (logo / name) ---------------
def header_section():
    col1, col2, col3 = st.columns([1, 6, 3], vertical_alignment="center")
    with col1:
        try:
            st.image(LOGO_FILE, width=38, caption=None, output_format="PNG")
        except:
            pass
    with col2:
        st.markdown(f"""
        <div class="header-wrap">
          <img src="{LOGO_FILE}" class="logo"/>
          <div class="header-title">{APP_TITLE}</div>
        </div>
        """, unsafe_allow_html=True)
    with col3:
        st.markdown('<div style="text-align:right">', unsafe_allow_html=True)
        name = st.text_input(
            "Player name",
            value=st.session_state.player,
            placeholder="Type name…",
            label_visibility="collapsed",
            key="player_input",
        )
        st.session_state.player = name.strip()
        st.markdown(f'<div class="player-tag">PLAYER&nbsp;<b>{st.session_state.player or "—"}</b></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)


# --------------- Progress in panel ---------------
def progress_panel():
    total = len(st.session_state.quiz) if st.session_state.quiz else 0
    answered = sum(1 for i in range(1, total + 1) if i in st.session_state.answers)
    with st.container():
        st.markdown('<div class="neon-panel">', unsafe_allow_html=True)
        st.markdown('<div class="progress-wrap">', unsafe_allow_html=True)
        st.markdown(f'<div class="progress-title">Answered {answered}/{total}</div>', unsafe_allow_html=True)
        st.progress(answered / total if total else 0.0)
        st.markdown('</div>', unsafe_allow_html=True)  # progress-wrap
        st.markdown('</div>', unsafe_allow_html=True)  # neon-panel


# --------------- Timer helpers ---------------
def ensure_deadline_for(i):
    if i not in st.session_state.deadlines:
        st.session_state.deadlines[i] = _now() + timedelta(seconds=QUESTION_SECONDS)

def time_remaining(i):
    if i not in st.session_state.deadlines:
        return QUESTION_SECONDS
    delta = (st.session_state.deadlines[i] - _now()).total_seconds()
    return max(0, int(delta))


# --------------- Main quiz write ---------------
def render_quiz():
    quiz = st.session_state.quiz
    i = st.session_state.current_i
    total = len(quiz)

    # progress (πάνω από την ερώτηση)
    progress_panel()

    # αν έχουμε τελειώσει
    if i > total:
        score = _score_now()
        st.success(f"✅ Finished! Score: {score}/{total}")
        # Leaderboard (in-session)
        if st.session_state.player:
            st.session_state.leaderboard.append({
                "player": st.session_state.player,
                "score": score,
                "when": datetime.utcnow().isoformat()
            })
        # Buttons
        colA, colB = st.columns([1,1])
        with colA:
            if st.button("🎲 Next player (new 15)", use_container_width=True, type="primary"):
                _clear_round(reset_file=False)
                st.experimental_rerun()
        with colB:
            if st.button("♻️ Full reset (clear file)", use_container_width=True):
                _clear_round(reset_file=True)
                st.experimental_rerun()

        # show quick leaderboard
        if st.session_state.leaderboard:
            st.subheader("Leaderboard (session)")
            lb = pd.DataFrame(st.session_state.leaderboard)
            lb = lb.sort_values(["score","when"], ascending=[False, True]).reset_index(drop=True)
            st.dataframe(lb, use_container_width=True, hide_index=True)
        return

    q = quiz[i-1]  # 0-based
    st.subheader(f"Question {i}/{total}")
    st.markdown(f"**{q['question']}**")

    # TIMER (αν ενεργό)
    locked = st.session_state.locks.get(i, False)

    if ENABLE_TIMER:
        ensure_deadline_for(i)
        remain = time_remaining(i)
        badge = f'<span class="badge">⏱ {remain}s</span>'
        st.markdown(badge, unsafe_allow_html=True)

        if remain <= 0:
            # κλείδωσε την ερώτηση
            st.session_state.locks[i] = True
            locked = True

        # auto-refresh όσο μετράει
        if not locked:
            st.experimental_rerun()

    # render options
    disabled_class = " choice-disabled" if locked else ""
    with st.container():
        st.markdown(f'<div class="neon-panel{disabled_class}">', unsafe_allow_html=True)

        # current selection temp
        sel_key = f"q{i}_temp"
        prev = st.session_state.answers.get(i)
        index_init = None
        if prev and prev in q["answers"]:
            index_init = q["answers"].index(prev)

        choice = st.radio(
            "Pick one:",
            options=q["answers"],
            index=index_init if index_init is not None else None,
            key=sel_key,
            disabled=locked,
            label_visibility="collapsed"
        )

        col1, col2 = st.columns([1,1])
        with col1:
            if st.button("✅ Submit", use_container_width=True, disabled=locked):
                if choice:
                    st.session_state.answers[i] = choice
                    st.session_state.locks[i] = True
                    st.experimental_rerun()
                else:
                    st.warning("Pick an answer first.")
        with col2:
            # next enabled μόνο αν υπάρχει answer ή είναι κλειδωμένη
            can_next = (i in st.session_state.answers) or locked
            if st.button("➡️ Next", use_container_width=True, disabled=not can_next):
                st.session_state.current_i = i + 1
                # reset timer for next Q
                if ENABLE_TIMER and (i+1) not in st.session_state.deadlines:
                    st.session_state.deadlines[i+1] = _now() + timedelta(seconds=QUESTION_SECONDS)
                st.experimental_rerun()

        st.markdown("</div>", unsafe_allow_html=True)  # neon panel


# --------------- App ---------------
def main():
    _init_state()
    header_section()

    # Upload area
    with st.container():
        st.markdown('<div class="neon-panel">', unsafe_allow_html=True)
        up = st.file_uploader("Upload your Excel (.xlsx) file", type=["xlsx"], label_visibility="visible")
        if up:
            df = _load_df(up)
            if df is not None:
                st.session_state.df = df
        if st.session_state.df is not None:
            st.caption(f"Loaded file with {len(st.session_state.df)} rows.")
        st.markdown('</div>', unsafe_allow_html=True)

    # Start quiz (only if έχουμε df & player)
    if st.session_state.df is not None and st.session_state.player:
        if st.session_state.quiz is None:
            st.session_state.quiz = _build_quiz(st.session_state.df)
            st.session_state.current_i = 1
            st.session_state.answers = {}
            st.session_state.locks = {}
            st.session_state.deadlines = {}
            if ENABLE_TIMER and st.session_state.quiz:
                st.session_state.deadlines[1] = _now() + timedelta(seconds=QUESTION_SECONDS)

        render_quiz()
    else:
        st.info("• Upload Excel and set a player name to start.")


if __name__ == "__main__":
    main()
