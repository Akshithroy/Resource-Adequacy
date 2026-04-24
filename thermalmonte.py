import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

LOLP_TARGET = 0.2
NENS_TARGET = 0.05
def main():

    st.header("Thermal Monte Carlo")

# =========================================================
# THERMAL PLANTS
# =========================================================
    st.header("Thermal Plants")
    
    THERMAL_DB = [
        {"name":"Brahmapuram","units":[21.32, 21.32, 21.32]},
        {"name":"Kozhikode","units":[160, 160, 160, 160, 160, 160]},
        {"name":"Cochin","units":[45, 45, 39, 45]},
        {"name":"R Gandh","units":[115.2, 115.2, 129.18]},

        {"name": "Plant A",
         "units":[140, 145, 150, 138, 142, 147, 135, 148]},

    
        {"name": "Plant B",
         "units":[130, 120, 135, 125, 140, 115]},

        {"name": "Plant C",
         "units":[90, 110, 95, 105, 100, 85]},

        {"name": "Plant D",
         "units":[120, 80, 115, 95, 105, 90]},
        {"name": "Plant E",
         "units":[120, 80, 115, 95, 105, 90]},

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
                0.0,1.0,0.02,
                key=f"thermal_{p_i}_{u_i}"
            )

            thermal_units.append({"cap":cap,"FOR":FOR})
            total_thermal_capacity += cap

    st.metric("Total Thermal Installed Capacity (MW)", round(total_thermal_capacity,2))

    # =========================================================
    # LOAD INPUT
    # =========================================================
    uploaded_file = st.file_uploader("Upload 8760 Load Excel", type=["xlsx"])

    def load_8760(file):
        df = pd.read_excel(file)
        load = df.iloc[:,0].values
        if len(load) != 8760:
            st.error("Load must be 8760 hours")
            st.stop()
        return load

    # =========================================================
    # MONTE CARLO
    # =========================================================
    def run_monte_carlo(units, load, n_sim):

        n_hours = 8760
        total_loss = np.zeros(n_hours)
        total_eens = np.zeros(n_hours)
        total_available = np.zeros(n_hours)

        for sim in range(n_sim):

            for h in range(n_hours):

                available = 0

                for u in units:
                    if np.random.rand() > u["FOR"]:
                        available += u["cap"]

                total_available[h] += available

                if available < load[h]:
                    total_loss[h] += 1
                    total_eens[h] += (load[h] - available)

        avg_lolp = total_loss / n_sim
        avg_eens = total_eens / n_sim
        avg_available = total_available / n_sim

        return avg_lolp, avg_eens, avg_available

    # =========================================================
    # METRICS
    # =========================================================
    def compute_metrics(avg_lolp, avg_eens, load):

        LOLE = np.sum(avg_lolp)
        LOLP = (LOLE / 8760) * 100
        EENS = np.sum(avg_eens)
        NENS = (EENS / np.sum(load)) * 100

        return LOLP, LOLE, EENS, NENS

    # =========================================================
    # MONTHLY LOLP
    # =========================================================
    def monthly_lolp(avg_lolp):

        hours_month = [744,672,744,720,744,720,744,744,720,744,720,744]

        monthly = []
        idx = 0

        for h in hours_month:
            monthly.append(np.mean(avg_lolp[idx:idx+h])*100)
            idx += h

        return monthly

    # =========================================================
    # RUN
    # =========================================================
    st.header("Run Study")

    n_sim = st.slider("Monte Carlo Simulations", 100, 3000, 500)

    if st.button("Run Adequacy Study"):

        if uploaded_file is None:
            st.error("Upload load file")
            st.stop()

        load = load_8760(uploaded_file)

        with st.spinner("Running Monte Carlo..."):
            avg_lolp, avg_eens, avg_available = run_monte_carlo(
                thermal_units, load, n_sim
            )

            lolp, lole, eens, nens = compute_metrics(
                avg_lolp, avg_eens, load
            )

        # =====================================================
        # KPI PANEL
        # =====================================================
        st.markdown("## 📊 System Reliability Overview")

        c1,c2,c3,c4 = st.columns(4)

        c1.metric("LOLP", f"{round(lolp,3)} %")
        c2.metric("EENS", f"{round(eens,1)} MWh")
        c3.metric("NENS", f"{round(nens,4)} %")
        c4.metric("LOLE", f"{round(lole,2)} hrs")

        if lolp <= LOLP_TARGET and nens <= NENS_TARGET:
            st.success("System is ADEQUATE ✅")
        else:
            st.error("System is NOT ADEQUATE ❌")

        # =====================================================
        # MONTHLY LOLP
        # =====================================================
        st.subheader("Monthly LOLP")

        monthly = monthly_lolp(avg_lolp)

        df_month = pd.DataFrame({
            "Month":["Jan","Feb","Mar","Apr","May","Jun",
                     "Jul","Aug","Sep","Oct","Nov","Dec"],
            "LOLP %": monthly
        })

        st.bar_chart(df_month.set_index("Month"))

        # =====================================================
        # TIME SERIES
        # =====================================================
        df = pd.DataFrame({
            "LOLP": avg_lolp,
            "Deficit": avg_deficit,
            "Available": avg_available,
            "Load": load
        })


   
        st.subheader("Daily LOLP")
        st.line_chart(df["LOLP"].resample("D").mean())


        st.subheader("Load vs Available")
        st.line_chart(df[["Load","Available"]])

        # =====================================================
        # PRM ANALYSIS
        # =====================================================
        st.subheader("PRM Sensitivity")

        extra_range = np.arange(0, 1000, 10)
        results = []

        for extra in extra_range:

            test_units = thermal_units + [{"cap": extra, "FOR":0.02}]

            avg_lolp_t, avg_eens_t, _, _ = run_monte_carlo(
                test_units, load, 10
            )

            lolp_t, _, _, nens_t = compute_metrics(
                avg_lolp_t, avg_eens_t, load
            )

            results.append((extra, lolp_t, nens_t))

        df_prm = pd.DataFrame(results, columns=["Extra MW","LOLP","NENS"])

        st.line_chart(df_prm.set_index("Extra MW"))
