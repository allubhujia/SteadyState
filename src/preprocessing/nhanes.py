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

ROOT = Path(__file__).resolve().parents[2]
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
        if df[col].dtype == object:
            df[col] = df[col].str.decode("utf-8").str.strip()
        else:
            df[col] = df[col].mask(df[col].abs()<SAS_ZERO, 0.0)
    df["SEQN"] = df["SEQN"].astype(int)
    return df

def hms_to_seconds(s: pd.Series) -> pd.Series:
    parts = s.str.split(":", expand = True).astype(int)
    return parts[0]*3600+parts[1]*60+parts[2]

def load_demographics(cycle: str) -> pd.DataFrame:
    d = read_xpt(cycle, "DEMO")
    out = pd.DataFrame({
        "SEQN": d["SEQN"],
        "cycle": cycle,
        "age": d["RIDAGEYR"],
        "female": (d["RIAGENDR"]==2).astype(int),
        "race_eth": d["RIDRETH3"],
        "education": d["DMDEDUC2"].where(d["DMDEDUC2"].between(1, 5)),
        "income_poverty_ratio": d["INDFMPIR"],
        "wt_mec_2yr": d["WTMEC2YR"],
        "psu": d["SDMVPSU"],
        "strata": d["SDMVSTRA"],
    })
    out["wt_mec_4yr"] = out["wt_mec_2yr"]/2
    return out

def load_sleep_questionnaire(cycle: str) -> pd.DataFrame:
    s = read_xpt(cycle, "SLQ")
    yes_no = lambda c: s[c].map({1: 1, 2: 0})
    return pd.DataFrame({
        "SEQN" : s["SEQN"],
        "self_report_sleep_h": s["SLD010H"].where(s["SLD010H"] < 77),
        "told_trouble_sleeping": yes_no("SLQ050"),
        "told_sleep_disorder": yes_no("SLQ060"),
    })

def load_cognition(cycle: str) -> pd.DataFrame:
    c = read_xpt(cycle, "CFQ")
    return pd.DataFrame({
        "SEQN":c["SEQN"],
        "cog_language": c["CFALANG"].map({1: "English", 2: "Spanish"}),
        "cerad_immediate": c[["CFDCST1", "CFDCST2", "CFDCST3"]].sum(axis=1, min_count=3),
        "cerad_delayed": c["CFDCSR"],
        "animal_fluency": c["CFDAST"],
        "digit_symbol": c["CFDDS"],
    })

COG_TESTS = ["cerad_immediate", "cerad_delayed", "animal_fluency", "digit_symbol"]

def load_nights(cycle: str) -> pd.DataFrame:
    hd = read_xpt(cycle, "PAXHD")
    hd = hd[hd["PAXSTS"]==1][["SEQN", "PAXFTIME"]]
    hd["start_s"] = hms_to_seconds(hd["PAXFTIME"])

    hr = read_xpt(cycle, "PAXHR").merge(hd[["SEQN", "start_s"]], on="SEQN")
    t = hr["start_s"]+hr["PAXSSNHP"]/80
    hr["night"] = np.floor((t-12*3600)/86400).astype(int)

    hr["h_since_noon"] = ((t-12*3600)%86400)/3600+hr["PAXTMH"]/120
    hr["sleep_x_h"] = hr["PAXSWMH"]*hr["h_since_noon"]
    hr["nap_min"] = hr["PAXSWMH"].where(hr["h_since_noon"] < NAP_END_HOUR-12, 0)
    hr["weekday"] = hr["PAXDAYWH"].astype(int)

    g = hr.groupby(["SEQN", "night"])
    n = g.agg(
        weekday=("weekday", "first"),
        sleep_min=("PAXSWMH", "sum"),
        wake_min=("PAXWWMH", "sum"),
        nonwear_min=("PAXNWMH", "sum"),
        unknown_min=("PAXUMH", "sum"),
        valid_min=("PAXVMH", "sum"),
        nap_min=("nap_min", "sum"),
        mims_total=("PAXMTSH", "sum"),
        lux_total=("PAXLXSH", "sum"),
        sleep_x_h=("sleep_x_h", "sum"),
    ).reset_index()

    n["wear_min"] = n["sleep_min"]+n["wake_min"]+n["unknown_min"]
    n["sleep_h"]=n["sleep_min"]/60
    n["valid_night"]=(
        (n["wear_min"] >= MIN_WEAR_MIN_PER_NIGHT)
        & n["sleep_h"].between(*SLEEP_H_RANGE)
    ).astype(int)

    n["sleep_midpoint_h_since_noon"] = n["sleep_x_h"]/n["sleep_min"].replace(0, np.nan)
    n["sleep_midpoint_clock_h"] = (12 + n["sleep_midpoint_h_since_noon"])%24
    n["lux_mean"] = n["lux_total"]/n["valid_min"].replace(0, np.nan)
    return n.drop(columns=["sleep_x_h", "lux_total"])

def add_within_person_deviation(n: pd.DataFrame) -> pd.DataFrame:
    g = n.groupby("SEQN")["sleep_h"]
    n["sleep_h_dev"] = n["sleep_h"] - g.transform("mean")
    n["sleep_h_z"] = n["sleep_h_dev"] / g.transform("std")
    return n

def summarise_nights(n: pd.DataFrame) -> pd.DataFrame:
    g = n.groupby("SEQN")
    s = g.agg(
        n_valid_nights=("sleep_h", "size"),
        sleep_h_mean=("sleep_h", "mean"),
        sleep_h_sd=("sleep_h", "std"),
        sleep_h_min=("sleep_h", "min"),
        sleep_h_max=("sleep_h", "max"),
        nap_min_mean=("nap_min", "mean"),
        midpoint_h_since_noon_mean=("sleep_midpoint_h_since_noon", "mean"),
        midpoint_h_sd=("sleep_midpoint_h_since_noon", "std"),
        mims_per_day=("mims_total", "mean"),
        lux_mean=("lux_mean", "mean"),
    ).reset_index()
    s["sleep_h_cv"] = s["sleep_h_sd"]/s["sleep_h_mean"]
    return s

def add_cognitive_composite(df: pd.DataFrame) -> pd.DataFrame:
    df["cog_complete"] = df[COG_TESTS].notna().all(axis=1).astype(int)
    ref = df[df["cog_complete"]==1]
    for t in COG_TESTS:
        df[f"{t}_z"] = (df[t]-ref[t].mean())/ref[t].std()
    df["cog_composite_z"] = df[[f"{t}_z" for t in COG_TESTS]].mean(axis=1, skipna=False)
    return df


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)

    demo, slq, cog, nights = [], [], [], []
    for cycle in CYCLES:
        print(f"Reading {cycle} ...")
        demo.append(load_demographics(cycle))
        slq.append(load_sleep_questionnaire(cycle))
        cog.append(load_cognition(cycle))
        nights.append(load_nights(cycle))
    demo, slq, cog, nights = (pd.concat(x, ignore_index=True) for x in (demo, slq, cog, nights))

    older = set(demo.loc[demo["age"] >= MIN_AGE, "SEQN"])
    nights = nights[nights["SEQN"].isin(older) & (nights["valid_night"] == 1)]
    counts = nights.groupby("SEQN").size()
    keep = set(counts[counts >= MIN_VALID_NIGHTS].index)
    nights = add_within_person_deviation(nights[nights["SEQN"].isin(keep)].copy())

    participants = (
        demo[demo["SEQN"].isin(keep)]
        .merge(slq, on="SEQN", how="left")
        .merge(cog, on="SEQN", how="left")
        .merge(summarise_nights(nights), on="SEQN", how="left")
    )
    participants = add_cognitive_composite(participants)

    nights = nights.drop(columns="valid_night")
    nights.to_csv(OUT/ "nhanes_nights.csv", index=False)
    participants.to_csv(OUT/ "nhanes_participants.csv", index=False)

    print(f"Age {MIN_AGE}+ with >= {MIN_VALID_NIGHTS} valid nights: {len(participants):,}")
    print(f" With complete cognition: {participants['cog_complete'].sum():,}")
    print(f"Nights: {len(nights):,}")
    print(f"Wrote {OUT}")

if __name__ == "__main__":
    main()
