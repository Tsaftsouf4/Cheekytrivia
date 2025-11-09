import time
import random
import pandas as pd
import streamlit as st

# ======================
#  App metadata / Config
# ======================
APP_TITLE   = "Cheeky Gamblers Trivia"
LOGO_FILE   = "cheeky_logo.png"    # Βάλε εδώ το δικό σου logo (στο root)
ROUND_SEC   = 45                   # 45s ανά ερώτηση
REQUIRED_COLS = ['#', 'Question', 'Answer 1', 'Answer 2', 'Answer 3', 'Answer 4', 'Correct Answer']

st.set_page_config(page_title=APP_TITLE, page_icon=LOGO_FILE, layout="wide")

# ======================
#  CSS (neon theme)
# ======================
NEON_CSS = """
<style>
:root {
  --brand: #FFD06A;
  --brand2:#ff4fd1;
  --panel:#0f1218;
  --panel-soft:#10131a;
  --text:#EDEEF2;
}
.main .block-container{
  max-width: 1180px;
  padding-top: 1rem !important;
  margin: 0 auto;
}

/* Header */
.header-row { display:flex; align-items:center; gap:12px; }
.header-title { font-size:1.5rem; font-weight:800; letter-spacing:.3px; color:var(--text); }
.logo { width:40px; height:40px; border-radius:12px; box-shadow:0 0 18px rgba(255,208,106,.25); }

/* Neon panel */
.neon-panel {
  background: linear-gradient(180deg, rgba(255,255,255,.02), rgba(0,0,0,.08));
  border:1px solid rgba(255,255,255,.06);
  border-radius:18px;
  padding:14px 16px;
  box-shadow:
    0 0 0 1px rgba(255,255,255,.03) inset,
    0 10px 35px rgba(0,0,0,.55),
    0 0 28px rgba(255,79,209,.08);
  margin-bottom: 14px;
}

/* Player card */
.player-tag {
  display:inline-flex; align-items:center; gap:.5rem;
  background:rgba(255,255,255,.05); border:1px solid rgba(255,208,106,.25);
  color:var(--text); padding:.45rem .75rem; border-radius:14px;
  box-shadow: 0 0 18px rgba(255,208,106,.2) inset;
  font-weight:700;
}
.player-input div[data-testid="stTextInput"]{ max-width: 320px; }
.player-input input{ height: 38px; border-radius: 12px; }

/* Progress wrap */
.progress-title { margin:2px 6px 8px 6px; color:var(--text); font-weight:700; }

/* Timer badge */
.timer-badge{
  display:inline-flex; gap:.35rem; align-items:center;
  background:linear-gradient(90deg, var(--brand), var(--brand2));
  color:#181a20; font-weight:800;
  padding:.35rem .65rem; border-radius:12px; box-shadow:0 0 14px rgba(255,79,209,.25);
}
</style>
"""
st.markdown(NEON_CSS, unsafe_allow_html=True)

# ======================
#  Helpers
# ======================
def neon_panel_start():
    st.markdown('<div class="neon-panel">', unsafe_allow_html=True)

def neon_panel_end():
    st.markdown('</div>', unsafe_allow_html=True)

def ensure_state():
    ss = st.session_state
    ss.setdefault("player", "")
    ss.setdefault("player_input", "")
    ss.setdefault("questions", [])
    ss.setdefault("current", 0)
    ss.setdefault("answered", 0)
    ss.setdefault("score", 0)
    ss.setdefault("order", [])          # shuffled order of options per question
    ss.setdefault("deadline", None)     # epoch seconds
    ss.setdefault("locked", False)      # locked when time runs out or submitted
    ss.setdefault("choice", None)
    ss.setdefault("started", False)

def sync_player():
    st.session_state["player"] = st.session_state.get("player_input", "").strip()

def header_section():
    neon_panel_start()
    colL, colR = st.columns([7,5], vertical_alignment="center")

    with colL:
        row = st.columns([0.6, 8])
        with row[0]:
            try: st.image(LOGO_FILE, width=40)
            except: st.write("")
        with row[1]:
            st.markdown(f"""
            <div class="header-row">
              <div class="header-title">{APP_TITLE}</div>
            </div>
            """, unsafe_allow_html=True)

    with colR:
        st.markdown('<div class="player-input">', unsafe_allow_html=True)
        st.text_input("Player name",
                      key="player_input",
                      value=st.session_state.get("player_input", ""),
                      placeholder="Type name…",
                      label_visibility="collapsed",
                      on_change=sync_player)
        st.markdown('</div>', unsafe_allow_html=True)
        tag_val = st.session_state.get("player","").strip() or "—"
        st.markdown(f'<div class="player-tag">PLAYER&nbsp;<b>{tag_val}</b></div>', unsafe_allow_html=True)

    neon_panel_end()

def load_questions(df: pd.DataFrame):
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        st.error(f"Missing columns. Required: {REQUIRED_COLS}")
        return []
    rows = []
    for _, r in df.iterrows():
        q = str(r['Question']).strip()
        if not q:  # skip empty
            continue
        options = [str(r['Answer 1']).strip(), str(r['Answer 2']).strip(),
                   str(r['Answer 3']).strip(), str(r['Answer 4']).strip()]
        correct = str(r['Correct Answer']).strip()
        rows.append({"q": q, "opts": options, "correct": correct})
    return rows

def start_question(idx):
    ss = st.session_state
    opts = ss["questions"][idx]["opts"].copy()
    random.shuffle(opts)
    ss["order"] = opts
    ss["deadline"] = time.time() + ROUND_SEC
    ss["locked"] = False
    ss["choice"] = None

def seconds_left():
    ss = st.session_state
    if not ss.get("deadline"):
        return ROUND_SEC
    return max(0, int(ss["deadline"] - time.time()))

def meta_refresh_each(sec=1):
    st.markdown(f"<meta http-equiv='refresh' content='{sec}'>", unsafe_allow_html=True)

# ======================
#  Quiz render
# ======================
def render_progress():
    neon_panel_start()
    st.markdown('<div class="progress-title">Progress</div>', unsafe_allow_html=True)
    total = len(st.session_state["questions"]) or 1
    pct = st.session_state["answered"] / total
    st.progress(pct, text=f"Answered {st.session_state['answered']}/{total}")
    neon_panel_end()

def render_quiz():
    qs = st.session_state["questions"]
    cur = st.session_state["current"]
    total = len(qs)

    if st.session_state.get("deadline") is None:
        start_question(cur)

    render_progress()

    q = qs[cur]
    left = seconds_left()
    locked = st.session_state["locked"] or left <= 0

    c1, c2 = st.columns([6,1])
    with c1:
        st.subheader(f"Question {cur+1}/{total}")
        st.write(q["q"])
    with c2:
        st.markdown(f"<div class='timer-badge'>⏱ {left}s</div>", unsafe_allow_html=True)

    if not locked:
        meta_refresh_each(1)

    opts = st.session_state["order"]
    if locked:
        choice = st.radio(" ", opts, index=None, label_visibility="collapsed", disabled=True)
    else:
        choice = st.radio(" ", opts, index=None, label_visibility="collapsed")
    st.session_state["choice"] = choice

    colL, colR = st.columns(2)
    with colL:
        submit = st.button("✅ Submit", disabled=(locked or choice is None))
    with colR:
        next_btn = st.button("➡️ Next", disabled=(not st.session_state["locked"]))

    if submit and not st.session_state["locked"]:
        st.session_state["locked"] = True
        st.session_state["answered"] += 1
        if choice and choice.strip() == q["correct"].strip():
            st.session_state["score"] += 1
        st.success("Locked in!")

    if next_btn and st.session_state["locked"]:
        if st.session_state["current"] < total - 1:
            st.session_state["current"] += 1
            start_question(st.session_state["current"])
        else:
            st.balloons()

def uploader_block():
    neon_panel_start()
    st.caption("Upload your Excel (.xlsx) file")
    up = st.file_uploader("Drag and drop file here", type=["xlsx"], label_visibility="collapsed")
    if up is not None:
        try:
            df = pd.read_excel(up)
            questions = load_questions(df)
            if questions:
                st.session_state["questions"] = random.sample(questions, k=min(15, len(questions)))
                st.session_state["current"] = 0
                st.session_state["answered"] = 0
                st.session_state["score"] = 0
                st.session_state["deadline"] = None
                st.session_state["started"] = False
                st.success(f"Loaded file with {len(df)} rows. Using {len(st.session_state['questions'])} randomized questions.")
        except Exception as e:
            st.error(f"Failed to read Excel: {e}")
    neon_panel_end()

# ======================
#  Main
# ======================
def main():
    ensure_state()
    header_section()
    uploader_block()

    has_q = bool(st.session_state["questions"])
    has_p = bool(st.session_state["player"].strip())

    if not (has_q and has_p and st.session_state["started"]):
        neon_panel_start()
        if not has_q or not has_p:
            st.markdown("• **Upload Excel** και **βάλε player name** για να ξεκινήσεις.")
        if has_q and has_p and not st.session_state["started"]:
            if st.button("🚀 Start", type="primary", use_container_width=True):
                st.session_state["started"] = True
                start_question(0)
        neon_panel_end()
        return

    render_quiz()

if __name__ == "__main__":
    main()
