"""
load_bigquery.py — Land the raw FACT tables in BigQuery as dbt sources.

This is the EL step (in production, Fivetran/Airbyte syncing Salesforce). It
loads only the two large fact tables — `fact_cases` and `fact_case_comments` —
as typed raw tables. The dimensions are dbt **seeds** (`dbt seed`), not loaded
here, because seeds are for small static reference data and facts are not.

After this runs:  cd dbt && dbt seed && dbt build   (builds staging + marts).

Config via env (with defaults):
    BQ_PROJECT   (default: $GOOGLE_CLOUD_PROJECT)
    BQ_DATASET   (default: ops_intel)
    BQ_LOCATION  (default: US)

Usage:
    gcloud auth application-default login
    BQ_PROJECT=my-project python load_bigquery.py
"""

import os
from pathlib import Path

import pandas as pd
from google.cloud import bigquery

PROJECT  = os.getenv("BQ_PROJECT") or os.getenv("GOOGLE_CLOUD_PROJECT")
DATASET  = os.getenv("BQ_DATASET", "ops_intel")
LOCATION = os.getenv("BQ_LOCATION", "US")
DATA     = Path(__file__).resolve().parent / "data"

# Explicit schemas so timestamps/dates/bools land correctly for Looker.
SF = bigquery.SchemaField
SCHEMAS = {
    "fact_cases": [
        SF("case_id", "STRING"), SF("case_number", "STRING"),
        SF("created_date", "TIMESTAMP"), SF("first_response_at", "TIMESTAMP"),
        SF("closed_date", "TIMESTAMP"), SF("status", "STRING"),
        SF("origin", "STRING"), SF("priority", "STRING"),
        SF("client_id", "STRING"), SF("contact_name", "STRING"),
        SF("owner_agent_id", "STRING"), SF("vendor_id", "STRING"),
        SF("product_line", "STRING"), SF("product_type", "STRING"),
        SF("case_type_id", "STRING"), SF("category", "STRING"),
        SF("category_tagged", "STRING"), SF("is_mistagged", "BOOL"),
        SF("subcategory", "STRING"), SF("subject", "STRING"),
        SF("description", "STRING"), SF("reason_code", "STRING"),
        SF("first_response_minutes", "FLOAT64"), SF("handle_time_minutes", "FLOAT64"),
        SF("resolution_time_hours", "FLOAT64"), SF("reopened_count", "INTEGER"),
        SF("escalated", "BOOL"), SF("sla_target_hours", "INTEGER"),
        SF("sla_met", "BOOL"), SF("is_first_contact_resolution", "BOOL"),
        SF("csat_score", "INTEGER"), SF("csat_comment", "STRING"),
        SF("resolution_summary", "STRING"), SF("kb_addressable", "BOOL"),
    ],
    "fact_case_comments": [
        SF("case_number", "STRING"), SF("seq", "INTEGER"),
        SF("author_type", "STRING"), SF("author", "STRING"),
        SF("created_at", "TIMESTAMP"), SF("body", "STRING"),
    ],
}


def main():
    if not PROJECT:
        raise SystemExit("Set BQ_PROJECT or GOOGLE_CLOUD_PROJECT.")
    client = bigquery.Client(project=PROJECT, location=LOCATION)
    ds_ref = bigquery.Dataset(f"{PROJECT}.{DATASET}")
    ds_ref.location = LOCATION
    client.create_dataset(ds_ref, exists_ok=True)
    print(f"→ dataset {PROJECT}.{DATASET} ({LOCATION})")

    for table, schema in SCHEMAS.items():
        df = pd.read_csv(DATA / f"{table}.csv")
        # Coerce blanks in nullable typed columns to NaN/NaT.
        for f in schema:
            if f.name not in df.columns:
                continue
            if f.field_type in ("TIMESTAMP", "DATE"):
                df[f.name] = pd.to_datetime(df[f.name], errors="coerce")
            elif f.field_type in ("INTEGER", "FLOAT64"):
                df[f.name] = pd.to_numeric(df[f.name], errors="coerce")
            elif f.field_type == "BOOL":
                df[f.name] = (df[f.name].astype(str).str.lower()
                              .map({"true": True, "false": False}))
        job = client.load_table_from_dataframe(
            df, f"{PROJECT}.{DATASET}.{table}",
            job_config=bigquery.LoadJobConfig(
                schema=schema, write_disposition="WRITE_TRUNCATE"),
        )
        job.result()
        print(f"  ✅ {table:<20} {len(df):>7,} rows")

    print(f"\nRaw facts loaded into {PROJECT}.{DATASET}. "
          f"Next:  cd dbt && dbt seed && dbt build")


if __name__ == "__main__":
    main()
