# ============================
# Cheeky Gamblers Trivia App
# ============================

import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime, timedelta

# ---------------- Branding / Page ----------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",   # βεβαιώσου ότι υπάρχει στο root του repo
    layout="wide",
)

BRAND_GOLD = "#FFD60A"
st.markdown(f"""
<style>
.block-container {{ padding-top: 1.4rem; padding-bottom: 2rem; }}
.badge {{
  display:inline-block; background:{BRAND_GOLD}; color:#000;
  padding:.28rem .6rem; border-radius:.55rem; font-weight:900; letter-spacing:.3px
}}
.header-wrap {{
  display:flex; align-items:center; gap:14px; justify-content:space-between;
  margin: 6px 0 14px 0;
}}
.header-left {{ display:flex; align-items:center; gap:12px; }}
.app-title {{ font-size:1.9rem; font-weight:800; margin:0; }}
.logo img {{ height:38px; width:auto; }}
.timer {{ font-size:2.2rem; font-weight:900; letter-spacing:.5px }}
.huge {{ font-size:2.0rem; line-height:1.25; font-weight:800 }}
</style>
""", unsafe_allow_html=True)

# Header (logo + title + $250)
left, right = st.columns([0.86, 0.14])
with left:
    c1, c2 = st.columns([0.06, 0.94])
    with c1:
        try:
            st.image("cheeky_logo.png", use_container_width=True)
        except Exception:
            st.markdown("🎰")
    with c2:
        st.markdown("<div class='app-title'>Cheeky Gamblers Trivia</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div style='text-align:right'><span class='badge'>$250</span> for 15/15</div>", unsafe_allow_html=True)

# --------------- Google Sheets backend ---------------
USE_GSHEETS = False
sh = ws_lb = ws_state = None

def boot_gsheets():
    """Connect to Google Sheets if secrets exist. Creates Leaderboard & State sheets if missing."""
    global USE_GSHEETS, sh, ws_lb, ws_state
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        if "gcp_service_account" in st.secrets and "SHEET_ID" in st.secrets:
            scope = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(st.secrets["SHEET_ID"])
            # Leaderboard
            try:
                ws_lb = sh.worksheet("Leaderboard")
            except Exception:
                ws_lb = sh.add_worksheet(title="Leaderboard", rows="2000", cols="10")
                ws_lb.append_row(["timestamp","player","score","total_questions","percent"])
            # State (για Admin→Dashboard sync)
            try:
                ws_state = sh.worksheet("State")
            except Exception:
                ws_state = sh.add_worksheet(title="State", rows="10", cols="20")
                ws_state.append_row(
                    ["updated_utc","q","a1","a2","a3","a4","correct","deadline_utc","phase"]
                )  # phase: idle|open|locked|revealed
                ws_state.append_row(["","","","","","","","","idle"])
            USE_GSHEETS = True
    except Exception:
        USE_GSHEETS = False

boot_gsheets()

# --------------- Query param / view routing ---------------
# Συμβατότητα: προτιμούμε νέο API, fallback στο experimental
try:
    q = st.query_params
    view = q.get("view", ["player"])[0].lower() if isinstance(q.get("view"), list) else (q.get("view") or "player").lower()
except Exception:
    qp = st.experimental_get_query_params()
    view = qp.get("view", ["player"])[0].lower()

# Βοηθητικά για rerun cross-version
def do_rerun():
    if hasattr(st, "rerun"):
        st.rerun()
    else:
        st.experimental_rerun()

# --------------- Shared helpers ---------------
REQUIRED_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def build_quiz(df: pd.DataFrame, shuffle: bool = False):
    """Φτιάχνει 15άδα από το Excel με optional shuffle απαντήσεων."""
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, r in sample.iterrows():
        opts = [r["Answer 1"], r["Answer 2"], r["Answer 3"], r["Answer 4"]]
        if shuffle:
            random.shuffle(opts)
        quiz.append({"q": str(r["Question"]), "opts": opts, "correct": str(r["Correct Answer"])})
    return quiz

def add_score_row(player: str, score: int, total: int):
    """Γράφει score στο Leaderboard (Sheets) ή το κρατά σε session."""
    percent = round(100 * score / max(1, total), 2)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if USE_GSHEETS:
        try:
            ws_lb.append_row([ts, player or "Anonymous", score, total, percent])
        except Exception as e:
            st.warning(f"Could not write to Google Sheets: {e}")
    else:
        if "leaderboard" not in st.session_state:
            st.session_state.leaderboard = []
        st.session_state.leaderboard.append(
            {"timestamp": ts, "player": player or "Anonymous", "score": score, "total_questions": total, "percent": percent}
        )

def get_leaderboard_df() -> pd.DataFrame:
    if USE_GSHEETS:
        data = ws_lb.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["timestamp","player","score","total_questions","percent"])
    return pd.DataFrame(st.session_state.get("leaderboard", []))

# --- Admin↔Dashboard state helpers (Google Sheets only)
def push_state(q: str, a1: str, a2: str, a3: str, a4: str, correct: str, seconds: int):
    if not USE_GSHEETS:
        st.error("Google Sheets not configured in Secrets."); return
    now = datetime.utcnow()
    dl = now + timedelta(seconds=seconds)
    ws_state.update("A2:I2", [[
        now.strftime("%Y-%m-%d %H:%M:%S"), q, a1, a2, a3, a4, correct,
        dl.strftime("%Y-%m-%d %H:%M:%S"), "open"
    ]])

def lock_state():
    if USE_GSHEETS: ws_state.update("I2","locked")

def reveal_state():
    if USE_GSHEETS: ws_state.update("I2","revealed")

def clear_state():
    if USE_GSHEETS: ws_state.update("A2:I2", [["","","","","","","","","idle"]])

def read_state_df():
    if not USE_GSHEETS: return pd.DataFrame()
    recs = ws_state.get_all_records()
    return pd.DataFrame(recs)

# Sidebar indicator
with st.sidebar:
    if view == "admin":
        st.success("🧠 ADMIN MODE")
    elif view == "dashboard":
        st.success("🖥️ DASHBOARD MODE")
    else:
        st.info("🎮 PLAYER MODE")
    st.write("Backend:", "🟢 Google Sheets" if USE_GSHEETS else "🟡 In-Memory")

# =========================================================
#                      ADMIN VIEW
# =========================================================
if view == "admin":
    st.caption("Drive the live question & timer for the on-stream dashboard.")

    uploaded_admin = st.file_uploader("📂 Upload Excel (.xlsx) for Admin (won't be shown to players)", type=["xlsx"], key="admin_uploader")
    shuffle_answers_admin = st.checkbox("🔀 Shuffle answers when building player quiz?", value=False, key="admin_shuffle")

    if uploaded_admin is not None:
        try:
            df_admin = pd.read_excel(uploaded_admin)
        except Exception as e:
            st.error(f"Could not read Excel: {e}")
            st.stop()

        if not all(c in df_admin.columns for c in REQUIRED_COLS):
            st.error(f"Missing columns. Required: {REQUIRED_COLS}")
            st.stop()

        if "admin_quiz" not in st.session_state:
            st.session_state.admin_quiz = build_quiz(df_admin, shuffle=shuffle_answers_admin)

        st.markdown("### Επιλογή ερώτησης για broadcast")
        idx = st.number_input("Question index", 1, len(st.session_state.admin_quiz), 1)
        qobj = st.session_state.admin_quiz[int(idx)-1]
        st.markdown(f"**Q:** {qobj['q']}")
        st.write("Options:", qobj["opts"])
        secs = st.slider("Countdown (seconds)", 10, 120, 30, step=5)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("🚀 Push to Dashboard"):
                a1, a2, a3, a4 = qobj["opts"]
                push_state(qobj["q"], a1, a2, a3, a4, qobj["correct"], int(secs))
                st.success("Question pushed.")
        with c2:
            if st.button("🔒 Lock answers"):
                lock_state(); st.info("Locked.")
        with c3:
            if st.button("✅ Reveal"):
                reveal_state(); st.success("Revealed.")
        with c4:
            if st.button("🧹 Clear"):
                clear_state(); st.warning("Cleared.")

    st.markdown("---")
    st.markdown("**State preview**")
    st.dataframe(read_state_df(), use_container_width=True, hide_index=True)
    st.info("Άνοιξε το public overlay στο: `?view=dashboard`")

# =========================================================
#                    DASHBOARD VIEW
# =========================================================
elif view == "dashboard":
    st.caption("Auto-refreshing display for stream overlay.")

    if not USE_GSHEETS:
        st.error("Google Sheets backend is not configured. Βάλε Secrets στο Streamlit.")
        st.stop()

    # auto refresh κάθε 1s
    st.autorefresh(interval=1000, key="tick")

    state = read_state_df()
    if state.empty or state.loc[0, "phase"] in ("idle", "", None):
        st.info("Waiting for admin to push a question…")
        st.stop()

    q = state.loc[0, "q"]
    a1, a2, a3, a4 = state.loc[0, "a1"], state.loc[0, "a2"], state.loc[0, "a3"], state.loc[0, "a4"]
    correct = state.loc[0, "correct"]
    phase = state.loc[0, "phase"]
    deadline = state.loc[0, "deadline_utc"]

    st.markdown(f"<div class='huge'>{q}</div>", unsafe_allow_html=True)
    st.radio(" ", [a1, a2, a3, a4], index=None, key="dash_dummy", label_visibility="collapsed", disabled=True)

    # countdown
    try:
        dl = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
        remaining = int((dl - datetime.utcnow()).total_seconds())
    except Exception:
        remaining = 0

    c1, c2, c3 = st.columns(3)
    c1.markdown(f"**Phase:** {phase}")
    c2.markdown(f"<div class='timer'>{max(0, remaining)}s</div>", unsafe_allow_html=True)
    c3.markdown("<div style='text-align:right'><span class='badge'>$250</span></div>", unsafe_allow_html=True)

    if phase == "revealed":
        st.success(f"Correct answer: **{correct}**")

    st.markdown("---")
    st.subheader("🏆 Top 5 Leaderboard")
    lb = get_leaderboard_df()
    if lb.empty:
        st.info("No scores yet.")
    else:
        lb = lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True]).head(5)
        st.dataframe(lb[["player","score","percent","timestamp"]], use_container_width=True, hide_index=True)

# =========================================================
#                     PLAYER VIEW (default)
# =========================================================
else:
    st.caption("15 random questions per round • Multiple choice • Stream-safe")

    with st.sidebar:
        player = st.text_input("Player name", placeholder="e.g., Tsaf / Saro / SlotMamba")
        shuffle_answers = st.checkbox("🔀 Shuffle answers inside each question?", value=False)
        st.caption("Scores sync to Leaderboard " + ("(Google Sheets)." if USE_GSHEETS else "(session only)."))

    uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"])

    if uploaded is not None:
        try:
            df = pd.read_excel(uploaded)
        except Exception as e:
            st.error(f"Could not read Excel: {e}")
            st.stop()

        if not all(c in df.columns for c in REQUIRED_COLS):
            st.error(f"Missing columns. Required: {REQUIRED_COLS}")
            st.stop()

        if "quiz" not in st.session_state:
            st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)

        answers = []
        for i, item in enumerate(st.session_state.quiz, start=1):
            choice = st.radio(f"{i}. {item['q']}", item["opts"], index=None, key=f"q{i}")
            answers.append(choice)

        c1, c2 = st.columns(2)
        with c1:
            if st.button("✅ Submit"):
                score = sum((ans == q["correct"]) for ans, q in zip(answers, st.session_state.quiz))
                total = len(st.session_state.quiz)
                st.subheader(f"Score this round: {score}/{total}")
                if score == total:
                    st.success("Perfect score! Claim your $250! 🏆")
                add_score_row(player, score, total)
                with st.expander("📘 Show answers"):
                    for j, (ans, q) in enumerate(zip(answers, st.session_state.quiz), start=1):
                        st.markdown(f"**{j}. {q['q']}**")
                        st.write(f"Your answer: {ans if ans else '—'}")
                        st.write(f"Correct: {q['correct']}")
                        st.write("---")
        with c2:
            if st.button("🎲 New Random 15"):
                # καθάρισε επιλογές & ξαναφτιάξε 15άδα
                for j in range(1, len(st.session_state.quiz)+1):
                    st.session_state.pop(f"q{j}", None)
                st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)
                do_rerun()
    else:
        st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
