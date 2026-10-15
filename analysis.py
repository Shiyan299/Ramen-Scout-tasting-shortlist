"""Shared transformations for the dashboard and notebook."""
from pathlib import Path
import pandas as pd

DATA_PATH = Path(__file__).with_name("ramen-ratings.csv")
THRESHOLD = 4.0
MIN_BRAND_RECORDS = 5

def load_data(path=DATA_PATH):
    data = pd.read_csv(path)
    required = {"Review #", "Brand", "Variety", "Style", "Country", "Stars", "Top Ten"}
    if not required.issubset(data.columns):
        raise ValueError(f"Missing columns: {sorted(required - set(data.columns))}")
    data = data.copy()
    for name in ["Brand", "Variety", "Style", "Country"]:
        data[name] = data[name].astype("string").str.strip().replace("", pd.NA)
    data["Style"] = data["Style"].fillna("Unknown")
    data["Country"] = data["Country"].fillna("Unknown")
    data["Origin"] = data["Country"].replace({"Taiwan": "Taiwan, China", "Hong Kong": "Hong Kong, China"})
    data["Score"] = pd.to_numeric(data["Stars"], errors="coerce")
    data.loc[~data["Score"].between(0, 5), "Score"] = float("nan")
    data["High rated"] = data["Score"].ge(THRESHOLD)
    return data

def filter_data(data, origins, styles):
    """Empty selection returns no matches."""
    return data.loc[data["Origin"].isin(origins) & data["Style"].isin(styles)].copy()

def headline(data):
    rated = data.dropna(subset=["Score"])
    n = len(rated)
    high = int(rated["High rated"].sum())
    return {"rated": n, "high": high, "share": high / n if n else None}

def brand_summary(data, minimum=MIN_BRAND_RECORDS):
    rated = data.dropna(subset=["Score"])
    summary = rated.groupby("Brand", dropna=False).agg(rated=("Score", "size"), high=("High rated", "sum"), mean=("Score", "mean")).reset_index()
    summary["share"] = summary["high"] / summary["rated"]
    return summary.loc[summary["rated"].ge(minimum)].sort_values(["share", "rated", "Brand"], ascending=[False, False, True]).reset_index(drop=True)

def shortlist(data):
    return data.loc[data["High rated"], ["Review #", "Brand", "Variety", "Style", "Origin", "Score"]].sort_values(["Score", "Brand", "Variety", "Review #"], ascending=[False, True, True, True]).reset_index(drop=True)
