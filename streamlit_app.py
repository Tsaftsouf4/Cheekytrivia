# ==============================
# Cheeky Gamblers Trivia — One-by-one, Shuffled options, 60s Timer
# ==============================

import streamlit as st
import pandas as pd
import random
import time
from datetime import datetime
from io import BytesIO

# ------------------ Page / Theme ------------------
st.set_page_config(
    page_title="Cheeky Gamblers Trivia",
    page_icon="cheeky_logo.png",
    layout="wide",
)

BRAND_GOLD = "#FFD60A"
QUESTION_TIME_SEC = 60

st.markdown(f"""
<style>
.block-container {{ padding-top: 8rem; padding-bottom: 2rem; max-width: 1100px; }}
.badge {{ display:inline-block; background:{BRAND_GOLD}; color:#000;
  padding:.28rem .6rem; border-radius:.55rem; font-weight:900; letter-spacing:.3px }}
.app-title {{ font-size:2rem; font-weight:800; margin:0; }}
.logo img {{ height:40px; width:auto; }}
.stRadio > div{{ gap:.5rem; }}
.timer {{ font-weight:800; }}
.player-box {{ border:1px solid rgba(255,255,255,.12); padding:.5rem .75rem; border-radius:.6rem;
  display:inline-flex; gap:.5rem; align-items:center; background:rgba(255,255,255,
