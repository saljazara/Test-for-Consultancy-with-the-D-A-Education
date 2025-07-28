import pandas as pd
import os

# Define paths
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "01_rawdata")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

# Load datasets
anc4 = pd.read_csv(os.path.join(RAW_DATA_DIR, "ANC4.CSV"))
sba = pd.read_csv(os.path.join(RAW_DATA_DIR, "SBA.CSV"))
status = pd.read_excel(os.path.join(RAW_DATA_DIR, "On-track and off-track countries.xlsx"))
population = pd.read_excel(os.path.join(RAW_DATA_DIR, "WPP2022_GEN_F01_DEMOGRAPHIC_INDICATORS_COMPACT_REV1.xlsx"))

# Filter most recent year (2018–2022)
anc4_filtered = anc4[anc4["TIME_PERIOD"].between(2018, 2022)]
sba_filtered = sba[sba["TIME_PERIOD"].between(2018, 2022)]

# Keep latest year per country
anc4_latest = anc4_filtered.sort_values("TIME_PERIOD").groupby("REF_AREA:Geographic area").last().reset_index()
sba_latest = sba_filtered.sort_values("TIME_PERIOD").groupby("REF_AREA:Geographic area").last().reset_index()

# Merge ANC4 and SBA
merged = pd.merge(anc4_latest[["REF_AREA:Geographic area", "OBS_VALUE"]], 
                  sba_latest[["REF_AREA:Geographic area", "OBS_VALUE"]],
                  on="REF_AREA:Geographic area", suffixes=("_ANC4", "_SBA"))

# Add country status (on-track / off-track)
merged = merged.rename(columns={"REF_AREA:Geographic area": "ISO3Code"})
merged = pd.merge(merged, status, on="ISO3Code", how="inner")

# Prepare population births data (2022)
births = population[(population["Year"] == 2022)][["ISO3 Alpha-code", "Births (thousands)"]]
births = births.rename(columns={"ISO3 Alpha-code": "ISO3Code", "Births (thousands)": "Births_2022"})

# Merge births
merged = pd.merge(merged, births, on="ISO3Code", how="inner")

# Calculate weighted ANC4 and SBA by birth count
for service in ["ANC4", "SBA"]:
    merged[f"{service}_weighted"] = merged[f"OBS_VALUE_{service}"] * merged["Births_2022"]

# Group by status and compute weighted average
grouped = merged.groupby("Status.U5MR").agg({
    "ANC4_weighted": "sum",
    "SBA_weighted": "sum",
    "Births_2022": "sum"
}).reset_index()

grouped["ANC4_pop_weighted"] = grouped["ANC4_weighted"] / grouped["Births_2022"]
grouped["SBA_pop_weighted"] = grouped["SBA_weighted"] / grouped["Births_2022"]

# Save to CSV
grouped.to_csv(os.path.join(OUTPUT_DIR, "population_weighted_coverage.csv"), index=False)

print("✅ Population-weighted ANC4 and SBA coverage calculated and saved.")
