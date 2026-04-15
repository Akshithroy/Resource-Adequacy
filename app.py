import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="RA Planner", layout="wide")

# =========================================================
# HEADER WITH LOGO
# =========================================================

col1, col2 = st.columns([6,1])

with col1:
    st.title("Resource Adequacy Planner")
    st.write("Thermal Only")

with col2:
    st.image("logo.jpg", width=120)


# =========================================================
# RELIABILITY TARGETS
# =========================================================

LOLP_TARGET = 0.2
NENS_TARGET = 0.05

st.info(f"Targets → LOLP ≤ {LOLP_TARGET}% | NENS ≤ {NENS_TARGET}%")

# =========================================================
# THERMAL PLANTS
# =========================================================

st.header("Thermal Plants")

THERMAL_DB = [
    #{"name":"Brahmapuram DG","units":[21.32,21.32,21.32]},
    {"name":"Kozhikode DG","units":[21.32,16,16]},
   # {"name":"Cochin CCPP","units":[45,45,39,45]},
   # {"name":"R Gandhi CCPP","units":[115.2,115.2,129.18]}
]

thermal_units = []

total_thermal_capacity = 0

for p_i, plant in enumerate(THERMAL_DB):

    st.subheader(plant["name"])

    for u_i, cap in enumerate(plant["units"]):

        c1,c2,c3 = st.columns(3)

        c1.write(f"Unit {u_i+1}")
        c2.write(f"{cap} MW")

        FOR = c3.number_input(
            "FOR",
            min_value=0.0,
            max_value=1.0,
            value=0.05,
            key=f"thermal_{p_i}_{u_i}"
        )

        thermal_units.append({
            "cap":cap,
            "FOR":FOR
        })

        total_thermal_capacity += cap


st.metric("Total Thermal Installed Capacity (MW)", round(total_thermal_capacity,2))

# =========================================================
# THERMAL SUMMARY
# =========================================================

total_units = len(thermal_units)

avg_unit_size = total_thermal_capacity / total_units if total_units > 0 else 0

c1, c2, c3 = st.columns(3)

c1.metric("Total Units", total_units)
c2.metric("Total Capacity (MW)", round(total_thermal_capacity,2))
c3.metric("Avg Unit Size (MW)", round(avg_unit_size,2))
# =========================================================
# LOAD MODEL
# =========================================================

st.header("Load Model")

peak_load = st.slider("Peak Load (MW)",0,6000,4000)

def build_load(peak):
    daily = 0.7 + 0.3*np.sin(np.linspace(0,2*np.pi,24))
    yearly = np.tile(daily,365)
    return yearly * peak


# =========================================================
# COPT
# =========================================================

def build_copt(units):

    copt = {0:1.0}

    for u in units:

        cap = int(round(u["cap"]))
        FOR = u["FOR"]

        new_copt = {}

        for outage,prob in copt.items():

            new_copt[outage] = new_copt.get(outage,0) + prob*(1-FOR)
            new_copt[outage+cap] = new_copt.get(outage+cap,0) + prob*FOR

        copt = new_copt

    df = pd.DataFrame({
        "Outage MW": list(copt.keys()),
        "Probability": list(copt.values())
    })

    total_cap = sum(u["cap"] for u in units)

    df["Available MW"] = total_cap - df["Outage MW"]

    return df.sort_values("Outage MW").reset_index(drop=True)


# =========================================================
# LOLP + NENS
# =========================================================

def compute_metrics(copt_df, load):

    total_lolp = 0
    total_eens = 0
    loss_hours = 0

    for L in load:

        loss_prob = 0
        eens_hour = 0

        for _,row in copt_df.iterrows():

            if row["Available MW"] < L:

                loss_prob += row["Probability"]
                eens_hour += (L-row["Available MW"]) * row["Probability"]

        loss_hours += loss_prob

        total_lolp += loss_prob
        total_eens += eens_hour

    LOLP = (total_lolp / len(load)) * 100
    EENS = total_eens
    NENS = (EENS / sum(load)) * 100

    return LOLP, EENS, NENS, loss_hours
# =========================================================
# RUN STUDY
# =========================================================

if st.button("Run Adequacy Study"):

    load = build_load(peak_load)

    copt_df = build_copt(thermal_units)

    lolp, eens, nens, loss_hours = compute_metrics(copt_df, load)

    st.subheader("Results")

    c1, c2, c3, c4 = st.columns(4)

    c1.metric("LOLP %", round(lolp,3))
    c2.metric("EENS (MWh)", round(eens,2))
    c3.metric("NENS %", round(nens,4))
    c4.metric("Loss of Load Hours", loss_hours)
# =========================================================
# COPT VIEW
# =========================================================

st.subheader("Thermal COPT")

copt_df = build_copt(thermal_units)
st.dataframe(copt_df, use_container_width=True)

