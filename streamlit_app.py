with nav_finish:
    all_answered = all(st.session_state.get(f"q{j}") is not None for j in range(1, total_q+1))
    if st.button("✅ Finish round", disabled=not all_answered):

        # Υπολογισμός score χωρίς καμία αποκάλυψη ανά ερώτηση
        answers = [st.session_state.get(f"q{j}") for j in range(1, total_q+1)]
        score = 0
        for j, ans in enumerate(answers, start=1):
            if ans is None:
                continue
            if _norm(ans) == quiz[j-1]["correct_norm"]:
                score += 1

        # Καταγραφή στο session leaderboard (προαιρετικό – το κρατάμε)
        add_score_row(player, score, total_q)

        # --- STEALTH LOGIC ---
        if HIDE_RESULTS_UNLESS_PERFECT and score < total_q:
            # ΔΕ ΔΕΙΧΝΕΙΣ ΤΙΠΟΤΑ ΣΤΟ STREAM
            # Αυτός ο γύρος τελείωσε – πάμε στον επόμενο παίκτη
            if AUTO_NEXT_ON_FAIL:
                # Φτιάχνουμε νέο σετ 15 και καθαρίζουμε τα keys
                for j in range(1, total_q+1):
                    st.session_state.pop(f"q{j}", None)
                st.session_state.quiz = build_quiz(df)
                st.session_state.current_i = 1
                _rerun()
            else:
                # Εναλλακτικά, δείξε ένα ουδέτερο μήνυμα και κουμπί για host
                colA, colB = st.columns([0.5, 0.5])
                with colA:
                    st.info("Round complete.")
                with colB:
                    if st.button("➡️ Next player (new 15)"):
                        for j in range(1, total_q+1):
                            st.session_state.pop(f"q{j}", None)
                        st.session_state.quiz = build_quiz(df)
                        st.session_state.current_i = 1
                        _rerun()

        else:
            # ΕΙΤΕ έχουμε τέλειο σκορ είτε θες να φαίνεται το αποτέλεσμα
            if score == total_q:
                st.subheader(f"Perfect score: {score}/{total_q} 🎉 $250!")
                st.balloons()
            else:
                # Αν δεν είσαι σε stealth, μπορείς να δείξεις το σκορ
                st.subheader(f"Score: {score}/{total_q}")

            # Προαιρετικά, εμφάνιση answers μόνο αν θες
            # (ή κράτα το όπως το είχες)
            with st.expander("📘 Show answers"):
                for j in range(1, total_q+1):
                    st.markdown(f"**{j}. {quiz[j-1]['q']}**")
                    st.write(f"Your answer: {st.session_state.get(f'q{j}') or '—'}")
                    st.write(f"Correct: {quiz[j-1]['correct']}")
                    st.write("---")

            # Κουμπί για νέο γύρο
            if st.button("🎲 New Random 15"):
                for j in range(1, total_q+1):
                    st.session_state.pop(f"q{j}", None)
                st.session_state.quiz = build_quiz(df)
                st.session_state.current_i = 1
                _rerun()
