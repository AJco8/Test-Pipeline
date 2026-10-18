import pandas as pd
import argparse
from pathlib import Path
from Analysis import *
import yaml

def load_config(path: str) -> PipelineConfig:
    with open(path, "r", encoding="utf-8") as f:
        data = yaml.safe_load(f) or {}
    cfg = default_config()
    # shallow merge for simplicity
    for k, v in data.items():
        if hasattr(cfg, k):
            setattr(cfg, k, v)
    return cfg
    
def save_output(data: pd.DataFrame, anomalies: pd.DataFrame, perf: pd.DataFrame, outdir: Path) -> Dict[str, Any]:
    outdir.mkdir(parents=True, exist_ok=True)

    processed_path = outdir / "processed.csv"
    anomalies.to_csv(processed_path, index=False)

    anomalies_path = outdir / "anomalies.csv"
    anomalies.to_csv(anomalies_path, index=False)

    perf_path = outdir / "performance_comparison.csv"
    perf.to_csv(perf_path, index=False)

def main()->None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--telemetry", type=str, default=None, help="Path to telemetry CSV")
    ap.add_argument("--config","--options","--ops", type=str, default=None, help="Path to JSON configuration options")
    ap.add_argument("--outdir", type=str, default="data", help="Output directory")
    ap.add_argument("--show","--plots", type=bool, default=False, help="Open generated plots")
    args = ap.parse_args()

    # Load Configuration
    options = load_config(args.config)

    # Load Telemetry Data
    telem_data = load_data(args.telemetry)

    pipeline(telem_data,options,args.outdir)

    
if __name__ == "__main__":
    main()