# streamlit_app.py
import random
from datetime import datetime
import pandas as pd
import streamlit as st

# ---------------- Page / Theme ----------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="🃏",
    layout="wide",
)

# ---------------- Utilities ----------------
REQUIRED_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]
ROUND_SIZE = 15

def init_state():
    ss = st.session_state
    ss.setdefault("started", False)
    ss.setdefault("df", None)
    ss.setdefault("order", [])
    ss.setdefault("qi", 0)            # index μέσα στο order
    ss.setdefault("score", 0)
    ss.setdefault("answered_this", False)
    ss.setdefault("selected", None)
    ss.setdefault("player", "")
    ss.setdefault("leaderboard", [])  # [(name, score, dt)]

def load_excel(file):
    df = pd.read_excel(file)
    # Normalise column names (strip)
    df.columns = [str(c).strip() for c in df.columns]
    missing = [c for c in REQUIRED_COLS if c not in df.columns]
    if missing:
        raise ValueError(f"Missing columns: {missing}")
    return df.reset_index(drop=True)

def start_game():
    """Callback για το κουμπί Start."""
    ss = st.session_state
    # Διάλεξε έως 15 τυχαίες ερωτήσεις
    n = min(ROUND_SIZE, len(ss.df))
    ss.order = random.sample(list(range(len(ss.df))), n)
    ss.qi = 0
    ss.score = 0
    ss.answered_this = False
    ss.selected = None
    ss.started = True
    st.rerun()

def reset_for_next_player():
    ss = st.session_state
    ss.started = False
    ss.order = []
    ss.qi = 0
    ss.score = 0
    ss.answered_this = False
    ss.selected = None
    # κρατάμε το df, για να μη ξανακάνεις upload
    st.rerun()

def render_header():
    left, mid, right = st.columns([1,5,2])
    with left:
        st.markdown("### 🦝")
    with mid:
        st.markdown("## Cheeky Gamblers Trivia")
    with right:
        st.text_input("Type name…", key="player", placeholder="Player name")
        st.caption(f"PLAYER  **{st.session_state.player or '—'}**")

def render_loader():
    st.subheader("Upload your Excel (.xlsx) file")
    file = st.file_uploader("Drag & drop or Browse", type=["xlsx"], label_visibility="collapsed")
    if file:
        try:
            st.session_state.df = load_excel(file)
            st.success(f"Loaded file with {len(st.session_state.df)} rows. Using up to {ROUND_SIZE} randomized questions.")
        except Exception as e:
            st.error(str(e))

def render_start():
    # γραμμή με κουμπί start
    disabled = not (st.session_state.df is not None and st.session_state.player.strip())
    start_btn = st.button("🚀 Start", type="primary", use_container_width=True, disabled=disabled, on_click=start_game)
    if disabled:
        st.info("• Upload Excel **και** βάλε player name για να ξεκινήσεις.")

def render_progress():
    qi = st.session_state.qi
    total = len(st.session_state.order)
    st.progress(qi/total if total else 0.0, text=f"Answered {qi}/{total}")

def render_question():
    ss = st.session_state
    df = ss.df
    idx = ss.order[ss.qi]
    row = df.iloc[idx]

    st.markdown(f"### Question {ss.qi+1}/{len(ss.order)}")
    st.write(row["Question"])

    # φτιάξε τις επιλογές και κάνε τυχαία σειρά
    options = [row["Answer 1"], row["Answer 2"], row["Answer 3"], row["Answer 4"]]
    random.seed(f"{idx}-{ss.qi}")  # σταθερό shuffle ανά ερώτηση/γύρισμα σελίδας
    random.shuffle(options)

    # δείξε radio
    ss.selected = st.radio(
        "Choose an answer:",
        options,
        index=None if not ss.selected else options.index(ss.selected) if ss.selected in options else None,
        key=f"q_{ss.qi}",
        label_visibility="collapsed"
    )

    col1, col2 = st.columns([1,1])
    with col1:
        submit = st.button("✅ Submit", use_container_width=True, disabled=ss.answered_this or ss.selected is None)
    with col2:
        next_btn = st.button("➡️ Next", use_container_width=True, disabled=not ss.answered_this)

    # Με το Submit κλειδώνουμε
    if submit and not ss.answered_this and ss.selected is not None:
        correct = str(row["Correct Answer"]).strip()
        if str(ss.selected).strip() == correct:
            ss.score += 1
            st.success("Correct!")
        else:
            st.error(f"Wrong. Correct answer: **{correct}**")
        ss.answered_this = True
        st.stop()  # σταμάτα αυτό το render ώστε να μη φύγει αμέσως

    # Next → επόμενη
    if next_btn and ss.answered_this:
        ss.qi += 1
        ss.answered_this = False
        ss.selected = None
        if ss.qi >= len(ss.order):
            # Τέλος παιχνιδιού
            finish_round()
            st.stop()
        st.rerun()

def finish_round():
    ss = st.session_state
    st.success(f"Round finished! Score: **{ss.score}/{len(ss.order)}**")
    # καταχώρησε στο leaderboard
    if ss.player.strip():
        ss.leaderboard.append((ss.player.strip(), ss.score, datetime.now().strftime("%Y-%m-%d %H:%M")))
    # δείξε leaderboard
    if ss.leaderboard:
        st.markdown("### Leaderboard (session)")
        lb = pd.DataFrame(ss.leaderboard, columns=["Player", "Score", "When"])
        lb = lb.sort_values(["Score", "When"], ascending=[False, True], ignore_index=True)
        st.dataframe(lb, use_container_width=True, height=220)
    st.button("🔁 Next Player", on_click=reset_for_next_player, use_container_width=True, type="primary")

# ---------------- Main ----------------
def main():
    init_state()
    render_header()
    st.divider()
    render_loader()

    # Αν δεν έχει αρχίσει το παιχνίδι → κουμπί Start
    if not st.session_state.started:
        st.divider()
        render_start()
        return

    # Παιχνίδι
    st.divider()
    render_progress()
    render_question()

if __name__ == "__main__":
    main()
