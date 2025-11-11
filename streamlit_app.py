# ==============================
# Cheeky Gamblers Trivia — One-by-one, Shuffled, 45s Timer, Confirm-on-Next, 10s Beep
# ==============================

import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
from io import BytesIO
import streamlit.components.v1 as components

# ------------------ Page / Theme ------------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",
    layout="wide",
)

BRAND_GOLD = "#FFD60A"
QUESTION_TIME_SEC = 45   # ⏳<<< CHANGED TO 45 SECONDS

st.markdown(f"""
<style>
.block-container {{ padding-top: 8rem; padding-bottom: 2rem; max-width: 1100px; }}
.badge {{ display:inline-block; background:{BRAND_GOLD}; color:#000;
  padding:.28rem .6rem; border-radius:.55rem; font-weight:900; letter-spacing:.3px }}
.app-title {{ font-size:2rem; font-weight:800; margin:0; }}
.logo img {{ height:40px; width:auto; }}
.stRadio > div{{ gap:.5rem; }}
.player-box {{ border:1px solid rgba(255,255,255,.12); padding:.5rem .75rem; border-radius:.6rem;
  display:inline-flex; gap:.5rem; align-items:center; background:rgba(255,255,255,.03); }}
.player-dot {{ width:.55rem; height:.55rem; border-radius:999px; background:{BRAND_GOLD}; display:inline-block; }}
.hint {{ opacity:.8; font-size:.9rem; }}
</style>
""", unsafe_allow_html=True)

# ------------------ Helpers ------------------
REQUIRED_COLS = ["#", "Question", "Answer 1", "Answer 2", "Answer 3", "Answer 4", "Correct Answer"]

def _norm(x):
    return str(x).strip().lower().replace("’","'").replace("“","\"").replace("”","\"")

def build_quiz(df: pd.DataFrame):
    """Φτιάχνει 15άδα και κάνει shuffle στις επιλογές κάθε ερώτησης."""
    sample = df.sample(n=min(15, len(df)), random_state=random.randrange(10**9)).reset_index(drop=True)
    quiz = []
    for _, r in sample.iterrows():
        opts = [str(r["Answer 1"]), str(r["Answer 2"]), str(r["Answer 3"]), str(r["Answer 4"])]
        random.shuffle(opts)
        quiz.append({
            "q": str(r["Question"]),
            "opts": opts,
            "correct": str(r["Correct Answer"]),
            "correct_norm": _norm(r["Correct Answer"])
        })
    return quiz

def add_score_row(player: str, score: int, total: int):
    percent = round(100 * score / max(1, total), 2)
    ts = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    st.session_state.setdefault("leaderboard", []).append(
        {"timestamp": ts, "player": player or "Anonymous", "score": score, "total": total, "percent": percent}
    )

def _rerun():
    if hasattr(st, "rerun"): st.rerun()
    else: st.experimental_rerun()

def _clear_answers_and_timers():
    if "quiz" in st.session_state:
        for j in range(1, len(st.session_state.quiz) + 1):
            for key in (f"q{j}", f"q{j}_temp", f"q{j}_locked", f"q{j}_beeped"):
                st.session_state.pop(key, None)
    st.session_state.pop("deadlines", None)

def _reset_quiz(df):
    st.session_state.quiz = build_quiz(df)
    st.session_state.current_i = 1
    _clear_answers_and_timers()

# ---- Timer helpers ----
def _ensure_deadlines():
    st.session_state.setdefault("deadlines", {})

def _start_deadline_if_absent(i):
    _ensure_deadlines()
    if i not in st.session_state.deadlines:
        st.session_state.deadlines[i] = time.time() + QUESTION_TIME_SEC

def _remaining_secs(i):
    _ensure_deadlines()
    dl = st.session_state.deadlines.get(i)
    if dl is None:
        return QUESTION_TIME_SEC
    return max(0, int(round(dl - time.time())))

def _lock_question(i):
    st.session_state[f"q{i}_locked"] = True

def _is_locked(i):
    return bool(st.session_state.get(f"q{i}_locked", False))

def _beep():
    """Παίζει έναν σύντομο beep (Web Audio API) – δεν χρειάζεται αρχείο."""
    components.html("""
    <script>
      (function() {
        try {
          const ctx = new (window.AudioContext || window.webkitAudioContext)();
          const o = ctx.createOscillator();
          const g = ctx.createGain();
          o.type = "sine";
          o.frequency.value = 1000;     // 1 kHz
          o.connect(g); g.connect(ctx.destination);
          g.gain.setValueAtTime(0.15, ctx.currentTime);
          o.start();
          o.stop(ctx.currentTime + 0.20); // 200 ms beep
        } catch (e) { /* ignore */ }
      })();
    </script>
    """, height=0, width=0)

# ------------------ Header ------------------
left, right = st.columns([0.86, 0.14])
with left:
    c1, c2 = st.columns([0.06, 0.94])
    with c1:
        try: st.image("cheeky_logo.png", use_container_width=True)
        except Exception: st.markdown("🎰")
    with c2:
        st.markdown("<div class='app-title'>Cheeky Gamblers Trivia</div>", unsafe_allow_html=True)
with right:
    st.markdown("<div style='text-align:right'><span class='badge'>$250</span> for 15/15</div>", unsafe_allow_html=True)

st.caption("15 random questions per round • Multiple choice • Stream-safe")

# ------------------ Sidebar ------------------
with st.sidebar:
    prev_player = st.session_state.get("prev_player", "")
    player = st.text_input("Player name", placeholder="e.g., Tsaf / Saro / SlotMamba", key="player")
    st.caption("Leaderboard αποθηκεύεται προσωρινά (session only).")

# ------------------ Upload (persist in session) ------------------
uploaded = st.file_uploader("📂 Upload your Excel (.xlsx) file", type=["xlsx"], key="uploader")
if uploaded is not None:
    st.session_state["xlsx_bytes"] = uploaded.getvalue()
    st.session_state["xlsx_name"] = uploaded.name

if "xlsx_bytes" not in st.session_state:
    st.info("Upload an Excel with columns: #, Question, Answer 1–4, Correct Answer.")
    if st.session_state.get("leaderboard"):
        st.markdown("---"); st.subheader("🏆 Leaderboard (session)")
        df_lb = pd.DataFrame(st.session_state.leaderboard).sort_values(
            by=["score","percent","timestamp"], ascending=[False, False, True]
        )
        st.dataframe(df_lb, use_container_width=True, hide_index=True)
    st.stop()

# Read Excel
try:
    df = pd.read_excel(BytesIO(st.session_state["xlsx_bytes"]))
except Exception as e:
    st.error(f"Could not read Excel: {e}")
    st.stop()

df.columns = [str(c).strip() for c in df.columns]
df = df.fillna("")
missing = [c for c in REQUIRED_COLS if c not in df.columns]
if missing:
    st.error(f"Missing columns: {missing}")
    st.stop()

# ------------------ Init state ------------------
if "quiz" not in st.session_state:
    _reset_quiz(df)

# Reset όταν αλλάξει παίκτης (και όχι κενό)
if player and player != prev_player:
    _reset_quiz(df)
    st.session_state["prev_player"] = player
if "prev_player" not in st.session_state:
    st.session_state["prev_player"] = player or ""

quiz = st.session_state.quiz
total_q = len(quiz)
cur = max(1, min(len(quiz), st.session_state.get("current_i", 1)))

st.markdown("---")

# ---- Player box (πάντα ορατό) ----
st.markdown(
    f"<div class='player-box'><span class='player-dot'></span>"
    f"<b>Player:</b> {player or 'Anonymous'}</div>",
    unsafe_allow_html=True
)
st.write("")

# ------------------ TIMER start/track ------------------
_start_deadline_if_absent(cur)
remaining = _remaining_secs(cur)
pct_left = remaining / QUESTION_TIME_SEC

# ------------------ Render Question ------------------
q = quiz[cur - 1]
st.subheader(f"Question {cur}/{total_q}")

# Timer as PROGRESS BAR (πάνω από τις επιλογές)
timer_bar = st.empty()

# Radio (PROVISIONAL selection only; final on Next/Finish)
radio_disabled = _is_locked(cur) or (st.session_state.get(f"q{cur}") is not None)
prev_choice_final = st.session_state.get(f"q{cur}")
prev_choice_temp = st.session_state.get(f"q{cur}_temp")
default_index = None
# δείξε την προσωρινή αν υπάρχει, αλλιώς την τελική
if prev_choice_temp in q["opts"]:
    default_index = q["opts"].index(prev_choice_temp)
elif prev_choice_final in q["opts"]:
    default_index = q["opts"].index(prev_choice_final)

choice_temp = st.radio(
    label=q["q"],
    options=q["opts"],
    index=default_index,
    key=f"q{cur}_temp",
    disabled=radio_disabled
)

# Helper μήνυμα: έχει επιλεγεί προσωρινά αλλά όχι οριστικά
if (st.session_state.get(f"q{cur}_temp") is not None) and (st.session_state.get(f"q{cur}") is None) and not radio_disabled:
    st.markdown("<div class='hint'>🔒 Επιλογή αποθηκευμένη προσωρινά — πάτα <b>Next</b> για οριστικοποίηση.</div>", unsafe_allow_html=True)

# === Timer bar states ===
if _is_locked(cur) and st.session_state.get(f"q{cur}") is None:
    timer_bar.progress(0.0, text="⌛ Time’s up! (locked)")
elif st.session_state.get(f"q{cur}") is not None:
    timer_bar.progress(1.0, text="✅ Answered")
else:
    timer_bar.progress(pct_left, text=f"⏳ Time left: {remaining}s")

# --- Beep στα 10s (μία φορά ανά ερώτηση) ---
if (remaining == 10) and not st.session_state.get(f"q{cur}_beeped", False) and st.session_state.get(f"q{cur}") is None and not _is_locked(cur):
    _beep()
    st.session_state[f"q{cur}_beeped"] = True

# Αν ο χρόνος έληξε χωρίς οριστική απάντηση -> lock & auto-next
if remaining == 0 and st.session_state.get(f"q{cur}") is None and not _is_locked(cur):
    _lock_question(cur)
    if cur < total_q:
        st.session_state.current_i = cur + 1   # βγάλε το αν δεν θες auto-next
    _rerun()

# Progress (πόσες οριστικές απαντήσεις)
answered = sum(1 for j in range(1, total_q+1) if st.session_state.get(f"q{j}") is not None)
st.progress(answered / max(1, total_q), text=f"Answered {answered}/{total_q}")

st.markdown("---")

# ------------------ Navigation ------------------
nav_prev, nav_next, nav_finish = st.columns([0.2, 0.2, 0.6])

with nav_prev:
    if st.button("⬅️ Previous", disabled=(cur == 1)):
        st.session_state.current_i = max(1, cur - 1)
        _rerun()

with nav_next:
    # Next ενεργό μόνο αν υπάρχει προσωρινή επιλογή για την τρέχουσα
    next_disabled = (st.session_state.get(f"q{cur}_temp") is None) or (cur == total_q)
    if st.button("➡️ Next", disabled=next_disabled):
        # Κάνε την προσωρινή επιλογή οριστική
        st.session_state[f"q{cur}"] = st.session_state.get(f"q{cur}_temp")
        st.session_state.current_i = min(total_q, cur + 1)
        _rerun()

with nav_finish:
    # Αν είμαστε στην τελευταία και υπάρχει μόνο προσωρινή, οριστικοποίησέ τη πριν το check
    if cur == total_q and st.session_state.get(f"q{cur}_temp") is not None and st.session_state.get(f"q{cur}") is None:
        st.session_state[f"q{cur}"] = st.session_state.get(f"q{cur}_temp")

    all_answered = all(st.session_state.get(f"q{j}") is not None for j in range(1, total_q+1))
    if st.button("✅ Finish round", disabled=not all_answered):
        answers = [st.session_state.get(f"q{j}") for j in range(1, total_q+1)]
        score = sum(1 for j, ans in enumerate(answers, start=1)
                    if ans is not None and _norm(ans) == quiz[j-1]["correct_norm"])
        st.subheader(f"Score this round: {score}/{total_q}")
        if score == total_q:
            st.success("Perfect score! Claim your $250! 🏆")
        add_score_row(player, score, total_q)

        with st.expander("📘 Show answers"):
            for j in range(1, total_q+1):
                st.markdown(f"**{j}. {quiz[j-1]['q']}**")
                st.write(f"Your answer: {st.session_state.get(f'q{j}') or '—'}")
                st.write(f"Correct: {quiz[j-1]['correct']}")
                st.write("---")

# ------------------ New set ------------------
st.markdown("---")
col_new, _ = st.columns([0.3, 0.7])
with col_new:
    if st.button("🎲 New Random 15"):
        _reset_quiz(df)
        _rerun()

# ------------------ Leaderboard ------------------
st.markdown("---")
st.subheader("🏆 Leaderboard (session)")
if not st.session_state.get("leaderboard"):
    st.info("No scores yet.")
else:
    df_lb = pd.DataFr_
