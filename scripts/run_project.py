import pandas as pd
import os
from user_profile import RAW_DATA_DIR, OUTPUTS_DIR

# === Load UNICEF data ===
anc4_path = os.path.join(RAW_DATA_DIR, "fusion_GLOBAL_DATAFLOW_UNICEF_1.0_.MNCH_ANC4..CSV")
sba_path = os.path.join(RAW_DATA_DIR, "fusion_GLOBAL_DATAFLOW_UNICEF_1.0_.MNCH_SAB..CSV")
classification_path = os.path.join(RAW_DATA_DIR, "On-track and off-track countries.xlsx")
pop_path = os.path.join(RAW_DATA_DIR, "WPP2022_GEN_F01_DEMOGRAPHIC_INDICATORS_COMPACT_REV1.xlsx")

# Load ANC4 & SBA
anc4_df = pd.read_csv(anc4_path)
sba_df = pd.read_csv(sba_path)

# Filter to 2018–2022, take latest year per country
anc4_filtered = anc4_df[anc4_df['Year'].between(2018, 2022)]
sba_filtered = sba_df[sba_df['Year'].between(2018, 2022)]

anc4_latest = anc4_filtered.sort_values('Year').groupby('Country', as_index=False).last()
sba_latest = sba_filtered.sort_values('Year').groupby('Country', as_index=False).last()

# Load population data for 2022 (Projected births)
pop_df = pd.read_excel(pop_path, sheet_name='Estimates')
pop_2022 = pop_df[pop_df['Time'] == 2022][['Location', 'Births']]

# Load classification of on-track / off-track
status_df = pd.read_excel(classification_path)
status_df = status_df[['Country', 'Status.U5MR']]

# Clean status
status_df['Track'] = status_df['Status.U5MR'].map({
    'on-track': 'On Track',
    'achieved': 'On Track',
    'acceleration needed': 'Off Track'
})

# === Merge all datasets ===
merged = (
    anc4_latest
    .merge(sba_latest[['Country', 'Value']], on='Country', suffixes=('_ANC4', '_SBA'))
    .merge(status_df[['Country', 'Track']], on='Country')
    .merge(pop_2022, left_on='Country', right_on='Location')
)

# === Compute Population-Weighted Averages ===
def weighted_average(df, value_column, weight_column='Births'):
    return (df[value_column] * df[weight_column]).sum() / df[weight_column].sum()

results = []

for group in ['On Track', 'Off Track']:
    subset = merged[merged['Track'] == group]
    anc4_avg = weighted_average(subset, 'Value_ANC4')
    sba_avg = weighted_average(subset, 'Value_SBA')
    results.append({'Group': group, 'ANC4': anc4_avg, 'SBA': sba_avg})

results_df = pd.DataFrame(results)

# === Save output ===
results_df.to_csv(os.path.join(OUTPUTS_DIR, 'coverage_results.csv'), index=False)
print("✅ Analysis complete. Results saved in outputs/coverage_results.csv")
