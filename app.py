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
# CASE 1: THERMAL COPT
# =========================================================
def run_thermal_copt():

    st.header("Thermal Plants")

    THERMAL_DB = [
        {"name":"Brahmapuram","units":[21.32,21.32,21.32]},
        {"name":"Kozhikode","units":[16,16,16,16,16,16]},
        {"name":"Cochin","units":[45,45,39,45]},
        {"name":"R Gandhi","units":[115.2,115.2,129.18]}
    ]

    thermal_units = []
    total_capacity = 0

    for p_i, plant in enumerate(THERMAL_DB):

        st.subheader(plant["name"])

        for u_i, cap in enumerate(plant["units"]):

            c1, c2, c3 = st.columns(3)

            c1.write(f"Unit {u_i+1}")
            c2.write(f"{cap} MW")

            FOR = c3.number_input(
                "FOR", 0.0, 1.0, 0.02, key=f"copt_{p_i}_{u_i}"
            )

            thermal_units.append({"cap": cap, "FOR": FOR})
            total_capacity += cap

    st.metric("Total Capacity (MW)", round(total_capacity,2))

    peak_load = st.slider("Peak Load (MW)", 0, 1000, 400)

    def build_load(peak):
        daily = 0.7 + 0.3*np.sin(np.linspace(0,2*np.pi,24))
        yearly = np.tile(daily,365)
        noise = np.random.normal(0, 0.03, size=8760)
        return yearly * peak * (1 + noise)

    def build_copt(units):
        copt = {0:1.0}
        for u in units:
            cap = int(round(u["cap"]))
            FOR = u["FOR"]
            new = {}
            for outage, prob in copt.items():
                new[outage] = new.get(outage,0) + prob*(1-FOR)
                new[outage+cap] = new.get(outage+cap,0) + prob*FOR
            copt = new

        df = pd.DataFrame({
            "Outage MW": list(copt.keys()),
            "Probability": list(copt.values())
        })

        total_cap = sum(u["cap"] for u in units)
        df["Available MW"] = total_cap - df["Outage MW"]

        return df.sort_values("Outage MW")

    def compute_metrics(copt_df, load):

        total_lolp = 0
        total_eens = 0
        loss_hours = 0

        hourly_lolp = []
        eens_profile = []

        for L in load:

            loss_prob = 0
            eens_hour = 0

            for _, row in copt_df.iterrows():
                if row["Available MW"] < L:
                    loss_prob += row["Probability"]
                    eens_hour += (L - row["Available MW"]) * row["Probability"]

            hourly_lolp.append(loss_prob)
            eens_profile.append(eens_hour)

            loss_hours += loss_prob
            total_lolp += loss_prob
            total_eens += eens_hour

        LOLP = (total_lolp / len(load)) * 100
        EENS = total_eens
        NENS = (EENS / sum(load)) * 100

        return LOLP, EENS, NENS, loss_hours, hourly_lolp, eens_profile

    if st.button("Run Adequacy Study"):

        load = build_load(peak_load)
        copt_df = build_copt(thermal_units)

        results = compute_metrics(copt_df, load)

        LOLP, EENS, NENS, LOLE, hourly_lolp, eens_profile = results

        st.metric("LOLP", f"{LOLP:.3f} %")
        st.metric("EENS", f"{EENS:.1f} MWh")
        st.metric("NENS", f"{NENS:.4f} %")
        st.metric("LOLE", f"{LOLE:.2f} hrs")

        if LOLP <= LOLP_TARGET and NENS <= NENS_TARGET:
            st.success("System is ADEQUATE ✅")
        else:
            st.error("System is NOT ADEQUATE ❌")


# =========================================================
# CASE 2: THERMAL + HYDRO
# =========================================================
def run_thermal_hydro():

    st.header("Thermal + Hydro System")

    THERMAL_DB = [
        {"name":"Brahmapuram","units":[21.32,21.32,21.32]},
        {"name":"Kozhikode","units":[16,16,16,16,16,16]},
        {"name":"Cochin","units":[45,45,39,45]},
        {"name":"R Gandhi","units":[115.2,115.2,129.18]}
    ]

    thermal_units = []
    thermal_capacity = 0

    for p_i, plant in enumerate(THERMAL_DB):
        st.subheader(plant["name"])

        for u_i, cap in enumerate(plant["units"]):

            c1,c2,c3 = st.columns(3)

            c1.write(f"Unit {u_i+1}")
            c2.write(f"{cap} MW")

            FOR = c3.number_input(
                "FOR", 0.0,1.0,0.02,
                key=f"hydro_{p_i}_{u_i}"   # FIX: unique key
            )

            thermal_units.append({"cap":cap,"FOR":FOR})
            thermal_capacity += cap

    st.metric("Thermal Capacity (MW)", round(thermal_capacity,2))

    total_units = len(thermal_units)
    avg_unit_size = thermal_capacity / total_units

    c1, c2, c3 = st.columns(3)
    c1.metric("Total Units", total_units)
    c2.metric("Total Capacity (MW)", round(thermal_capacity,2))
    c3.metric("Avg Unit Size (MW)", round(avg_unit_size,2))

    # HYDRO
    st.header("Hydro System")

    hydro_capacity = 1964.15
    monthly_factors = [0.35,0.30,0.25,0.20,0.30,0.80,0.90,0.85,0.85,0.70,0.55,0.45]
    st.metric("Total Hydro Capacity (MW)", hydro_capacity)

    # LOAD
    st.header("Load Model")

    peak_load = st.slider("Peak Load (MW)",0,4000,1000)

    months = ["Jan","Feb","Mar","Apr","May","Jun","Jul","Aug","Sep","Oct","Nov","Dec"]
    hours_month = [744,672,744,720,744,720,744,744,720,744,720,744]

    def build_load(peak):
        daily = 0.7 + 0.3*np.sin(np.linspace(0,2*np.pi,24))
        yearly = np.tile(daily,365)
        noise = np.random.normal(0,0.03,8760)
        return yearly * peak * (1 + noise)

    def build_copt(units):
        copt = {0:1.0}
        for u in units:
            cap = int(round(u["cap"]))
            FOR = u["FOR"]
            new = {}
            for outage,prob in copt.items():
                new[outage] = new.get(outage,0)+prob*(1-FOR)
                new[outage+cap] = new.get(outage+cap,0)+prob*FOR
            copt = new

        df = pd.DataFrame({
            "Outage MW":list(copt.keys()),
            "Probability":list(copt.values())
        })

        total = sum(u["cap"] for u in units)
        df["Available MW"] = total - df["Outage MW"]

        return df.sort_values("Outage MW")

    def compute_thermal_only(copt_df, load):
        monthly_lolp = []
        hour_index = 0

        for h_m in hours_month:
            total_lolp = 0
            for _ in range(h_m):
                L = load[hour_index]
                loss_prob = 0
                for _, row in copt_df.iterrows():
                    if row["Available MW"] < L:
                        loss_prob += row["Probability"]
                total_lolp += loss_prob
                hour_index += 1

            monthly_lolp.append((total_lolp / h_m) * 100)

        return monthly_lolp

    def compute_with_hydro(copt_df, load):
        monthly_lolp = []
        hour_index = 0

        for m, h_m in enumerate(hours_month):

            total_lolp = 0
            hydro_available = hydro_capacity * monthly_factors[m]

            for _ in range(h_m):

                L = load[hour_index]
                loss_prob = 0

                for _, row in copt_df.iterrows():

                    avail = row["Available MW"]
                    deficit = max(0, L - avail)

                    hydro_support = min(deficit, hydro_available)
                    effective = avail + hydro_support

                    if effective < L:
                        loss_prob += row["Probability"]

                total_lolp += loss_prob
                hour_index += 1

            monthly_lolp.append((total_lolp / h_m) * 100)

        return monthly_lolp

    if st.button("Run Adequacy Study"):

        load = build_load(peak_load)
        copt = build_copt(thermal_units)

        thermal_only = compute_thermal_only(copt, load)
        hydro_case = compute_with_hydro(copt, load)

        st.session_state["data"] = {
            "thermal_only": thermal_only,
            "hydro_case": hydro_case
        }

    if "data" in st.session_state:

        data = st.session_state["data"]

        thermal_only = data["thermal_only"]
        hydro_case = data["hydro_case"]

        st.markdown("## 📊 System Reliability Overview")

        LOLP = np.mean(hydro_case)
        EENS = sum(hydro_case) * 10
        NENS = EENS / (peak_load * 8760) * 100
        LOLE = sum(hydro_case)

        c1, c2, c3, c4 = st.columns(4)

        c1.metric("LOLP", f"{LOLP:.3f} %")
        c2.metric("EENS", f"{EENS:.1f} MWh")
        c3.metric("NENS", f"{NENS:.4f} %")
        c4.metric("LOLE", f"{LOLE:.2f} hrs")

        if LOLP <= LOLP_TARGET and NENS <= NENS_TARGET:
            st.success("System is ADEQUATE ✅")
        else:
            st.error("System is NOT ADEQUATE ❌")

        st.markdown("## 📈 Reliability Comparison")

        col1, col2 = st.columns(2)

        with col1:
            fig1, ax1 = plt.subplots()
            ax1.plot(months, thermal_only, marker='o', linestyle='--')
            ax1.set_title("Thermal Only LOLP")
            ax1.grid(True)
            st.pyplot(fig1)

        with col2:
            fig2, ax2 = plt.subplots()
            ax2.plot(months, hydro_case, marker='o')
            ax2.set_title("Thermal + Hydro LOLP")
            ax2.grid(True)
            st.pyplot(fig2)

        st.markdown("## 🔋 Hydro Contribution")

        improvement = np.array(thermal_only) - np.array(hydro_case)

        fig3, ax3 = plt.subplots()
        ax3.bar(months, improvement)
        ax3.set_title("Monthly LOLP Reduction due to Hydro")
        ax3.grid(True)

        st.pyplot(fig3)


# =========================================================
# CASE 3: MONTE CARLO
# =========================================================
def run_thermal_monte():

    st.header("Thermal Plants")

    THERMAL_DB = [
        {"name":"Brahmapuram","units":[21.32, 21.32, 21.32]},
        {"name":"Kozhikode","units":[160, 160, 160, 160, 160, 160]},
        {"name":"Cochin","units":[45, 45, 39, 45]},
        {"name":"R Gandh","units":[115.2, 115.2, 129.18]},

        {"name": "New Base Load Plant",
         "units":[140, 145, 150, 138, 142, 147, 135, 148]},

        {"name": "Mid Merit Plant",
         "units":[130, 120, 135, 125, 140, 115]},

        {"name": "Peaker Units A",
         "units":[90, 110, 95, 105, 100, 85]},

        {"name": "Peaker Units B",
         "units":[120, 80, 115, 95, 105, 90]},
        {"name": "Peaker Units C ",
         "units":[120, 80, 115, 95, 105, 90]},

        {"name": "Peaker Units D",
        "units":[90, 110, 95, 105, 100, 85]},
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
                key=f"monte_{p_i}_{u_i}"   # FIX: unique key
            )

            thermal_units.append({"cap":cap,"FOR":FOR})
            total_thermal_capacity += cap

    st.metric("Total Thermal Installed Capacity (MW)", round(total_thermal_capacity,2))

    uploaded_file = st.file_uploader("Upload 8760 Load Excel", type=["xlsx"])

    def load_8760(file):
        df = pd.read_excel(file)
        load = df.iloc[:,0].values
        if len(load) != 8760:
            st.error("Load must be 8760 hours")
            st.stop()
        return load

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
        avg_deficit = avg_eens

        return avg_lolp, avg_eens, avg_deficit, avg_available

    def compute_metrics(avg_lolp, avg_eens, load):

        LOLE = np.sum(avg_lolp)
        LOLP = (LOLE / 8760) * 100
        EENS = np.sum(avg_eens)
        NENS = (EENS / np.sum(load)) * 100

        return LOLP, LOLE, EENS, NENS

    def monthly_lolp(avg_lolp):

        hours_month = [744,672,744,720,744,720,744,744,720,744,720,744]

        monthly = []
        idx = 0

        for h in hours_month:
            monthly.append(np.mean(avg_lolp[idx:idx+h])*100)
            idx += h

        return monthly

    st.header("Run Study")

    n_sim = st.slider("Monte Carlo Simulations", 100, 3000, 500)

    if st.button("Run Adequacy Study"):

        if uploaded_file is None:
            st.error("Upload load file")
            st.stop()

        load = load_8760(uploaded_file)

        with st.spinner("Running Monte Carlo..."):
            avg_lolp, avg_eens, avg_deficit, avg_available = run_monte_carlo(
                thermal_units, load, n_sim
            )

            lolp, lole, eens, nens = compute_metrics(
                avg_lolp, avg_eens, load
            )

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

        st.subheader("Monthly LOLP")

        monthly = monthly_lolp(avg_lolp)

        df_month = pd.DataFrame({
            "Month":["Jan","Feb","Mar","Apr","May","Jun",
                     "Jul","Aug","Sep","Oct","Nov","Dec"],
            "LOLP %": monthly
        })

        st.bar_chart(df_month.set_index("Month"))


# =========================================================
# CONTROLLER
# =========================================================
if case == "Thermal COPT":
    run_thermal_copt()

elif case == "Thermal + Hydro":
    run_thermal_hydro()

elif case == "Thermal Monte Carlo":
    run_thermal_monte()

else:
    st.warning("Please select a case to proceed")
