# Pantheon Metrics Dashboard

A **Streamlit dashboard** for visualizing Pantheon site metrics using the [Terminus CLI](https://pantheon.io/docs/terminus).  
---

## 🚀 What does this do?

- Runs the `terminus env:metrics` command for your Pantheon site and environment.
- Parses and displays the results in a beautiful, interactive dashboard.
- Shows charts, a cache efficiency gauge, and a summary.
- Lets you export the parsed data as CSV.

---

## ⚠️ Requirements

- **Python 3.7+**
- **Terminus CLI** installed and accessible in your system PATH  
  [Install Terminus](https://pantheon.io/docs/terminus/install)
- **Pantheon account** with access to the site you want to monitor
- **You must be authenticated with Terminus** (`terminus auth:login`)
- The script must be run on your local machine or a server where you can install Terminus and Python packages (it will not work on Streamlit Cloud or other platforms that do not allow custom CLI tools).

---

## 🛠️ Installation

1. **Clone this repository:**
```bash
   git clone https://github.com/curthayman/pantheon-metrics-dashboard.git
```
```bash   
   cd pantheon-metrics-dashboard
```

2. **Install Python dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Install Terminus CLI:**
   https://docs.pantheon.io/terminus/install


5. **Authenticate with Terminus:**
```bash   
terminus auth:login
```
---

## ▶️ Usage

1. **Run the dashboard:**
```bash
   streamlit run metrics_dashboard.py
```
2. **In your browser:**
   Enter your Pantheon site name and environment (e.g., mysite and live)
   Select the period (day, week, or month)
   Click "Get Metrics"
   Explore the charts, gauge, and download CSV if needed
   
## 📝 Notes
   The dashboard calls the Terminus CLI under the hood, so it must be available in your system PATH.
   This dashboard cannot run on Streamlit Cloud or similar platforms, because they do not allow installing or running custom CLI tools      like Terminus.
   If you get authentication errors, run terminus auth:login in your terminal.

## 🙋‍♂️ Questions or Issues?
   Open an issue or contact Me!

## 🏆 Credits
   Created by Curt Hayman, CEH.
   - Terminus
   - Streamlit
   - pandas
   - plotly

