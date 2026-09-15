"""Interactive Streamlit dashboard for the multi-agent farm."""

from __future__ import annotations

import pandas as pd
import plotly.express as px
import streamlit as st

from precision_farm.simulation import FarmSimulation, SimulationConfig

st.set_page_config(page_title="Precision Farm MAS", page_icon="🌱", layout="wide")
st.title("Precision Farm · Multi-Agent Simulator")
st.caption("Decentralized monitoring, Contract Net allocation and adaptive resource management")

with st.sidebar:
    st.header("Scenario")
    scenario = st.selectbox("Environment", ["mixed", "normal", "drought", "pest", "failure"])
    ticks = st.slider("Simulation ticks", 20, 120, 60, 5)
    seed = st.number_input("Random seed", 0, 9999, 42)
    water = st.slider("Initial water", 150, 1000, 650, 25)
    fertilizer = st.slider("Initial fertilizer", 50, 400, 180, 10)
    run = st.button("Run simulation", type="primary", width="stretch")

key = (scenario, ticks, seed, water, fertilizer)
if run or st.session_state.get("farm_key") != key:
    config = SimulationConfig(
        scenario=scenario, ticks=ticks, seed=int(seed), water=water, fertilizer=fertilizer
    )
    st.session_state.farm_result = FarmSimulation(config).run()
    st.session_state.farm_key = key

result = st.session_state.farm_result
history = pd.DataFrame(result["history"])
zones = pd.DataFrame(result["zones"])
tasks = pd.DataFrame(result["tasks"])
messages = pd.DataFrame(result["message_log"])
metrics = result["metrics"]

columns = st.columns(5)
columns[0].metric("Final crop health", f"{history.iloc[-1].average_crop_health:.1f}%")
columns[1].metric("Harvested yield", f"{metrics['harvested_yield']:.1f}")
columns[2].metric("Water used", f"{metrics['water_used']:.0f} L")
columns[3].metric("Completed tasks", metrics["completed_tasks"])
columns[4].metric("Messages", metrics["messages"])

left, right = st.columns([1.5, 1])
with left:
    st.subheader("Farm evolution")
    chart = history.melt(
        "tick",
        value_vars=["average_crop_health", "average_moisture", "average_nutrients"],
        var_name="metric",
        value_name="value",
    )
    st.plotly_chart(px.line(chart, x="tick", y="value", color="metric"), width="stretch")
with right:
    st.subheader("Current crop-health map")
    pivot = zones.pivot(index="row", columns="column", values="crop_health")
    st.plotly_chart(
        px.imshow(pivot, text_auto=".0f", color_continuous_scale="RdYlGn", zmin=0, zmax=100),
        width="stretch",
    )

tab1, tab2, tab3 = st.tabs(["Contract Net tasks", "Agent messages", "Zone state"])
with tab1:
    if tasks.empty:
        st.info("No task was required in this run.")
    else:
        st.dataframe(tasks.drop(columns=["bids"], errors="ignore"), width="stretch")
        st.bar_chart(tasks.status.value_counts())
with tab2:
    st.dataframe(
        messages[["tick", "sender", "recipient", "performative", "conversation_id"]],
        width="stretch",
    )
with tab3:
    st.dataframe(zones, width="stretch")

st.caption(
    "The simulation object advances time only. Monitoring agents initiate tasks "
    "and select contractors from peer bids."
)
