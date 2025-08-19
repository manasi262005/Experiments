import os
import pandas as pd
import matplotlib.pyplot as plt

# -------- SETTINGS --------
DATA_PATH = os.path.join("data", "patients.csv")
OUT_CLEAN = os.path.join("outputs", "clean")
OUT_FIGS = os.path.join("outputs", "figures")
OUT_METRICS = os.path.join("outputs", "metrics")

os.makedirs(OUT_CLEAN, exist_ok=True)
os.makedirs(OUT_FIGS, exist_ok=True)
os.makedirs(OUT_METRICS, exist_ok=True)

# -------- 1) LOAD --------
print("Loading dataset...")
df = pd.read_csv(DATA_PATH)

print("Rows, Cols:", df.shape)
print("Columns:", list(df.columns))

# -------- 2) CLEANING & ENRICHMENT --------
print("Cleaning & enriching...")

df.columns = [c.strip() for c in df.columns]

# Convert dates
if "Date of Admission" in df.columns:
    df["Date of Admission"] = pd.to_datetime(df["Date of Admission"], errors="coerce")

# Convert Billing
if "Billing Amount" in df.columns:
    df["Billing Amount"] = (
        df["Billing Amount"]
        .astype(str)
        .str.replace(r"[^0-9.\-]", "", regex=True)
    )
    df["Billing Amount"] = pd.to_numeric(df["Billing Amount"], errors="coerce")

# Convert Age
if "Age" in df.columns:
    df["Age"] = pd.to_numeric(df["Age"], errors="coerce")

# Normalize Gender
if "Gender" in df.columns:
    df["Gender"] = df["Gender"].astype(str).str.strip().str.title()
    df["Gender"] = df["Gender"].replace({"M": "Male", "F": "Female"})

# Clean text cols
for col in ["Name","Blood Type","Medical Condition","Doctor","Hospital","Insurance Provider"]:
    if col in df.columns:
        df[col] = df[col].astype(str).str.strip()

df = df.drop_duplicates()

# Fill missing values
if "Billing Amount" in df.columns and df["Billing Amount"].isna().any():
    df["Billing Amount"] = df["Billing Amount"].fillna(df["Billing Amount"].median())
if "Gender" in df.columns:
    df["Gender"] = df["Gender"].fillna("Unknown")
if "Insurance Provider" in df.columns:
    df["Insurance Provider"] = df["Insurance Provider"].fillna("Unknown")
if "Blood Type" in df.columns:
    df["Blood Type"] = df["Blood Type"].fillna("Unknown")

# Derived cols
if "Age" in df.columns:
    bins = [0, 18, 40, 60, 200]
    labels = ["Child (0-18)","Adult (19-40)","Middle (41-60)","Senior (61+)"]
    df["Age Group"] = pd.cut(df["Age"], bins=bins, labels=labels, right=True, include_lowest=True)

df["Admission Year"] = df["Date of Admission"].dt.year
df["Admission Month"] = df["Date of Admission"].dt.to_period("M").astype(str)
df["Month Name"] = df["Date of Admission"].dt.strftime("%b")

# Save cleaned dataset
clean_path = os.path.join(OUT_CLEAN, "patients_clean.csv")
df.to_csv(clean_path, index=False)
print(f"Saved cleaned data → {clean_path}")

# -------- 3) METRICS --------
print("Computing metrics...")

kpi = pd.DataFrame({
    "Total Patients": [len(df)],
    "Total Billing": [df["Billing Amount"].sum()],
    "Average Billing": [df["Billing Amount"].mean()]
})
kpi.to_csv(os.path.join(OUT_METRICS, "kpis.csv"), index=False)

if "Medical Condition" in df.columns:
    cond_counts = df["Medical Condition"].value_counts().reset_index()
    cond_counts.columns = ["Medical Condition", "Patients"]
    cond_counts.to_csv(os.path.join(OUT_METRICS, "medical_condition_counts.csv"), index=False)

monthly = (
    df.dropna(subset=["Date of Admission"])
      .groupby("Admission Month")
      .size()
      .reset_index(name="Admissions")
      .sort_values("Admission Month")
)
monthly.to_csv(os.path.join(OUT_METRICS, "admissions_by_month.csv"), index=False)

if "Medical Condition" in df.columns:
    avg_bill_cond = (
        df.groupby("Medical Condition")["Billing Amount"]
          .mean()
          .sort_values(ascending=False)
          .reset_index()
    )
    avg_bill_cond.to_csv(os.path.join(OUT_METRICS, "avg_billing_by_condition.csv"), index=False)

# --- NEW: Blood Type metrics ---
if "Blood Type" in df.columns:
    blood_counts = df["Blood Type"].value_counts().reset_index()
    blood_counts.columns = ["Blood Type", "Patients"]
    blood_counts.to_csv(os.path.join(OUT_METRICS, "blood_type_counts.csv"), index=False)

    avg_bill_blood = (
        df.groupby("Blood Type")["Billing Amount"]
          .mean()
          .sort_values(ascending=False)
          .reset_index()
    )
    avg_bill_blood.to_csv(os.path.join(OUT_METRICS, "avg_billing_by_bloodtype.csv"), index=False)

# -------- 4) VISUALS --------
print("Creating charts...")

def save_bar(series_or_df, x, y=None, title="", path="figure.png", rotate=False):
    plt.figure(figsize=(10,5))
    if y:
        plt.bar(series_or_df[x], series_or_df[y])
    else:
        series_or_df.plot(kind="bar")
    plt.title(title)
    if rotate:
        plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

def save_pie(labels, sizes, title, path):
    plt.figure(figsize=(6,6))
    plt.pie(sizes, labels=labels, autopct="%1.1f%%")
    plt.title(title)
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

def save_line(df_line, x, y, title, path):
    plt.figure(figsize=(10,5))
    plt.plot(df_line[x], df_line[y], marker="o")
    plt.title(title)
    plt.xticks(rotation=45, ha="right")
    plt.tight_layout()
    plt.savefig(path, dpi=150)
    plt.close()

# Charts
if not monthly.empty:
    save_line(monthly, "Admission Month", "Admissions",
              "Admissions Over Time (Monthly)",
              os.path.join(OUT_FIGS, "admissions_over_time.png"))

if "Medical Condition" in df.columns:
    top10 = df["Medical Condition"].value_counts().head(10)
    save_bar(top10, x=None, y=None,
             title="Top 10 Medical Conditions",
             path=os.path.join(OUT_FIGS, "top10_medical_conditions.png"),
             rotate=True)

if "Gender" in df.columns:
    g = df["Gender"].value_counts()
    save_pie(g.index.tolist(), g.values.tolist(),
             "Gender Distribution",
             os.path.join(OUT_FIGS, "gender_distribution.png"))

if "Age Group" in df.columns:
    ag = df["Age Group"].value_counts().sort_index()
    save_pie([str(x) for x in ag.index.tolist()], ag.values.tolist(),
             "Age Group Distribution",
             os.path.join(OUT_FIGS, "age_group_distribution.png"))

if "Medical Condition" in df.columns:
    top_bill = (
        df.groupby("Medical Condition")["Billing Amount"]
          .mean()
          .sort_values(ascending=False)
          .head(10)
    )
    save_bar(top_bill, x=None, y=None,
             title="Average Billing by Condition (Top 10)",
             path=os.path.join(OUT_FIGS, "avg_billing_by_condition.png"),
             rotate=True)

if "Insurance Provider" in df.columns:
    ins = df["Insurance Provider"].value_counts().head(10)
    save_pie(ins.index.tolist(), ins.values.tolist(),
             "Insurance Provider Share (Top 10)",
             os.path.join(OUT_FIGS, "insurance_provider_share.png"))

# --- NEW: Blood Type charts ---
if "Blood Type" in df.columns:
    bt = df["Blood Type"].value_counts()
    save_pie(bt.index.tolist(), bt.values.tolist(),
             "Blood Type Distribution",
             os.path.join(OUT_FIGS, "blood_type_distribution.png"))

    bt_avg = (
        df.groupby("Blood Type")["Billing Amount"]
          .mean()
          .sort_values(ascending=False)
    )
    save_bar(bt_avg, x=None, y=None,
             title="Average Billing by Blood Type",
             path=os.path.join(OUT_FIGS, "avg_billing_by_bloodtype.png"),
             rotate=True)

print("All done ✅")
print(f"See outputs in: {OUT_CLEAN}, {OUT_METRICS}, {OUT_FIGS}")