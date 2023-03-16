import json
import pandas as pd

from cowidev import PATHS
from cowidev.cases_deaths.params import API


URL = "https://covid19.who.int/WHO-COVID-19-global-data.csv"


def load_data(server_mode):
    """Load WHO data"""
    # Load data
    try:
        df = pd.read_csv(URL)
    except Exception:
        if server_mode:
            API.send_error(
                channel="#corona-data-updates",
                title="Cases/Deaths: File not found in source!",
                message="Could not load data from WHO!",
            )
        raise ValueError("Could not load data from WHO.")
    # Process data
    df = process_data(df, API, server_mode)
    return df


def process_data(df: pd.DataFrame, API, server_mode):
    # Clean column names, column and row ordering, etc.
    df = format_table(df)
    # Remove zero-values
    # df = df[(df["total_cases"] > 0) | (df["total_deaths"] > 0)]
    # Harmonize country names
    df = harmonize_country_names(df, API, server_mode)
    # Handle country-specific issues
    df = handle_country_issues(df)
    return df


def format_table(df: pd.DataFrame) -> pd.DataFrame:
    """Rename columns, sort columns and rows, etc."""
    column_renaming = {
        "Country": "location",
        "Date_reported": "date",
        "New_cases": "new_cases",
        "Cumulative_cases": "total_cases",
        "New_deaths": "new_deaths",
        "Cumulative_deaths": "total_deaths",
    }
    # Rename columns
    df = df.rename(columns=column_renaming)
    # Sort columns and rows
    df = df[column_renaming.values()].sort_values(["location", "date"])
    return df


def harmonize_country_names(df: pd.DataFrame, api, server_mode) -> pd.DataFrame:
    """Harmonize country names with OWID's standard names."""
    # Load country name mapping
    with open(PATHS.INTERNAL_INPUT_WHO_CASES_DEATHS_COUNTRY_STD_FILE, "r") as f:
        dix = json.load(f)
    # Check missing / unexpected countries
    countries_received = set(df["location"])
    countries_expected = set(dix.keys())
    if countries_missing := countries_expected - countries_received:
        if server_mode:
            api.send_error(
                channel="#corona-data-updates",
                title="Cases/Deaths: Missing countries!",
                message=f"There were missing countries in source: {countries_missing}",
            )
        raise ValueError(f"Missing countries: {countries_missing}")
    if countries_unexpected := countries_received - countries_expected:
        if server_mode:
            api.send_error(
                channel="#corona-data-updates",
                title="Cases/Deaths: Unexpected countries!",
                message=f"There were unexpected countries in source: {countries_unexpected}",
            )
        raise ValueError(f"Unexpected countries: {countries_unexpected}")
    # Harmonize country names
    df["location"] = df["location"].map(dix)
    assert not df["location"].isnull().any(), "There are still missing countries!"
    return df


def handle_country_issues(df: pd.DataFrame) -> pd.DataFrame:
    """Handles some country-specific issues.

    Example: "Bonaire, Sint Eustatius and Saba" does not come as a country, but as its individual entities.
    """
    # Remove 'Others'
    df = df[~df["location"].isin(["Other", "Others"])]
    # Estimate "Bonaire Sint Eustatius and Saba" as the sum of its individual entities
    countries = ["Sint Eustatius", "Bonaire", "Saba"]
    df.loc[df["location"].isin(countries), "location"] = "Bonaire Sint Eustatius and Saba"
    df = df.groupby(["location", "date"], as_index=False).sum()
    return df
