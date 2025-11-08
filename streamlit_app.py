import streamlit as st

st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",
    layout="wide",
)
import pandas as pd
import random, time
from datetime import datetime, timedelta

# ---------------- Google Sheets backend ----------------
USE_GSHEETS = False
sh = ws_lb = ws_state = None

def _boot_gsheets():
    global USE_GSHEETS, sh, ws_lb, ws_state
    try:
        import gspread
        from google.oauth2.service_account import Credentials
        if "gcp_service_account" in st.secrets and "SHEET_ID" in st.secrets:
            scope = ["https://www.googleapis.com/auth/spreadsheets"]
            creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
            gc = gspread.authorize(creds)
            sh = gc.open_by_key(st.secrets["SHEET_ID"])
            # Leaderboard sheet
            try: ws_lb = sh.worksheet("Leaderboard")
            except: 
                ws_lb = sh.add_worksheet(title="Leaderboard", rows="2000", cols="10")
                ws_lb.append_row(["timestamp","player","score","total_questions","percent"])
            # State sheet (single row holds the live question)
            try: ws_state = sh.worksheet("State")
            except:
                ws_state = sh.add_worksheet(title="State", rows="10", cols="20")
                ws_state.append_row(
                    ["updated_utc","q","a1","a2","a3","a4","correct","deadline_utc","phase"]
                )  # phase: idle|open|locked|revealed
                ws_state.append_row(["","","","","","","","","idle"])
            USE_GSHEETS = True
    except Exception as e:
        USE_GSHEETS = False

_boot_gsheets()
# -------------------------------------------------------

# ---------------- Branding / Theme ---------------------
PAGE_ICON_PATH = "cheeky_logo.png"
st.set_page_config(page_title="Cheeky Gamblers Trivia – $250 Challenge", page_icon=PAGE_ICON_PATH)
BRAND_GOLD = "#FFD60A"
st.markdown(f"""
<style>
.block-container{{padding-top:2rem;padding-bottom:2.5rem}}
.badge{{display:inline-block;background:{BRAND_GOLD};color:#000;padding:.25rem .6rem;border-radius:.5rem;font-weight:900}}
.huge{{font-size:2.2rem;line-height:1.25;font-weight:800}}
.timer{{font-size:2.6rem;font-weight:900;letter-spacing:.5px}}
.bigopt label{{font-size:1.05rem}}
</style>
""", unsafe_allow_html=True)

# ---------------- Helpers ------------------------------
REQUIRED = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def build_quiz(df, shuffle=False):
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz=[]
    for _, r in sample.iterrows():
        opts=[r["Answer 1"],r["Answer 2"],r["Answer 3"],r["Answer 4"]]
        if shuffle: random.shuffle(opts)
        quiz.append({"q": str(r["Question"]), "opts": opts, "correct": str(r["Correct Answer"])})
    return quiz

def add_score_row(player, score, total):
    if not USE_GSHEETS: return
    ws_lb.append_row([
        datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S"),
        player or "Anonymous", score, total, round(100*score/max(1,total),2)
    ])

def push_state(q, a1, a2, a3, a4, correct, seconds):
    if not USE_GSHEETS: 
        st.error("Google Sheets not configured.")
        return
    now = datetime.utcnow()
    deadline = now + timedelta(seconds=seconds)
    values = [
        now.strftime("%Y-%m-%d %H:%M:%S"), q, a1, a2, a3, a4, correct,
        deadline.strftime("%Y-%m-%d %H:%M:%S"), "open"
    ]
    ws_state.update(f"A2:I2", [values])

def lock_state():
    if USE_GSHEETS: ws_state.update("I2","locked")

def reveal_state():
    if USE_GSHEETS: ws_state.update("I2","revealed")

def clear_state():
    if USE_GSHEETS:
        ws_state.update("A2:I2", [["","","","","","","","","idle"]])

def read_state_df():
    if not USE_GSHEETS: return pd.DataFrame()
    recs = ws_state.get_all_records()
    return pd.DataFrame(recs)

def get_leaderboard_df():
    if not USE_GSHEETS: return pd.DataFrame()
    data = ws_lb.get_all_records()
    return pd.DataFrame(data)

# ---------------- Routing ------------------------------
view = st.query_params.get("view", ["player"])[0]

# ---------------- Admin View ---------------------------
if view == "admin":
    st.markdown("## 🎛️ Admin Panel")
    st.caption("Drive the live question & timer for the on-stream dashboard. Backend: " + ("🟢 Google Sheets" if USE_GSHEETS else "🔴 OFF"))
    with st.sidebar:
        shuffle_answers = st.checkbox("🔀 Shuffle answers when building player quiz?", value=False)

    uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file (admin only)", type=["xlsx"])
    if uploaded:
        df = pd.read_excel(uploaded)
        if not all(c in df.columns for c in REQUIRED):
            st.error(f"Missing columns. Required: {REQUIRED}")
            st.stop()
        if "quiz" not in st.session_state:
            st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)

        st.markdown("#### Pick a question to broadcast")
        idx = st.number_input("Question index", 1, len(st.session_state.quiz), 1)
        qobj = st.session_state.quiz[idx-1]
        st.markdown(f"**Q:** {qobj['q']}")
        st.write("Options:", qobj["opts"])
        secs = st.slider("Countdown (seconds)", 10, 120, 30, step=5)

        c1, c2, c3, c4 = st.columns(4)
        with c1:
            if st.button("🚀 Push to Dashboard"):
                a1,a2,a3,a4 = qobj["opts"]
                push_state(qobj["q"], a1,a2,a3,a4, qobj["correct"], secs)
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
    st.info("Open the public dashboard at: `?view=dashboard`")

# ---------------- Dashboard View -----------------------
elif view == "dashboard":
    st.markdown("## 🎥 Cheeky Trivia — Live Dashboard  ")
    st.caption("Auto-refreshing display for stream overlay.")
    st_autorefresh = st.experimental_rerun if hasattr(st, "experimental_rerun") else None
    st.experimental_set_query_params(view="dashboard")

    if not USE_GSHEETS:
        st.error("Google Sheets backend is not configured. Ask admin to set Secrets.")
        st.stop()

    # Auto refresh
    st_autorefresh = st.autorefresh(interval=1000, limit=None, key="tick")

    state = read_state_df()
    if state.empty or state.loc[0,"phase"] in ("idle",""):
        st.info("Waiting for admin to push a question…")
        st.stop()

    q = state.loc[0,"q"]; a1 = state.loc[0,"a1"]; a2=state.loc[0,"a2"]; a3=state.loc[0,"a3"]; a4=state.loc[0,"a4"]
    correct = state.loc[0,"correct"]; phase = state.loc[0,"phase"]
    deadline = state.loc[0,"deadline_utc"]

    st.markdown(f"<div class='huge'>{q}</div>", unsafe_allow_html=True)
    st.write("")
    st.radio(" ", [a1,a2,a3,a4], index=None, label_visibility="collapsed", horizontal=False, key="dummy", disabled=True)

    # timer
    try:
        dl = datetime.strptime(deadline, "%Y-%m-%d %H:%M:%S")
        remaining = int((dl - datetime.utcnow()).total_seconds())
    except:
        remaining = 0

    cols = st.columns(3)
    cols[0].markdown(f"**Phase:** {phase}")
    cols[1].markdown(f"<div class='timer'>{max(0,remaining)}s</div>", unsafe_allow_html=True)
    cols[2].markdown("<div style='text-align:right'><span class='badge'>$250</span></div>", unsafe_allow_html=True)

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

# ---------------- Player Quiz (default) ----------------
else:
    st.markdown("## Cheeky Gamblers Trivia")
    st.caption("15 random questions per round • Multiple choice • Stream-safe")
    with st.sidebar:
        player = st.text_input("Player name", placeholder="e.g., Tsaf / Saro / SlotMamba")
        shuffle_answers = st.checkbox("🔀 Shuffle answers inside each question?", value=False)
        st.caption("Scores sync to Leaderboard (Google Sheets).")

    uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"])

    if uploaded:
        try:
            df = pd.read_excel(uploaded)
        except Exception as e:
            st.error(f"Could not read Excel: {e}"); st.stop()

        if not all(c in df.columns for c in REQUIRED):
            st.error(f"Missing columns. Required: {REQUIRED}"); st.stop()

        if "quiz" not in st.session_state:
            st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)

        answers=[]
        for i,item in enumerate(st.session_state.quiz, start=1):
            choice = st.radio(f"{i}. {item['q']}", item["opts"], index=None, key=f"q{i}")
            answers.append(choice)

        c1,c2 = st.columns(2)
        with c1:
            if st.button("✅ Submit"):
                score = sum((ans == q["correct"]) for ans, q in zip(answers, st.session_state.quiz))
                total = len(st.session_state.quiz)
                st.subheader(f"Score this round: {score}/{total}")
                if score == total: st.success("Perfect score! Claim your $250! 🏆")
                if USE_GSHEETS: add_score_row(player, score, total)
                with st.expander("📘 Show answers"):
                    for i,(ans,q) in enumerate(zip(answers, st.session_state.quiz), start=1):
                        st.markdown(f"**{i}. {q['q']}**")
                        st.write(f"Your answer: {ans if ans else '—'}")
                        st.write(f"Correct: {q['correct']}"); st.write("---")
        with c2:
            if st.button("🎲 New Random 15"):
                for i in range(1, len(st.session_state.quiz)+1):
                    st.session_state.pop(f"q{i}", None)
                st.session_state.quiz = build_quiz(df, shuffle=shuffle_answers)
                (st.rerun() if hasattr(st,"rerun") else st.experimental_rerun())
    else:
        st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
