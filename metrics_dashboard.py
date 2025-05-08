import streamlit as st
import subprocess
import re
from datetime import datetime
import time
import pandas as pd
import plotly.graph_objects as go

st.set_page_config(page_title="Terminus Metrics Dashboard", layout="wide")

st.markdown("""
# Terminus Metrics Analyzer
Created by Curt Hayman, CEH

This dashboard fetches and analyzes Pantheon site metrics using the Terminus CLI.
""")

# Form for user input
with st.form("metrics_form"):
    site_name = st.text_input("Enter the site name")
    env_name = st.text_input("Enter the environment name")
    period = st.selectbox("Select the period", ["day", "week", "month"])
    submitted = st.form_submit_button("Get Metrics")

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
        pass
    return df

def extract_cache_hit_ratios(df):
    if df is None or "Period" not in df or "Cache Hit Ratio" not in df:
        return []
    return list(zip(df["Period"], df["Cache Hit Ratio"]))

if submitted and site_name and env_name and period:
    st.info("Running Terminus command. Please wait...")
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
        reformatted_output = reformat_date_in_output(result.stdout)
        st.subheader("Metrics Table (Raw Output)")
        st.code(reformatted_output, language="text")

        df = parse_table_to_df(reformatted_output)
        if df is not None:
            st.subheader("Metrics Table (Parsed)")
            st.dataframe(df, use_container_width=True)

            # CSV Export
            csv = df.to_csv(index=False).encode('utf-8')
            st.download_button(
                label="Download data as CSV",
                data=csv,
                file_name=f"{site_name}_{env_name}_metrics.csv",
                mime='text/csv',
            )

            # Charts
            st.subheader("Charts")
            st.line_chart(df.set_index("Period")[["Visits", "Pages Served"]])
            st.line_chart(df.set_index("Period")[["Cache Hit Ratio"]])

            # Cache Efficiency Gauge (Plotly)
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
        else:
            st.warning("Could not parse table output for advanced features.")

        # Errors
        error_text = ""
        if result.stderr:
            error_lines = result.stderr.splitlines()
            filtered_errors = [line for line in error_lines if "Deprecated" not in line]
            if filtered_errors:
                error_text = "\n".join(filtered_errors)
                st.error(error_text)

        # Cache Hit Ratio Breakdown
        cache_data = extract_cache_hit_ratios(df) if df is not None else []
        summary_text = f"The output above displays the performance metrics for the site '{site_name}' in the '{env_name}' environment over the chosen period of '{period}'. It includes key data such as total visits, pages served, and cache performance (hits, misses, and hit ratio). This information can help assess the site's traffic patterns and caching efficiency, identifying potential areas for optimization if cache misses are high or hit ratios are lower than expected."
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
            cache_breakdown_text = "Cache Hit Ratio Breakdown: Unable to extract data. Please check the debug info above for details on output format issues.\n"
        st.subheader("Cache Hit Ratio Breakdown")
        st.text(cache_breakdown_text)

    except Exception as e:
        st.error(f"An error occurred: {str(e)}")