"""Preprocess NHANES 2011-2014 into analysis-ready tables.

Reads  data/raw/nhanes/{2011-2012,2013-2014}/*.xpt
Writes data/processed/nhanes/
    nhanes_nights.csv        one row per participant-night (noon-to-noon window)
    nhanes_participants.csv  one row per participant: demographics, sleep
                             questionnaire, cognition, 7-day sleep summary

Run from the repo root:  python src/preprocessing/nhanes.py
"""

from pathlib import Path
import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parent[2]
RAW = ROOT / "data" / "raw" / "nhanes"
OUT = ROOT / "data" / "processed" / "nhanes" 

CYCLES = {"2011-2012": "G", "2013-2014": "H"}

MIN_AGE = 60
MIN_WEAR_MIN_PER_NIGHT = 1200
MIN_VALID_NIGHTS = 4
NAP_END_HOUR = 18
SLEEP_H_RANGE = (2, 16)

SAS_ZERO = 1e-10

def read_xpt(cycle: str, name: str) -> pd.DataFrame:
    sfx = CYCLES[cycle]
    df = pd.read_sas(RAW / cycle / f"{name}_{sfx}.xpt", format="xport")
    for col in df.columns:
        if df[col].dtyp == object:
            df[col] = df[col].str.decode("utf-8").str.strip()
        else:
            df[col] = df[col].mask(df[col].abs()<SAS_ZERO, 0.0)
    df["SEQN"] = df["SEQN"].astype(int)
    return df

def hms_to_seconds(s: pd.Series) -> pd.Series:
    parts = s.str.split(":", expand = True).astype(int)
    return parts[0]*3600+parts[1]*60+parts[2]

