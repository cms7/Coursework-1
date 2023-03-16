import pandas as pd
import numpy as np

from cowidev.megafile.steps.test import get_testing
from cowidev.cases_deaths.params import (
    LARGE_DATA_CORRECTIONS,
    AGGREGATE_REGIONS_SPEC,
    DOUBLING_DAYS_SPEC,
    ROLLING_AVG_SPEC,
    DAYS_SINCE_SPEC,
)
from cowidev.cases_deaths.utils import load_population


# ================================================
# Main functions
# ================================================
def process_data(df):
    df = (
        df[["date", "location", "new_cases", "new_deaths", "total_cases", "total_deaths"]]
        .pipe(format_date)
        .pipe(discard_rows)
        .pipe(inject_owid_aggregates)
        .pipe(inject_weekly_growth)
        .pipe(inject_biweekly_growth)
        .pipe(inject_doubling_days)
        .pipe(
            inject_per_million,
            [
                "new_cases",
                "new_deaths",
                "total_cases",
                "total_deaths",
                "weekly_cases",
                "weekly_deaths",
                "biweekly_cases",
                "biweekly_deaths",
            ],
        )
        .pipe(inject_rolling_avg)
        .pipe(inject_cfr)
        .pipe(inject_days_since)
        .pipe(inject_exemplars)
        .sort_values(by=["location", "date"])
    )
    return df


# ================================================
# Discard rows
# ================================================


def format_date(df: pd.DataFrame) -> pd.DataFrame:
    print("Formatting date…")
    df["date"] = pd.to_datetime(df["date"], format="%Y-%m-%d")
    return df


# ================================================
# Discard rows
# ================================================
def discard_rows(df):
    print("Discarding rows…")
    # For all rows where new_cases or new_deaths is negative, we keep the cumulative value but set
    # the daily change to NA. This also sets the 7-day rolling average to NA for the next 7 days.
    df.loc[df.new_cases < 0, "new_cases"] = np.nan
    df.loc[df.new_deaths < 0, "new_deaths"] = np.nan

    # Custom data corrections
    for ldc in LARGE_DATA_CORRECTIONS:
        df.loc[(df.location == ldc[0]) & (df.date.astype(str) == ldc[1]), f"new_{ldc[2]}"] = np.nan

    # If the last known value is above 1000 cases or 100 deaths but the latest reported value is 0
    # then set that value to NA in case it's a temporary reporting error. (Up to 7 days in the past)
    df = df.sort_values(["location", "date"]).groupby("location").apply(hide_recent_zeros)

    return df


def hide_recent_zeros(df: pd.DataFrame) -> pd.DataFrame:
    last_reported_date = df.date.max()

    last_positive_cases_date = df.loc[df.new_cases > 0, "date"].max()
    if pd.isnull(last_positive_cases_date):
        return df
    if last_positive_cases_date != last_reported_date:
        last_known_cases = df.loc[df.date == last_positive_cases_date, "new_cases"].item()
        if last_known_cases >= 100 and (last_reported_date - last_positive_cases_date).days < 7:
            df.loc[df.date > last_positive_cases_date, "new_cases"] = np.nan

    last_positive_deaths_date = df.loc[df.new_deaths > 0, "date"].max()
    if pd.isnull(last_positive_deaths_date):
        return df
    if last_positive_deaths_date != last_reported_date:
        last_known_deaths = df.loc[df.date == last_positive_deaths_date, "new_deaths"].item()
        if last_known_deaths >= 10 and (last_reported_date - last_positive_deaths_date).days < 7:
            df.loc[df.date > last_positive_deaths_date, "new_deaths"] = np.nan

    return df


# ================================================
# OWID aggregates
# ================================================
def inject_owid_aggregates(df):
    print("Adding aggregates…")

    def _sum_aggregate(df, name, include=None, exclude=None):
        df = df.copy()
        if include:
            df = df[df["location"].isin(include)]
        if exclude:
            df = df[~df["location"].isin(exclude)]
        df = df.groupby("date").sum().reset_index()
        df["location"] = name
        return df

    return pd.concat(
        [
            df,
            *[_sum_aggregate(df, name, **params) for name, params in AGGREGATE_REGIONS_SPEC.items()],
        ],
        sort=True,
        ignore_index=True,
    )


# ====================================
# Weekly & biweekly growth calculation
# ====================================


def inject_weekly_growth(df):
    print("Adding weekly growth…")
    return _inject_growth(df, "weekly", 7)


def inject_biweekly_growth(df):
    print("Adding biweekly growth…")
    return _inject_growth(df, "biweekly", 14)


def _inject_growth(df, prefix, periods):
    cases_colname = "%s_cases" % prefix
    deaths_colname = "%s_deaths" % prefix
    cases_growth_colname = "%s_pct_growth_cases" % prefix
    deaths_growth_colname = "%s_pct_growth_deaths" % prefix

    df[[cases_colname, deaths_colname]] = (
        df[["location", "new_cases", "new_deaths"]]
        .groupby("location")[["new_cases", "new_deaths"]]
        .rolling(window=periods, min_periods=periods - 1, center=False)
        .sum()
        .reset_index(level=0, drop=True)
    )
    df[[cases_growth_colname, deaths_growth_colname]] = (
        df[["location", cases_colname, deaths_colname]]
        .groupby("location")[[cases_colname, deaths_colname]]
        .pct_change(periods=periods, fill_method=None)
        .round(3)
        .replace([np.inf, -np.inf], pd.NA)
        * 100
    )

    df.loc[df.new_cases.isnull(), cases_colname] = np.nan
    df.loc[df.new_deaths.isnull(), deaths_colname] = np.nan

    return df


# ================================================
# Doubling days calculation
# ================================================


def inject_doubling_days(df):
    print("Adding doubling days…")
    for col, spec in DOUBLING_DAYS_SPEC.items():
        value_col = spec["value_col"]
        periods = spec["periods"]
        df.loc[df[value_col] == 0, value_col] = np.nan
        df[col] = (
            df.groupby("location", as_index=False)[value_col]
            .pct_change(periods=periods, fill_method=None)[value_col]
            .map(lambda pct: pct_change_to_doubling_days(pct, periods))
        )
    return df


def pct_change_to_doubling_days(pct_change, periods):
    if pd.notnull(pct_change) and pct_change != 0:
        doubling_days = periods * np.log(2) / np.log(1 + pct_change)
        return np.round(doubling_days, decimals=2)
    return pd.NA


# ================================================
# Per-capita metrics
# ================================================


def inject_per_million(df, measures):
    print("Adding per-capita metrics…")
    df = inject_population(df)
    # Fix population value for France (Should not include overseas territories for the WHO)
    df.loc[df.location == "France", "population"] = 64626624
    for measure in measures:
        pop_measure = measure + "_per_million"
        series = df[measure] / (df["population"] / 1e6)
        df[pop_measure] = series.round(decimals=3)
    df = drop_population(df)
    return df


# Useful for adding it to regions.csv and
def inject_population(df):
    return df.merge(load_population(), how="left", on="location")


def drop_population(df):
    return df.drop(columns=["population_year", "population"])


# ================================================
# Rolling averages
# ================================================


def inject_rolling_avg(df):
    print("Adding rolling-average metrics…")
    df = df.copy().sort_values(by="date")
    for col, spec in ROLLING_AVG_SPEC.items():
        df[col] = df[spec["col"]].astype("float")
        df[col] = (
            df.groupby("location")[col]
            .rolling(
                window=spec["window"],
                min_periods=spec["min_periods"],
                center=spec["center"],
            )
            .mean()
            .round(decimals=3)
            .reset_index(level=0, drop=True)
        )
    return df


# ================================================
# Case Fatality Ratio
# ================================================


def inject_cfr(df):
    print("Adding case-fatality-rate metrics…")

    def _apply_row_cfr_100(row):
        if pd.notnull(row["total_cases"]) and row["total_cases"] >= 100:
            return row["cfr"]
        return pd.NA

    cfr_series = (df["total_deaths"] / df["total_cases"]) * 100
    df["cfr"] = cfr_series.round(decimals=3)
    df["cfr_100_cases"] = df.apply(_apply_row_cfr_100, axis=1)
    return df


# ================================================
# 'Days since' variables
# ================================================


def inject_days_since(df):
    print("Adding days-since metrics…")

    def _days_since(df, spec):
        def _get_date_of_threshold(df, col, threshold):
            try:
                return df["date"][df[col] >= threshold].iloc[0]
            except Exception:
                return None

        def _date_diff(a, b, positive_only=False):
            if pd.isnull(a) or pd.isnull(b):
                return None
            diff = (a - b).days
            if positive_only and diff < 0:
                return None
            return diff

        ref_date = pd.to_datetime(_get_date_of_threshold(df, spec["value_col"], spec["value_threshold"]))
        return (
            pd.to_datetime(df["date"])
            .map(lambda date: _date_diff(date, ref_date, spec["positive_only"]))
            .astype("Int64")
        )

    df = df.copy()
    for col, spec in DAYS_SINCE_SPEC.items():
        df[col] = (
            df[["date", "location", spec["value_col"]]]
            .groupby("location")
            .apply(lambda df_group: _days_since(df_group, spec))
            .reset_index(level=0, drop=True)
        )
    return df


# ================================================
# Variables to find exemplars
# ================================================


def inject_exemplars(df):
    print("Adding exemplars metrics…")
    df = inject_population(df)

    # Inject days since 100th case IF population ≥ 5M
    def mapper_days_since(row):
        if pd.notnull(row["population"]) and row["population"] >= 5e6:
            return row["days_since_100_total_cases"]
        return pd.NA

    df["days_since_100_total_cases_and_5m_pop"] = df.apply(mapper_days_since, axis=1)

    # Inject boolean when all exenplar conditions hold
    # Use int because the Grapher doesn't handle non-ints very well
    countries_with_testing_data = set(get_testing()["location"])

    def mapper_bool(row):
        if (
            pd.notnull(row["days_since_100_total_cases"])
            and pd.notnull(row["population"])
            and row["days_since_100_total_cases"] >= 21
            and row["population"] >= 5e6
            and row["location"] in countries_with_testing_data
        ):
            return 1
        return 0

    df["5m_pop_and_21_days_since_100_cases_and_testing"] = df.apply(mapper_bool, axis=1)

    return drop_population(df)
