# unique κλειδί ερώτησης (αλλάζει σε κάθε ερώτηση)
question_key = f"q_{current_index}"   # current_index = 1..15 ή 0..14

# 1) ξεκινά το timer αν άλλαξε ερώτηση
start_question_timer(question_key)

# 2) auto refresh για να κατεβαίνει το ρολόι
autorefresh_each_second(question_key)

# 3) δείξε timer badge
left = get_time_left()
st.markdown(
    f"<div style='display:inline-block;padding:.35rem .7rem;border-radius:999px;"
    f"background:rgba(255,214,10,.14);border:1px solid rgba(255,214,10,.45);"
    f"box-shadow:0 0 10px rgba(255,214,10,.25);font-weight:700'>⏱️ {left}s</div>",
    unsafe_allow_html=True
)

# 4) κλείδωμα αν τελείωσε ο χρόνος
is_locked = lock_if_time_over()

# 5) τα options σου, π.χ. radio/checkboxes:
disabled_flag = is_locked  # True αν τέλειωσε ο χρόνος
picked = st.radio(
    " ",  # κενή ετικέτα για να μη διπλασιάζει τίτλους
    options_list,              # ['A', 'B', 'C', 'D']
    index=None,
    disabled=disabled_flag,
    key=f"ans_{question_key}",
)
