# ==============================
# Cheeky Gamblers Trivia — fixed layout + timer
# ==============================

import streamlit as st
import pandas as pd
import random, time
from datetime import datetime, timedelta

# --------------- Settings ---------------
APP_TITLE = "Cheeky Gamblers Trivia"
SAMPLE_SIZE = 15
ENABLE_TIMER = True           # ⬅️ Timer ON
QUESTION_SECONDS = 45
LOGO_FILE = "cheeky_logo.png"  # φρόντισε να υπάρχει στο root

# --------------- Page / Theme ---------------
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
.block-container { padding-top: 1.0rem !important; }
html, body, [class*="css"]{font-family: ui-sans-serif,system-ui,-apple-system,"Segoe UI",Roboto;}

/* header */
.header-row { display:flex; align-items:center; gap:12px; }
.header-title { font-size:1.5rem; font-weight:800; letter-spacing:.3px; color:var(--text); }
.logo { width:40px; height:40px; border-radius:12px; box-shadow:0 0 18px rgba(255,208,106,.25); }

/* player tag + input wrapper */
.player-wrap { text-align:right; }
.player-tag {
  display:inline-flex; align-items:center; gap:.5rem; margin-top:.3rem;
  background:rgba(255,255,255,.05); border:1px solid rgba(255,208,106,.25);
  color:var(--text); padding:.45rem .75rem; border-radius:14px;
  box-shadow: 0 0 18px rgba(255,208,106,.2) inset;
}

/* neon panel */
.neon-panel {
  background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.08));
  border:1px solid rgba(255,255,255,.06);
  border-radius:18px;
  padding:18px 18px 16px;
  box-shadow:
    0 0 0 1px rgba(255,255,255,.03) inset,
    0 10px 35px rgba(0,0,0,.55),
    0 0 28px rgba(255,79,209,.08);
  margin-bottom: 14px;
}

/* progress panel */
.progress-wrap { background:#0e1015; border-radius:18px; padding:12px 12px 18px; box-shadow:0 0 24px rgba(255,208,106,.12) inset; }
.progress-title { margin:2px 6px 8px 6px; color:var(--text); font-weight:700; }

/* badge (timer) */
.badge {
  display:inline-block; font-weight:700; letter-spacing:.2px;
  font-size:.8rem; color:#20242c; background: var(--brand);
  padding:.28rem .6rem; border-radius:.55rem;
  box-shadow: 0 0 24px rgba(255,208,106,.35);
}

.choice-disabled label { opacity:.55; }
button[kind="primary"] { width:100%; }
</style>
"""
st.markdown(NEON_CSS, unsafe_allow_html=True)

# --------------- Helpers ---------------
REQ_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def _now(): return datetime.utcnow()

def _init_state():
    ss = st.session_state
    ss.setdefault("df", None)
    ss.setdefault("player", "")
    ss.setdefault("quiz", None)
    ss.setdefault("current_i", 1)
    ss.setdefault("answers", {})      # q->text
    ss.setdefault("locks", {})        # q->bool
    ss.setdefault("deadlines", {})    # q->datetime
    ss.setdefault("leaderboard", [])
    ss.setdefault("_tick_last", time.time())

def _clear_round(reset_file=False):
    keep = st.session_state.df if not reset_file else None
    st.session_state.clear()
    _init_state()
    st.session_state.df = keep

def _load_df(upload):
    try:
        df = pd.read_excel(upload)
        missing = [c for c in REQ_COLS if c not in df.columns]
        if missing:
            st.error(f"Missing columns. Required: {REQ_COLS}")
            return None
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
        random.shuffle(answers)
        out.append({"question": q, "answers": answers, "correct": correct})
    return out

def _score_now():
    score = 0
    quiz = st.session_state.quiz or []
    for i, item in enumerate(quiz, start=1):
        sel = st.session_state.answers.get(i)
        if sel and sel == item["correct"]:
            score += 1
    return score

# --------------- Header ---------------
def header_section():
    c1, c2, c3 = st.columns([0.6, 6, 3.4], vertical_alignment="center")
    with c1:
        try: st.image(LOGO_FILE, width=40)
        except: st.write("")
    with c2:
        st.markdown(f"""
        <div class="header-row">
          <img src="{LOGO_FILE}" class="logo"/>
          <div class="header-title">{APP_TITLE}</div>
        </div>
        """, unsafe_allow_html=True)
    with c3:
        st.markdown('<div class="player-wrap">', unsafe_allow_html=True)
        name = st.text_input("Player name", value=st.session_state.player, placeholder="Type name…", label_visibility="collapsed")
        st.session_state.player = name.strip()
        st.markdown(f'<div class="player-tag">PLAYER&nbsp;<b>{st.session_state.player or "—"}</b></div>', unsafe_allow_html=True)
        st.markdown('</div>', unsafe_allow_html=True)

# --------------- Progress ---------------
def progress_panel():
    quiz = st.session_state.quiz or []
    total = len(quiz)
    answered = sum(1 for i in range(1, total+1) if i in st.session_state.answers)
    st.markdown('<div class="neon-panel">', unsafe_allow_html=True)
    st.markdown('<div class="progress-wrap">', unsafe_allow_html=True)
    st.markdown(f'<div class="progress-title">Answered {answered}/{total}</div>', unsafe_allow_html=True)
    st.progress(answered/total if total else 0)
    st.markdown('</div></div>', unsafe_allow_html=True)

# --------------- Timer utils ---------------
def ensure_deadline_for(i):
    ss = st.session_state
    if i not in ss.deadlines:
        ss.deadlines[i] = _now() + timedelta(seconds=QUESTION_SECONDS)

def time_remaining(i):
    ss = st.session_state
    if i not in ss.deadlines:
        return QUESTION_SECONDS
    return max(0, int((ss.deadlines[i]-_now()).total_seconds()))

def auto_refresh_every(sec=1):
    """Προκαλεί 'ήπιο' auto-refresh ~κάθε sec, χωρίς сторон libs."""
    now = time.time()
    if now - st.session_state._tick_last >= sec:
        st.session_state._tick_last = now
        st.experimental_rerun()

# --------------- Quiz Render ---------------
def render_quiz():
    quiz = st.session_state.quiz
    i = st.session_state.current_i
    total = len(quiz)

    # progress
    progress_panel()

    # Finish
    if i > total:
        score = _score_now()
        st.success(f"✅ Finished! Score: {score}/{total}")

        colA, colB = st.columns([1,1])
        with colA:
            if st.button("🎲 Next player (new 15)", type="primary", use_container_width=True):
                _clear_round(reset_file=False)
                st.experimental_rerun()
        with colB:
            if st.button("♻️ Full reset (clear file)", use_container_width=True):
                _clear_round(reset_file=True)
                st.experimental_rerun()

        # leaderboard (προαιρετικά)
        if st.session_state.player:
            st.session_state.leaderboard.append({
                "player": st.session_state.player,
                "score": score,
                "when": datetime.utcnow().isoformat()
            })
        if st.session_state.leaderboard:
            st.subheader("Leaderboard (session)")
            lb = pd.DataFrame(st.session_state.leaderboard).sort_values(["score","when"], ascending=[False, True])
            st.dataframe(lb, hide_index=True, use_container_width=True)
        return

    q = quiz[i-1]
    st.subheader(f"Question {i}/{total}")
    st.markdown(f"**{q['question']}**")

    # Timer
    locked = st.session_state.locks.get(i, False)
    if ENABLE_TIMER and not locked:
        ensure_deadline_for(i)
        remain = time_remaining(i)
        st.markdown(f'<span class="badge">⏱ {remain}s</span>', unsafe_allow_html=True)
        if remain <= 0:
            st.session_state.locks[i] = True
            locked = True
        else:
            auto_refresh_every(1)  # trigger re-render ανά ~1s

    # Neon panel για επιλογές + κουμπιά
    disabled_class = " choice-disabled" if locked else ""
    st.markdown(f'<div class="neon-panel{disabled_class}">', unsafe_allow_html=True)

    sel_key = f"q{i}_temp"
    prev = st.session_state.answers.get(i)
    init_index = q["answers"].index(prev) if prev in q["answers"] else None

    choice = st.radio(
        "Pick one:",
        options=q["answers"],
        index=init_index if init_index is not None else None,
        key=sel_key,
        disabled=locked,
        label_visibility="collapsed",
    )

    c1, c2 = st.columns([1,1])
    with c1:
        if st.button("✅ Submit", use_container_width=True, disabled=locked):
            if choice:
                st.session_state.answers[i] = choice
                st.session_state.locks[i] = True
                st.experimental_rerun()
            else:
                st.warning("Pick an answer first.")
    with c2:
        can_next = (i in st.session_state.answers) or locked
        if st.button("➡️ Next", use_container_width=True, disabled=not can_next):
            st.session_state.current_i = i + 1
            if ENABLE_TIMER:  # set deadline for next
                st.session_state.deadlines[i+1] = _now() + timedelta(seconds=QUESTION_SECONDS)
            st.experimental_rerun()

    st.markdown('</div>', unsafe_allow_html=True)  # neon-panel


# --------------- Main ---------------
def main():
    _init_state()
    header_section()

    # Upload panel (πάντα σε neon)
    st.markdown('<div class="neon-panel">', unsafe_allow_html=True)
    up = st.file_uploader("Upload your Excel (.xlsx) file", type=["xlsx"], label_visibility="visible")
    if up:
        df = _load_df(up)
        if df is not None:
            st.session_state.df = df
    if st.session_state.df is not None:
        st.caption(f"Loaded file with {len(st.session_state.df)} rows.")
    st.markdown('</div>', unsafe_allow_html=True)

    # Start quiz όταν έχουμε αρχείο + player
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
        st.info("• Upload Excel και βάλε player name για να ξεκινήσεις.")

if __name__ == "__main__":
    main()
