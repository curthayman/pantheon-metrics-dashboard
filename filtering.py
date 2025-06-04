import subprocess
import pandas as pd
import io

def get_performance_sites():
    result = subprocess.run(
        ["terminus", "site:list", "--format=csv"],
        capture_output=True, text=True, check=True
    )
    df = pd.read_csv(io.StringIO(result.stdout))
    filtered_df = df[df["Plan"].isin(["Performance Large", "Performance 2XL", "Performance Extra Large"])]
    return filtered_df

# Example usage:
if __name__ == "__main__":
    perf_sites = get_performance_sites()
    print(perf_sites)
