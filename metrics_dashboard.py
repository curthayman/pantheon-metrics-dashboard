import streamlit as st
import subprocess
import re
from datetime import datetime
import time
import pandas as pd
import plotly.graph_objects as go
import requests
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()
SLACK_WEBHOOK_URL = os.getenv("SLACK_WEBHOOK_URL")
SLACK_CHANNEL = "#pantheonmetricsalerts"

st.set_page_config(page_title="AI Terminus Metrics Dashboard", layout="wide")
status_top = st.empty()  # Placeholder for top-of-page status messages

for key in ['df', 'reformatted_output', 'site_name', 'env_name', 'period']:
    if key not in st.session_state:
        st.session_state[key] = None

def send_slack_notification(message):
    if not SLACK_WEBHOOK_URL or "hooks.slack.com/services/" not in SLACK_WEBHOOK_URL:
        st.warning("Slack webhook URL is not set or invalid. Please update SLACK_WEBHOOK_URL in your .env file.")
        return False
    payload = {"text": message}
    try:
        response = requests.post(SLACK_WEBHOOK_URL, json=payload)
        return response.status_code == 200
    except Exception as e:
        st.error(f"Error sending Slack notification: {e}")
        return False

def get_terminus_user():
    try:
        result = subprocess.run(
            ["terminus", "auth:whoami"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

def get_php_version(site, env):
    if not site or not env:
        return "N/A"
    try:
        result = subprocess.run(
            ["terminus", "env:info", "--field=php_version", f"{site}.{env}"],
            capture_output=True, text=True, check=True
        )
        return result.stdout.strip()
    except Exception as e:
        return f"Error: {e}"

st.markdown("""
# AI Terminus Metrics Analyzer

This dashboard fetches and analyzes Pantheon site metrics using the Terminus CLI.
""")

with st.form("metrics_form"):
    site_name = st.text_input("Enter the site name")
    env_name = st.text_input("Enter the environment name")
    period = st.selectbox("Select the period", ["day", "week", "month"])
    submitted = st.form_submit_button("Get Metrics")

if site_name and env_name:
    st.session_state['site_name'] = site_name
    st.session_state['env_name'] = env_name

with st.sidebar:
    st.header("Help & Documentation")
    st.markdown("""
    **How to Use:**
    1. Enter your Pantheon site name and environment (e.g., `sitename` and `dev`).
    2. Select the period for metrics (day, week, or month).
    3. Click "Get Metrics" to fetch and analyze data.

    **What is this?**
    This dashboard uses the [Terminus CLI](https://pantheon.io/docs/terminus) to fetch site metrics from Pantheon and visualize them.

    **Troubleshooting:**
    - Ensure the Terminus CLI is installed and authenticated.
    - If you see parsing errors, check the raw output for unexpected formatting.
    - For more help, visit the [Pantheon Terminus Docs](https://pantheon.io/docs/terminus).
    """)
    st.markdown(f"**Slack notifications will be sent to:** `{SLACK_CHANNEL}`")
    st.subheader("Session Info")
    user = get_terminus_user()
    st.write(f"**Current Terminus User:** {user}")

    site_for_php = st.session_state.get('site_name', '')
    env_for_php = st.session_state.get('env_name', '')
    if site_for_php and env_for_php:
        php_version = get_php_version(site_for_php, env_for_php)
        st.write(f"**PHP Version:** {php_version}")
    else:
        st.write("**PHP Version:** N/A")

    if st.button("Send Test Slack Notification"):
        dummy_site = "example-site"
        dummy_env = "live"
        dummy_date = "2024-05-08"
        dummy_day = "Wednesday"
        dummy_recent_visits = 90000
        dummy_avg_visits = 10000
        dummy_prev_periods = ["2024-04-10", "2024-04-17", "2024-04-24", "2024-05-01"]
        dummy_prev_visits = [9500, 10200, 9800, 10500]
        dummy_percent_increase = ((dummy_recent_visits - dummy_avg_visits) / dummy_avg_visits) * 100

        test_message = (
            f":rotating_light: *Anomalous Traffic Detected!*\n"
            f"Site: {dummy_site} ({dummy_env})\n"
            f"Date: {dummy_date} ({dummy_day})\n"
            f"Recent Visits: {dummy_recent_visits:,}\n"
            f"Average (last 4 periods): {dummy_avg_visits:,.2f}\n"
            f"Previous 4 periods:\n"
            + "\n".join([f"  - {d}: {v:,} visits" for d, v in zip(dummy_prev_periods, dummy_prev_visits)]) + "\n"
            f"Increase: {dummy_percent_increase:.1f}%"
        )
        if send_slack_notification(test_message):
            st.success("Test notification sent to Slack!")
        else:
            st.error("Failed to send test notification.")

    st.markdown("---")
    st.markdown("<div style='text-align: center; font-size: 12px;'>Created with Python and Streamlit by Curt Hayman, CEH</div>", unsafe_allow_html=True)
    st.markdown("---")

def reformat_date_in_output(output):
    date_pattern = r'\b(\d{4})-(\d{2})-(\d{2})\b'
    def replace_date(match):
        try:
            date_str = match.group(0)
            reformatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m-%d-%Y")
            return reformatted
        except ValueError:
            return date_str
    return re.sub(date_pattern, replace_date, output)

def parse_table_to_df(output):
    lines = output.splitlines()
    header_idx = next((i for i, line in enumerate(lines) if "Period" in line and "Cache Hit Ratio" in line), None)
    if header_idx is None:
        return None
    header = re.split(r'\s{2,}', lines[header_idx].strip())
    data = []
    for line in lines[header_idx+2:]:
        if not line.strip() or line.strip().startswith("-"):
            continue
        row = re.split(r'\s{2,}', line.strip())
        if len(row) == len(header):
            data.append(row)
    if not data:
        return None
    df = pd.DataFrame(data, columns=header)
    for col in ["Visits", "Pages Served", "Cache Hits", "Cache Misses"]:
        df[col] = df[col].str.replace(",", "").astype(int)
    df["Cache Hit Ratio"] = df["Cache Hit Ratio"].str.replace("%", "").astype(float)
    try:
        df["Period"] = pd.to_datetime(df["Period"], format="%m-%d-%Y")
    except Exception:
        try:
            df["Period"] = pd.to_datetime(df["Period"], format="%Y-%m-%d")
        except Exception:
            pass
    return df

def extract_cache_hit_ratios(df):
    if df is None or "Period" not in df or "Cache Hit Ratio" not in df:
        return []
    return list(zip(df["Period"], df["Cache Hit Ratio"]))

df = st.session_state.get('df')
reformatted_output = st.session_state.get('reformatted_output')
site_name_state = st.session_state.get('site_name', '')
env_name_state = st.session_state.get('env_name', '')
period_state = st.session_state.get('period', '')

if submitted and site_name and env_name and period:
    status_placeholder = st.empty()
    status_placeholder.info("Running Terminus command. Please wait...")
    datapoints = "auto"
    format = "table"
    fields = "Period,Visits,Pages Served,Cache Hits,Cache Misses,Cache Hit Ratio"
    command = [
        "terminus",
        "env:metrics",
        "--period", period,
        "--datapoints", datapoints,
        "--format", format,
        "--fields", fields,
        "--",
        f"{site_name}.{env_name}"
    ]

    progress = st.progress(0)
    for i in range(50):
        time.sleep(0.01)
        progress.progress((i+1)/50)

    try:
        result = subprocess.run(command, capture_output=True, text=True)
        progress.progress(1.0)
        status_placeholder.success("Script finished loading.")

        reformatted_output = reformat_date_in_output(result.stdout)
        df = parse_table_to_df(reformatted_output)

        st.session_state['df'] = df
        st.session_state['reformatted_output'] = reformatted_output
        st.session_state['site_name'] = site_name
        st.session_state['env_name'] = env_name
        st.session_state['period'] = period

        site_name_state = site_name
        env_name_state = env_name
        period_state = period

    except Exception as e:
        status_placeholder.empty()
        st.error(f"An error occurred: {str(e)}")

if df is not None and not df.empty:
    st.subheader("Metrics Table (Parsed)")
    st.dataframe(df, use_container_width=True)

    with st.form("send_parsed_metrics_form"):
        send_parsed = st.form_submit_button("Send Parsed Metrics to Slack")
        if send_parsed:
            summary = df.head(5).to_markdown(index=False)
            slack_message = (
                f":bar_chart: *Pantheon Metrics Output*\n"
                f"Site: {site_name_state} ({env_name_state})\n"
                f"Period: {period_state}\n"
                f"```\n{summary}\n```"
            )
            if send_slack_notification(slack_message):
                st.success("Parsed metrics sent to Slack!")
            else:
                st.error("Failed to send metrics to Slack.")

    csv = df.to_csv(index=False).encode('utf-8')
    st.download_button(
        label="Download data as CSV",
        data=csv,
        file_name=f"{site_name_state}_{env_name_state}_metrics.csv",
        mime='text/csv',
    )

    st.subheader("Charts")
    st.line_chart(df.set_index("Period")[["Visits", "Pages Served"]])
    st.line_chart(df.set_index("Period")[["Cache Hit Ratio"]])

    st.subheader("Cache Efficiency Gauge")
    avg_ratio = df["Cache Hit Ratio"].mean() if not df.empty else 0
    fig = go.Figure(go.Indicator(
        mode = "gauge+number",
        value = avg_ratio,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': "Avg Cache Hit Ratio (%)"},
        gauge = {
            'axis': {'range': [0, 100]},
            'bar': {'color': "darkblue"},
            'steps': [
                {'range': [0, 50], 'color': "red"},
                {'range': [50, 70], 'color': "orange"},
                {'range': [70, 100], 'color': "green"}
            ],
        }
    ))
    st.plotly_chart(fig, use_container_width=True)

    if "Visits" in df.columns and len(df) > 4:
        recent_visits = df["Visits"].iloc[-1]
        avg_visits = df["Visits"].iloc[-5:-1].mean()
        prev_periods = df["Period"].iloc[-5:-1].dt.strftime('%Y-%m-%d').tolist()
        prev_visits = df["Visits"].iloc[-5:-1].tolist()
        anomaly_date = df["Period"].iloc[-1].strftime('%Y-%m-%d')
        anomaly_day = df["Period"].iloc[-1].strftime('%A')
        percent_increase = ((recent_visits - avg_visits) / avg_visits) * 100 if avg_visits > 0 else 0

        if avg_visits > 0 and recent_visits > avg_visits * 1.25:
            alert_message = (
                f":rotating_light: *Anomalous Traffic Detected!*\n"
                f"Site: {site_name_state} ({env_name_state})\n"
                f"Date: {anomaly_date} ({anomaly_day})\n"
                f"Recent Visits: {recent_visits:,}\n"
                f"Average (last 4 periods): {avg_visits:,.2f}\n"
                f"Previous 4 periods:\n"
                + "\n".join([f"  - {d}: {v:,} visits" for d, v in zip(prev_periods, prev_visits)]) + "\n"
                f"Increase: {percent_increase:.1f}%"
            )
            if send_slack_notification(alert_message):
                status_top.success("Slack notification sent for anomalous traffic.")
            else:
                st.error("Failed to send Slack notification.")

    cache_data = extract_cache_hit_ratios(df) if df is not None else []
    summary_text = f"The output above displays the performance metrics for the site '{site_name_state}' in the '{env_name_state}' environment over the chosen period of '{period_state}'. It includes key data such as total visits, pages served, and cache performance (hits, misses, and hit ratio). This information can help assess the site's traffic patterns and caching efficiency, identifying potential areas for optimization if cache misses are high or hit ratios are lower than expected."
    st.subheader("Summary of Findings")
    st.write(summary_text)

    cache_breakdown_text = ""
    if cache_data:
        cache_breakdown_text += "Cache Hit Ratio Breakdown:\n"
        for period_val, ratio in cache_data:
            cache_breakdown_text += f" - Period {period_val.strftime('%m-%d-%Y') if hasattr(period_val, 'strftime') else period_val}: Cache Hit Ratio is {ratio}%\n"
        ratios = [r for _, r in cache_data]
        avg_ratio = sum(ratios) / len(ratios) if ratios else 0
        cache_breakdown_text += f"   Average Cache Hit Ratio: {avg_ratio:.2f}%\n"
        if avg_ratio < 70:
            cache_breakdown_text += "   Note: Average ratio is below 70%, which may indicate caching inefficiencies. Consider reviewing cache policies or content optimization.\n"
        else:
            cache_breakdown_text += "   Note: Average ratio is above 70%, suggesting effective caching performance.\n"
    else:
        cache_breakdown_text = "Cache Hit Ratio Breakdown: Unable to extract data. Please check the output above for details on output format issues.\n"
    st.subheader("Cache Hit Ratio Breakdown")
    st.text(cache_breakdown_text)