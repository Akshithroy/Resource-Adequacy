import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="RA Planner", layout="wide")

# =========================================================
# HEADER
# =========================================================

col1, col2 = st.columns([6,1])

with col1:
    st.title("Resource Adequacy Planner")


with col2:
    st.image("logo.jpg", width=120)

st.info("Targets → LOLP ≤ 0.2% | NENS ≤ 0.05%")

case = st.selectbox(
    "Select Case",
    ["Select case", "Thermal COPT", "Thermal + Hydro", "Thermal Monte Carlo"]
)


# =========================================================
# CONTROLLER
# =========================================================
if case == "Thermal COPT":
    import thermalcopt
    
    thermalcopt.main()

elif case == "Thermal + Hydro":
    import thermalhydro
    #importlib.reload(thermalhydro)
    thermalhydro.main()

elif case == "Thermal Monte Carlo":
    import thermalmonte
    #importlib.reload(thermalmonte)
    thermalmonte.main()
