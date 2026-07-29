import subprocess

try:
    subprocess.run(["playwright", "install", "chromium"], check=True)
except Exception as e:
    print(f"Playwright install warning: {e}")

import streamlit as st
from src.agent import run_agent

st.set_page_config(page_title="QA Testing Agent", layout="wide")
st.title("Autonomous QA Testing Agent")
st.write("Give it a URL and a goal — it drives a real browser, decides its own next steps, and reports what it did.")

target_url = st.text_input("Target URL", value="https://srs-test-agent-ai.streamlit.app/")

uploaded_file = st.file_uploader("File to upload during the test (optional)", type=["docx"])
file_path = None
if uploaded_file:
    file_path = uploaded_file.name
    with open(file_path, "wb") as f:
        f.write(uploaded_file.getbuffer())

default_goal = (
    "Upload the provided SRS document and click Analyze. "
    "Confirm the app shows 'Found' requirements text."
)
goal = st.text_area("Testing goal", value=default_goal, height=100)

max_steps = st.slider("Max steps", min_value=2, max_value=12, value=6)

if st.button("Run Agent", type="primary"):
    if uploaded_file and file_path:
        goal = goal.replace("the provided SRS document", f"the file '{file_path}'")

    st.divider()
    step_container = st.container()
    history = []

    with st.spinner("Agent running..."):
        for event in run_agent(target_url, goal, max_steps=max_steps):
            if event["type"] == "warning":
                st.warning(event["message"])

            elif event["type"] == "step":
                with step_container:
                    with st.expander(
                        f"Step {event['step']}: {event['action']} → {event['target']}",
                        expanded=True,
                    ):
                        col1, col2 = st.columns([1, 1])
                        with col1:
                            st.image(event["screenshot"], use_container_width=True)
                        with col2:
                            st.markdown(f"**Reasoning:** {event['reasoning']}")
                            st.markdown(f"**Result:** {event['result']}")

            elif event["type"] == "done":
                history = event["history"]

    st.divider()
    st.success(f"Run complete — {len(history)} steps taken.")

    report_lines = ["# QA Agent Run Report\n", f"**Goal:** {goal}\n", f"**Target URL:** {target_url}\n\n"]
    for i, h in enumerate(history, 1):
        report_lines.append(f"## Step {i}: {h['action']} → {h.get('target_text')}\n")
        report_lines.append(f"- Reasoning: {h['reasoning']}\n")
        report_lines.append(f"- Result: {h['step_result']}\n\n")
    report_md = "\n".join(report_lines)

    st.download_button("Download Report (Markdown)", report_md, "qa_agent_report.md")
