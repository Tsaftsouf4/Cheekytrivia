import streamlit as st
import pandas as pd
import random, time
from datetime import datetime

# ---------- Optional Google Sheets backend ----------
USE_GSHEETS = False
try:
    # Αν έχεις βάλει st.secrets["gcp_service_account"] και st.secrets["SHEET_ID"], θα ενεργοποιηθεί μόνο του
    if "gcp_service_account" in st.secrets and "SHEET_ID" in st.secrets:
        import gspread
        from google.oauth2.service_account import Credentials
        scope = ["https://www.googleapis.com/auth/spreadsheets"]
        creds = Credentials.from_service_account_info(st.secrets["gcp_service_account"], scopes=scope)
        gc = gspread.authorize(creds)
        sh = gc.open_by_key(st.secrets["SHEET_ID"])
        try:
            ws = sh.worksheet("Leaderboard")
        except gspread.WorksheetNotFound:
            ws = sh.add_worksheet(title="Leaderboard", rows="1000", cols="10")
            ws.append_row(["timestamp","player","score","total_questions","percent"])
        USE_GSHEETS = True
except Exception as e:
    USE_GSHEETS = False
# ----------------------------------------------------

st.set_page_config(page_title="Cheeky Gamblers Trivia – $250 Challenge", page_icon="🎰")

st.title("Cheeky Gamblers Trivia – $250 Challenge")
st.caption("15 random questions each run. Scores go to the leaderboard.")

# --- sidebar controls
with st.sidebar:
    player = st.text_input("Player name (for leaderboard)", value="", placeholder="e.g., Tsaf / Saro / SlotMamba")
    shuffle_answers = st.checkbox("🔀 Shuffle answers inside each question?", value=False)
    st.markdown("---")
    st.write("Backend:", "🟢 Google Sheets" if USE_GSHEETS else "🟡 In-Memory (session)")

uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"])

required_cols = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def build_quiz(df, shuffle=False):
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, row in sample.iterrows():
        options = [row["Answer 1"], row["Answer 2"], row["Answer 3"], row["Answer 4"]]
        if shuffle:
            random.shuffle(options)
        quiz.append({"q": str(row["Question"]), "opts": options, "correct": str(row["Correct Answer"])})
    return quiz, sample  # επιστρέφουμε και το sample για αναφορά

def add_score(player_name, score, total_q):
    percent = round(100 * score / max(1, total_q), 2)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    if USE_GSHEETS:
        try:
            ws.append_row([ts, player_name or "Anonymous", score, total_q, percent])
        except Exception as e:
            st.warning(f"Could not write to Google Sheets: {e}")
    else:
        if "leaderboard" not in st.session_state:
            st.session_state.leaderboard = []
        st.session_state.leaderboard.append(
            {"timestamp": ts, "player": player_name or "Anonymous", "score": score, "total_questions": total_q, "percent": percent}
        )

def get_leaderboard_df():
    if USE_GSHEETS:
        data = ws.get_all_records()
        return pd.DataFrame(data) if data else pd.DataFrame(columns=["timestamp","player","score","total_questions","percent"])
    else:
        return pd.DataFrame(st.session_state.get("leaderboard", []))

# --- main flow ---
if uploaded:
    try:
        df = pd.read_excel(uploaded)
    except Exception as e:
        st.error(f"Could not read Excel: {e}")
        st.stop()

    if not all(c in df.columns for c in required_cols):
        st.error(f"Missing columns. Required: {required_cols}")
        st.stop()

    # init quiz
    if "quiz" not in st.session_state:
        st.session_state.quiz, st.session_state.sample_df = build_quiz(df, shuffle=shuffle_answers)

    # render questions
    answers = []
    for i, item in enumerate(st.session_state.quiz, start=1):
        choice = st.radio(f"{i}. {item['q']}", item["opts"], index=None, key=f"q{i}")
        answers.append(choice)

    # actions
    col1, col2, col3 = st.columns([1,1,1])
    with col1:
        if st.button("✅ Submit"):
            score = sum((ans == q["correct"]) for ans, q in zip(answers, st.session_state.quiz))
            total_q = len(st.session_state.quiz)
            st.subheader(f"Score this round: {score}/{total_q}")
            if score == total_q:
                st.success("Perfect score! Claim your $250 on stream! 🏆")

            # write to leaderboard
            add_score(player, score, total_q)

            with st.expander("📘 Show answers"):
                for i, (ans, q) in enumerate(zip(answers, st.session_state.quiz), start=1):
                    st.markdown(f"**{i}. {q['q']}**")
                    st.write(f"Your answer: {ans if ans else '—'}")
                    st.write(f"Correct: {q['correct']}")
                    st.write("---")

    with col2:
        if st.button("🎲 New Random 15"):
            # καθάρισε τις απαντήσεις και φτιάξε νέο sample
            for i in range(1, len(st.session_state.quiz)+1):
                st.session_state.pop(f"q{i}", None)
            st.session_state.quiz, st.session_state.sample_df = build_quiz(df, shuffle=shuffle_answers)
            if hasattr(st, "rerun"):
                st.rerun()
            else:
                st.experimental_rerun()

    with col3:
        if st.button("🧹 Reset Leaderboard (session)"):
            if USE_GSHEETS:
                st.warning("Google Sheets backend: κάνε reset χειροκίνητα στο Sheet.")
            else:
                st.session_state["leaderboard"] = []
                st.success("Leaderboard cleared (session).")

    st.markdown("----")

    # Leaderboard view
    st.subheader("🏆 Leaderboard")
    lb = get_leaderboard_df()
    if not lb.empty:
        # ταξινόμηση: καλύτερο score/percent πρώτο
        lb_sorted = lb.sort_values(by=["score","percent","timestamp"], ascending=[False, False, True])
        st.dataframe(lb_sorted, use_container_width=True)
    else:
        st.info("No scores yet. Submit a round to appear here.")
else:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
