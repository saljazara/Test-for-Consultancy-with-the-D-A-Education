import pandas as pd
import os
import matplotlib.pyplot as plt
import seaborn as sns
import re

# ----------------------
# Define file paths
# ----------------------
RAW_DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "01_rawdata")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "outputs")

# ----------------------
# Load datasets
# ----------------------
anc4 = pd.read_csv(os.path.join(RAW_DATA_DIR, "fusion_GLOBAL_DATAFLOW_UNICEF_1.0_.MNCH_ANC4.csv"))
sba = pd.read_csv(os.path.join(RAW_DATA_DIR, "fusion_GLOBAL_DATAFLOW_UNICEF_1.0_.MNCH_SAB.csv"))
status = pd.read_excel(os.path.join(RAW_DATA_DIR, "On-track and off-track countries.xlsx"))

population = pd.read_excel(
    os.path.join(RAW_DATA_DIR, "WPP2022_GEN_F01_DEMOGRAPHIC_INDICATORS_COMPACT_REV1.xlsx"),
    sheet_name="Projections",
    skiprows=16
)

# ----------------------
# Prepare population data
# ----------------------
population = population.dropna(subset=["Year"])
population["Year"] = population["Year"].astype(int)

births_2022 = population[population["Year"] == 2022][["ISO3 Alpha-code", "Births (thousands)"]]
births_2022 = births_2022.rename(columns={
    "ISO3 Alpha-code": "ISO3Code",
    "Births (thousands)": "Births_2022"
})

# ----------------------
# Filter ANC4 and SBA data for years 2018-2022
# ----------------------
anc4_filtered = anc4[anc4["TIME_PERIOD:Time period"].between(2018, 2022)]
sba_filtered = sba[sba["TIME_PERIOD:Time period"].between(2018, 2022)]

# Extract latest per REF_AREA (by TIME_PERIOD)
anc4_latest = anc4_filtered.sort_values("TIME_PERIOD:Time period").groupby("REF_AREA:Geographic area").last().reset_index()
sba_latest = sba_filtered.sort_values("TIME_PERIOD:Time period").groupby("REF_AREA:Geographic area").last().reset_index()

# Rename observation columns for clarity
anc4_latest = anc4_latest.rename(columns={"OBS_VALUE:Observation Value": "OBS_VALUE_ANC4"})
sba_latest = sba_latest.rename(columns={"OBS_VALUE:Observation Value": "OBS_VALUE_SBA"})

# ----------------------
# Extract first 3 letters from REF_AREA as ISO3 code for merging
# ----------------------
anc4_latest["ISO3Code"] = anc4_latest["REF_AREA:Geographic area"].str[:3].str.upper()
sba_latest["ISO3Code"] = sba_latest["REF_AREA:Geographic area"].str[:3].str.upper()

# Normalize status ISO3Code too
status["ISO3Code"] = status["ISO3Code"].astype(str).str.strip().str.upper()

# ----------------------
# Merge ANC4 and SBA data on ISO3Code
# ----------------------
merged = pd.merge(
    anc4_latest[["ISO3Code", "OBS_VALUE_ANC4"]],
    sba_latest[["ISO3Code", "OBS_VALUE_SBA"]],
    on="ISO3Code",
    how="inner"
)

# Merge with status dataset on ISO3Code
merged = pd.merge(
    merged,
    status[["ISO3Code", "Status.U5MR"]],
    on="ISO3Code",
    how="inner"
)

# ----------------------
# Calculate average ANC4 and SBA coverage by Status.U5MR
# ----------------------
grouped = merged.groupby("Status.U5MR").agg({
    "OBS_VALUE_ANC4": "mean",
    "OBS_VALUE_SBA": "mean"
}).reset_index()

# Save output CSV
output_path = os.path.join(OUTPUT_DIR, "simple_average_coverage.csv")
grouped.to_csv(output_path, index=False)
print(f"Saved simple average coverage to: {output_path}")

# ----------------------
# Plotting
# ----------------------
plot_df = grouped.melt(id_vars="Status.U5MR", value_vars=["OBS_VALUE_ANC4", "OBS_VALUE_SBA"],
                       var_name="Indicator", value_name="Coverage")

# Rename indicators for better labels
plot_df["Indicator"] = plot_df["Indicator"].replace({
    "OBS_VALUE_ANC4": "ANC4",
    "OBS_VALUE_SBA": "SBA"
})

# Normalize Status.U5MR for consistent plot legend
plot_df["Status.U5MR"] = plot_df["Status.U5MR"].str.lower().replace({
    "on-track": "On-track",
    "achieved": "On-track",
    "on track": "On-track",
    "acceleration needed": "Off-track",
    "acceleration needed": "Off-track"
})

plt.figure(figsize=(8, 5))
sns.barplot(data=plot_df, x="Indicator", y="Coverage", hue="Status.U5MR", palette="Set2")
plt.title("Simple Average Coverage of ANC4 and SBA (2018-2022)")
plt.ylabel("Coverage (%)")
plt.xlabel("Indicator")
plt.ylim(0, 100)
plt.legend(title="U5MR Status")
plt.tight_layout()

plot_path = os.path.join(OUTPUT_DIR, "simple_coverage_comparison.png")
plt.savefig(plot_path)
plt.show()

# ----------------------
# Calculate population-weighted coverage by Status.U5MR
# ----------------------

# Merge births data for weighting
merged_with_births = pd.merge(merged, births_2022, on="ISO3Code", how="inner")

# Drop rows with missing data to avoid issues in weighted average
merged_clean = merged_with_births.dropna(subset=["OBS_VALUE_ANC4", "OBS_VALUE_SBA", "Births_2022"])

# Calculate weighted averages
weighted_coverage = merged_clean.groupby("Status.U5MR", group_keys=False).apply(
    lambda x: pd.Series({
        "Weighted_ANC4": (x["OBS_VALUE_ANC4"] * x["Births_2022"]).sum() / x["Births_2022"].sum(),
        "Weighted_SBA": (x["OBS_VALUE_SBA"] * x["Births_2022"]).sum() / x["Births_2022"].sum()
    })
).reset_index()

# Save weighted averages CSV
weighted_output_path = os.path.join(OUTPUT_DIR, "weighted_average_coverage.csv")
weighted_coverage.to_csv(weighted_output_path, index=False)
print(f"Saved weighted average coverage to: {weighted_output_path}")

# Prepare data for plotting
plot_weighted_df = weighted_coverage.melt(id_vars="Status.U5MR", value_vars=["Weighted_ANC4", "Weighted_SBA"],
                                         var_name="Indicator", value_name="Coverage")

# Rename indicators for plot labels
plot_weighted_df["Indicator"] = plot_weighted_df["Indicator"].replace({
    "Weighted_ANC4": "ANC4",
    "Weighted_SBA": "SBA"
})

# Normalize Status.U5MR for consistent legend
plot_weighted_df["Status.U5MR"] = plot_weighted_df["Status.U5MR"].str.lower().replace({
    "on-track": "On-track",
    "achieved": "On-track",
    "on track": "On-track",
    "acceleration needed": "Off-track",
    "acceleration needed": "Off-track"
})

# Plot weighted coverage
plt.figure(figsize=(8, 5))
sns.barplot(data=plot_weighted_df, x="Indicator", y="Coverage", hue="Status.U5MR", palette="Set2")
plt.title("Population-Weighted Coverage of ANC4 and SBA (2018-2022)")
plt.ylabel("Coverage (%)")
plt.xlabel("Indicator")
plt.ylim(0, 100)
plt.legend(title="U5MR Status")
plt.tight_layout()

weighted_plot_path = os.path.join(OUTPUT_DIR, "weighted_coverage_comparison.png")
plt.savefig(weighted_plot_path)
plt.show()


from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
from reportlab.lib.utils import ImageReader
import textwrap

# Paths
pdf_path = os.path.join(OUTPUT_DIR, "coverage_report.pdf")
plot_image_path = plot_path  # Use the plot you already saved

# Interpretation text
interpretation = """
The figure above shows the average coverage for ANC4 and SBA indicators for countries grouped by 
their under-five mortality rate (U5MR) status as either On-track or Off-track towards sustainable development goals. 

Population-weighted averages account for country size differences using projected births in 2022. 

Note that data quality and reporting periods vary; hence, conclusions should be considered indicative, not definitive.
"""

def create_pdf_report(pdf_path, plot_image_path, interpretation):
    c = canvas.Canvas(pdf_path, pagesize=letter)
    width, height = letter

    # Title
    c.setFont("Helvetica-Bold", 16)
    c.drawString(72, height - 72, "Coverage Report: ANC4 and SBA (2018-2022)")

    # Insert plot image
    img = ImageReader(plot_image_path)
    img_width = 400
    img_height = 250
    c.drawImage(img, 72, height - 72 - img_height - 30, width=img_width, height=img_height)

    # Add interpretation text below image with wrapping
    c.setFont("Helvetica", 11)
    text_object = c.beginText(72, height - 72 - img_height - 80)
    wrapped_text = textwrap.wrap(interpretation, width=90)
    for line in wrapped_text:
        text_object.textLine(line)
    c.drawText(text_object)

    c.save()

create_pdf_report(pdf_path, plot_image_path, interpretation)
print(f"PDF report created at: {pdf_path}")
