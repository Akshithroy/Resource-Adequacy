import streamlit as st
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt

def main():

    st.header("Thermal COPT")

    # =========================================================
    # THERMAL DATA
    # =========================================================

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
                "FOR",
                min_value=0.0,
                max_value=1.0,
                value=0.02,
                key=f"{p_i}_{u_i}"
            )

            thermal_units.append({"cap": cap, "FOR": FOR})
            total_capacity += cap


    st.metric("Total Capacity (MW)", round(total_capacity,2))


    total_units = len(thermal_units)
    avg_unit_size = total_capacity / total_units

    c1, c2, c3 = st.columns(3)

    c1.metric("Total Units", total_units)
    c2.metric("Total Capacity (MW)", round(total_capacity,2))
    c3.metric("Avg Unit Size (MW)", round(avg_unit_size,2))


    # =========================================================
    # LOAD MODEL
    # =========================================================

    st.header("Load Model")

    peak_load = st.slider(
        "Peak Load (MW)",
        0,1000,400
    )


    def build_load(peak):
        daily = 0.7 + 0.3*np.sin(np.linspace(0,2*np.pi,24))
        yearly = np.tile(daily,365)
        noise = np.random.normal(0,0.03,size=8760)
        return yearly*peak*(1+noise)


    def build_copt(units):

        copt={0:1.0}

        for u in units:

            cap=int(round(u["cap"]))
            FOR=u["FOR"]

            new_copt={}

            for outage,prob in copt.items():

                new_copt[outage]=(
                    new_copt.get(outage,0)
                    + prob*(1-FOR)
                )

                new_copt[outage+cap]=(
                    new_copt.get(outage+cap,0)
                    + prob*FOR
                )

            copt=new_copt


        df=pd.DataFrame({
            "Outage MW":list(copt.keys()),
            "Probability":list(copt.values())
        })

        total_cap=sum(
            u["cap"] for u in units
        )

        df["Available MW"]=(
            total_cap-df["Outage MW"]
        )

        return df.sort_values(
            "Outage MW"
        ).reset_index(drop=True)



    def compute_metrics(copt_df,load):

        total_lolp=0
        total_eens=0
        loss_hours=0

        hourly_lolp=[]
        eens_profile=[]

        for L in load:

            loss_prob=0
            eens_hour=0

            for _,row in copt_df.iterrows():

                if row["Available MW"]<L:
                    loss_prob+=row["Probability"]

                    eens_hour += (
                        L-row["Available MW"]
                    )*row["Probability"]

            hourly_lolp.append(loss_prob)
            eens_profile.append(eens_hour)

            loss_hours+=loss_prob
            total_lolp+=loss_prob
            total_eens+=eens_hour


        LOLP=(total_lolp/len(load))*100
        EENS=total_eens
        NENS=(EENS/sum(load))*100

        return (
            LOLP,EENS,NENS,
            loss_hours,
            hourly_lolp,
            eens_profile
        )


    if st.button("Run Adequacy Study"):

        load=build_load(peak_load)
        copt_df=build_copt(thermal_units)

        results=compute_metrics(
            copt_df,
            load
        )

        st.session_state["load"]=load
        st.session_state["copt"]=copt_df
        st.session_state["results"]=results


    if "load" in st.session_state:

        load=st.session_state["load"]
        copt_df=st.session_state["copt"]

        (
            LOLP,EENS,NENS,
            LOLE,
            hourly_lolp,
            eens_profile
        )=st.session_state["results"]


        st.markdown(
            "## 📊 System Reliability Overview"
        )

        c1,c2,c3,c4=st.columns(4)

        c1.metric(
            "LOLP",
            f"{LOLP:.3f} %"
        )

        c2.metric(
            "EENS",
            f"{EENS:.1f} MWh"
        )

        c3.metric(
            "NENS",
            f"{NENS:.4f} %"
        )

        c4.metric(
            "LOLE",
            f"{LOLE:.2f} hrs"
        )


        if LOLP<=0.2 and NENS<=0.05:
            st.success(
                "System is ADEQUATE ✅"
            )
        else:
            st.error(
                "System is NOT ADEQUATE ❌"
            )

  # ================= SUMMARY =================
        st.markdown("### ⚡ System Summary")
        st.write(f"""
        - Installed Capacity: **{round(total_capacity,1)} MW**
        - Peak Demand: **{peak_load} MW**
        - Reserve Margin: **{round((total_capacity-peak_load)/peak_load*100,2)} %**
        """)
        df_hour=pd.DataFrame({
            "Hour":np.arange(8760),
            "LOLP":hourly_lolp
        })

        df_hour["Month"]=(
            df_hour["Hour"]//730
        )+1

        monthly=df_hour.groupby(
            "Month"
        )["LOLP"].mean()


        fig_hourly,ax1=plt.subplots()
        ax1.plot(
            df_hour["Hour"],
            df_hour["LOLP"]
        )

        fig_monthly,ax2=plt.subplots()
        monthly.plot(
            kind='bar',
            ax=ax2
        )

        col1,col2=st.columns(2)

        with col1:
            st.pyplot(fig_hourly)

        with col2:
            st.pyplot(fig_monthly)


        st.dataframe(
            copt_df,
            use_container_width=True
        )

  
