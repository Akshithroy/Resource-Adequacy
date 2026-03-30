import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

st.set_page_config(page_title="Resource Adequacy Planner", layout="wide")

# =========================================================
# HEADER
# =========================================================

col1, col2 = st.columns([8,1])

with col1:
    st.title("Resource Adequacy Planner")
    st.write("COPT-based Reliability Model")

with col2:
    st.image("logo.jpg", width=120)

# =========================================================
# RELIABILITY TARGETS
# =========================================================

LOLP_TARGET = 0.2
NENS_TARGET = 0.05

st.info(f"Reliability Targets → LOLP ≤ {LOLP_TARGET}% | NENS ≤ {NENS_TARGET}%")

# =========================================================
# PLANT DATABASE
# =========================================================

st.header("Kerala Plant Database")

PLANT_DB = [
{"name":"Brahmapuram DG","units":[21.32,21.32,21.32],"type":"diesel"},
{"name":"Kozhikode DG","units":[16,16,16,16,16,16],"type":"diesel"},
{"name":"Cochin CCPP","units":[45,45,39,45],"type":"thermal"},
{"name":"R Gandhi CCPP","units":[115.2,115.2,129.18],"type":"thermal"},
{"name":"Idamalayar","units":[37.5,37.5],"type":"hydro"},
{"name":"Idukki","units":[130,130,130,130,130,130],"type":"hydro"},
{"name":"Kakkad","units":[25,25],"type":"hydro"},
{"name":"Kuttiyadi Addl","units":[50,50,50],"type":"hydro"},
{"name":"Kuttiyadi","units":[25,25,25],"type":"hydro"},
{"name":"Lower Periyar","units":[60,60,60],"type":"hydro"},
{"name":"Nariamanglam","units":[17.55,17.55,17.55],"type":"hydro"},
{"name":"Pallivasal Extn","units":[30,30],"type":"hydro"},
{"name":"Pallivasal","units":[5,5,5,7.5,7.5,7.5],"type":"hydro"},
{"name":"Panniar","units":[15,15],"type":"hydro"},
{"name":"Poringalkuthu","units":[8,8,8,8],"type":"hydro"},
{"name":"Sabarigiri","units":[50,50,50,50,50,50],"type":"hydro"},
{"name":"Sengulam","units":[12,12,12,12],"type":"hydro"},
{"name":"Sholayar","units":[18,18,18],"type":"hydro"},
{"name":"Thottiyar","units":[10,30],"type":"hydro"}
]

units = []

# =========================================================
# INPUT SECTION
# =========================================================

months = ["Jan","Feb","Mar","Apr","May","Jun",
          "Jul","Aug","Sep","Oct","Nov","Dec"]

default_hydro_factors = [0.70,0.65,0.55,0.45,0.50,0.80,1.00,0.95,0.90,0.85,0.80,0.75]

for p_i, plant in enumerate(PLANT_DB):

    st.subheader(plant["name"])

    if plant["type"] == "hydro":

        plant_capacity = sum(plant["units"])
        st.write(f"Installed Capacity : {plant_capacity} MW")

        hydro_FOR = st.number_input(
            "Hydro Forced Outage Rate",
            min_value=0.0,
            max_value=0.2,
            value=0.02,
            step=0.01,
            key=f"hydro_for_{p_i}"
        )

        cols = st.columns(6)
        factors = []

        for m_i, m in enumerate(months):

            col = cols[m_i % 6]

            f = col.number_input(
                m,
                min_value=0.0,
                max_value=1.0,
                value=default_hydro_factors[m_i],
                step=0.01,
                key=f"hydro_{p_i}_{m_i}"
            )

            factors.append(f)

        for cap in plant["units"]:
            units.append({
                "cap":cap,
                "FOR":hydro_FOR,
                "type":"hydro",
                "factors":factors
            })

    else:

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

            units.append({
                "cap":cap,
                "FOR":FOR,
                "type":"thermal"
            })

# =========================================================
# CAPACITY OVERVIEW
# =========================================================

installed_capacity = sum(u["cap"] for u in units)

expected_available_capacity = 0

for u in units:

    if u["type"] == "hydro":
        expected_available_capacity += u["cap"] * np.mean(u["factors"])
    else:
        expected_available_capacity += u["cap"] * (1-u["FOR"])

st.subheader("Capacity Overview")

c1,c2 = st.columns(2)

c1.metric("Installed Capacity (MW)",round(installed_capacity,2))
c2.metric("Expected Available Capacity (MW)",round(expected_available_capacity,2))

peak_load = st.slider("Peak Load MW",1000,6000,4000)

# =========================================================
# RESERVE MARGIN
# =========================================================

reserve_margin = ((expected_available_capacity - peak_load)/peak_load)*100

st.subheader("System Reserve Margin")

c1,c2 = st.columns(2)
c1.metric("Peak Load (MW)",peak_load)
c2.metric("Reserve Margin (%)",round(reserve_margin,2))

# =========================================================
# LOAD MODEL
# =========================================================

def build_load(peak):

    daily = 0.7 + 0.3*np.sin(np.linspace(0,2*np.pi,24))
    yearly = np.tile(daily,365)

    return yearly*peak

# =========================================================
# COPT
# =========================================================

def build_copt(units):

    copt = {0:1.0}

    for u in units:

        if u["type"] == "hydro":
            factor = np.mean(u["factors"])
            cap = int(round(u["cap"] * factor))
            FOR = u["FOR"]
        else:
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

    total_capacity = sum(
        u["cap"]*np.mean(u["factors"]) if u["type"]=="hydro"
        else u["cap"]
        for u in units
    )

    df["Available MW"] = total_capacity - df["Outage MW"]

    return df.sort_values("Outage MW").reset_index(drop=True)

# =========================================================
# LOLP + NENS
# =========================================================

def compute_lolp_nens(copt_df,load):

    total_lolp=0
    total_eens=0

    for L in load:

        for _,row in copt_df.iterrows():

            if row["Available MW"] < L:

                total_lolp += row["Probability"]
                total_eens += (L-row["Available MW"])*row["Probability"]

    yearly_lolp=(total_lolp/len(load))*100
    nens_percent=(total_eens/sum(load))*100

    return yearly_lolp,nens_percent

# =========================================================
# ADEQUACY STUDY
# =========================================================

if st.button("Run Adequacy Study"):

    load = build_load(peak_load)
    copt_df = build_copt(units)

    lolp,nens = compute_lolp_nens(copt_df,load)

    st.subheader("Adequacy Result")

    c1,c2 = st.columns(2)

    c1.metric("LOLP %",round(lolp,3))
    c2.metric("NENS %",round(nens,4))

    st.subheader("Hourly Load Profile")

    fig,ax = plt.subplots()
    ax.plot(load)
    ax.set_xlabel("Hour of Year")
    ax.set_ylabel("Load (MW)")
    ax.grid(True)

    st.pyplot(fig)

# =========================================================
# COPT TABLE
# =========================================================

st.subheader("Capacity Outage Probability Table")

copt_df = build_copt(units)

st.dataframe(copt_df,use_container_width=True)
