import subprocess
import time
import re
import sys
from tqdm import tqdm
from datetime import datetime
import html

# Help text to display with -h or --help
HELP_TEXT = """
Terminus Metrics Script - Help
==============================
This script fetches performance metrics for a site using 'terminus env:metrics'. It reformats dates, summarizes Cache Hit Ratio, and optionally saves output to HTML.

Usage:
  python metrics.py [-h|--help]

Options:
  -h, --help    Show this help message and exit.

Prerequisites:
  - Python 3.x (check with 'python3 --version')
  - Terminus CLI (must be installed and accessible)
  - Python package: tqdm (install with 'pip install tqdm')
  - If you get a auth error, you have to run this command in order to log back in - terminus auth:login --email=<loginemail>

Steps:
  1. Run the script: 'python metrics.py'
  2. Enter site name, environment name, and period (day/week/month) when prompted.
  3. Choose whether to save output to an HTML file.
  4. View results in terminal and/or saved HTML file.

Note: Ensure 'terminus' is in your PATH and you have necessary permissions to run metrics commands.
"""

# Check for help flag
if len(sys.argv) > 1 and sys.argv[1] in ['-h', '--help']:
    print(HELP_TEXT)
    sys.exit(0)

# Display ASCII art graph at the start, just wanted to add something fun :)
ASCII_GRAPH = """
   Terminus Metrics Analyzer - Created by Curt Hayman, CEH
   ------------------------
       Metrics Graph
          /|       80%
         / |       60%
        /  |       40%
       /___|       20%
      |    |________
      | Visits | Pages
   ------------------------
"""
print(ASCII_GRAPH)

# Prompt user for site name, environment name, and period
site_name = input("Enter the site name: ")
env_name = input("Enter the environment name: ")
period = input("Enter the period (day, week, or month): ").lower()

# Validate period input
while period not in ["day", "week", "month"]:
    print("Invalid period. Please choose 'day', 'week', or 'month'.")
    period = input("Enter the period (day, week, or month): ").lower()

# Prompt user for HTML output option
save_to_html = input("Would you like to save the output to an HTML file? (yes/no): ").lower()
html_filename = ""
if save_to_html in ["yes", "y"]:
    html_filename = input("Enter the HTML filename (e.g., output.html): ")

# Define parameters
datapoints = "auto"  # Use 'auto' for reasonable default
format = "table"  # Use table format for pretty output
fields = "Period,Visits,Pages Served,Cache Hits,Cache Misses,Cache Hit Ratio"  # Fields with spaces as in help output

# Constructing the command
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

# Function to reformat dates in the output from YYYY-MM-DD to MM-DD-YYYY
def reformat_date_in_output(output):
    date_pattern = r'\b(\d{4})-(\d{2})-(\d{2})\b'
    def replace_date(match):
        try:
            date_str = match.group(0)
            reformatted = datetime.strptime(date_str, "%Y-%m-%d").strftime("%m-%d-%Y")
            return reformatted
        except ValueError:
            return date_str  # Return original if not a valid date
    return re.sub(date_pattern, replace_date, output)

# Function to parse Cache Hit Ratio from the output
def extract_cache_hit_ratios(output):
    cache_data = []
    lines = output.splitlines()
    header_found = False
    header_line = None
    for i, line in enumerate(lines):
        if "Period" in line and "Cache Hit Ratio" in line:
            header_found = True
            header_line = line
            continue
        if header_found and line.strip():
            parts = re.split(r'\s{2,}|\t|,', line)
            parts = [p.strip() for p in parts if p.strip()]
            if len(parts) >= 2:
                try:
                    period_val = parts[0]
                    ratio_val = parts[-1].strip('%')
                    if ratio_val.replace('.', '').isdigit():
                        cache_data.append((period_val, float(ratio_val)))
                except (ValueError, IndexError):
                    continue
    if not header_found:
        print("\nDebug Info: Could not find header with 'Period' and 'Cache Hit Ratio' in output.")
    else:
        print(f"\nDebug Info: Header found: {header_line}")
        print(f"Debug Info: Parsed {len(cache_data)} data rows.")
        if not cache_data and header_found:
            print("Debug Info: No data rows parsed. Possible mismatch in table structure or delimiters.")
    return cache_data

# Function to convert text output to HTML format
def create_html_output(reformatted_output, error_text, summary_text, cache_breakdown_text, site_name):
    # Escape special characters to prevent HTML injection and preserve formatting
    output_escaped = html.escape(reformatted_output)
    errors_section = f'<div class="section"><h2>Errors</h2><pre>{html.escape(error_text)}</pre></div>' if error_text else ""
    summary_escaped = html.escape(summary_text)
    cache_breakdown_escaped = html.escape(cache_breakdown_text)
    site_name_escaped = html.escape(site_name)
    
    html_content = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Terminus Metrics Output</title>
    <style>
        body {{ font-family: 'Courier New', Courier, monospace; background-color: #f0f0f0; color: #333; margin: 20px; line-height: 1.5; }}
        .container {{ max-width: 900px; margin: 0 auto; background-color: #fff; padding: 20px; border: 1px solid #ccc; box-shadow: 0 0 10px rgba(0,0,0,0.1); }}
        pre {{ white-space: pre-wrap; background-color: #e8e8e8; padding: 10px; border-radius: 5px; overflow-x: auto; }}
        h2 {{ color: #2c3e50; }}
        .section {{ margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Terminus Metrics Report for {site_name_escaped}</h1>
        <div class="section">
            <h2>Command Output</h2>
            <pre>{output_escaped}</pre>
        </div>
        {errors_section}
        <div class="section">
            <h2>Summary of Findings</h2>
            <pre>{summary_escaped}</pre>
        </div>
        <div class="section">
            <h2>Cache Hit Ratio Breakdown</h2>
            <pre>{cache_breakdown_escaped}</pre>
        </div>
    </div>
</body>
</html>"""
    return html_content

# Run the command with a progress bar
try:
    print("Running command, please wait...")
    with tqdm(total=100, desc="Processing") as pbar:
        result = subprocess.run(command, capture_output=True, text=True)
        for i in range(100):
            time.sleep(0.02)  # Simulate some work being done
            pbar.update(1)
    
    # Reformat dates in the output
    reformatted_output = reformat_date_in_output(result.stdout)
    print(reformatted_output)
    
    # Handle errors
    error_text = ""
    if result.stderr:
        error_lines = result.stderr.splitlines()
        filtered_errors = [line for line in error_lines if "Deprecated" not in line]
        if filtered_errors:
            error_text = "\n".join(filtered_errors)
            print("Errors:")
            print(error_text)
    
    # Extract Cache Hit Ratio data for summary
    cache_data = extract_cache_hit_ratios(result.stdout)
    
    # Summary of findings
    summary_text = f"The output above displays the performance metrics for the site '{site_name}' in the '{env_name}' environment over the chosen period of '{period}'. It includes key data such as total visits, pages served, and cache performance (hits, misses, and hit ratio). This information can help assess the site's traffic patterns and caching efficiency, identifying potential areas for optimization if cache misses are high or hit ratios are lower than expected."
    print("\nSummary of Findings:")
    print(summary_text)
    
    # Cache Hit Ratio breakdown
    cache_breakdown_text = ""
    if cache_data:
        cache_breakdown_text += "Cache Hit Ratio Breakdown:\n"
        for period_val, ratio in cache_data:
            cache_breakdown_text += f" - Period {period_val}: Cache Hit Ratio is {ratio}%\n"
        ratios = [r for _, r in cache_data]
        avg_ratio = sum(ratios) / len(ratios) if ratios else 0
        cache_breakdown_text += f"   Average Cache Hit Ratio: {avg_ratio:.2f}%\n"
        if avg_ratio < 70:
            cache_breakdown_text += "   Note: Average ratio is below 70%, which may indicate caching inefficiencies. Consider reviewing cache policies or content optimization.\n"
        else:
            cache_breakdown_text += "   Note: Average ratio is above 70%, suggesting effective caching performance.\n"
    else:
        cache_breakdown_text = "Cache Hit Ratio Breakdown: Unable to extract data. Please check the debug info above for details on output format issues.\n"
    print(cache_breakdown_text)
    
    # Save to HTML if requested
    if html_filename:
        try:
            html_content = create_html_output(reformatted_output, error_text, summary_text, cache_breakdown_text, site_name)
            with open(html_filename, 'w', encoding='utf-8') as f:
                f.write(html_content)
            print(f"\nOutput successfully saved to {html_filename}")
        except Exception as e:
            print(f"\nFailed to save HTML file: {str(e)}")
except Exception as e:
    print(f"An error occurred: {str(e)}")
