import os
import sys

import pandas as pd

from cowidev import PATHS
from cowidev.jhu.utils import print_err


def load_data():
    """Load JHU data"""
    df_data = _load_raw_data()
    df_locs = _load_raw_locations()
    df = df_data.merge(df_locs, how="left", on=["Country/Region"])
    # Remove UK nations. To add these, we need to revisit how population is ingested (currently only UN nations are included)
    df = df[
        -df["Country/Region"].isin(
            [
                "Channel Islands",
                "Guernsey",
                "Jersey",
                "England",
                "Northern Ireland",
                "Scotland",
                "Wales",
            ]
        )
    ]
    return df


def load_population(year=2021):
    df = pd.read_csv(
        PATHS.INTERNAL_INPUT_UN_POPULATION_FILE,
        keep_default_na=False,
        usecols=["entity", "year", "population"],
    )
    return (
        pd.DataFrame([_find_closest_year_row(df_group, year) for loc, df_group in df.groupby("entity")])
        .dropna()
        .rename(columns={"entity": "location", "year": "population_year"})
    )


def load_owid_continents():
    return pd.read_csv(
        PATHS.INTERNAL_INPUT_OWID_CONT_FILE,
        keep_default_na=False,
        header=0,
        names=["location", "code", "year", "continent"],
        usecols=["location", "continent"],
    )


def load_wb_income_groups():
    return pd.read_csv(
        PATHS.INTERNAL_INPUT_WB_INCOME_FILE,
        keep_default_na=False,
        header=0,
        names=["location", "code", "income_group", "year"],
        usecols=["location", "income_group"],
    )


def load_eu_country_names():
    df = pd.read_csv(
        PATHS.INTERNAL_INPUT_OWID_EU_FILE,
        keep_default_na=False,
        header=0,
        names=["location", "eu"],
        usecols=["location"],
    )
    return df["location"].tolist()


def _find_closest_year_row(df, year=2021):
    """Returns the row which is closest to the year specified (in either direction)"""
    df = df.copy()
    df["year"] = df["year"].sort_values(ascending=True)
    return df.loc[df["year"].map(lambda x: abs(x - year)).idxmin()]


def _load_raw_data():
    """Load raw data"""
    # get cases
    global_cases = _get_metric("confirmed", "global")
    # get deaths
    global_deaths = _get_metric("deaths", "global")
    return pd.merge(global_cases, global_deaths, on=["date", "Country/Region"], how="outer")


def _load_raw_locations():
    """Load location data"""
    return pd.read_csv(PATHS.INTERNAL_INPUT_JHU_STD_FILE, keep_default_na=False).rename(
        columns={"Country": "Country/Region", "Our World In Data Name": "location"}
    )


def _get_metric(metric, region):
    """Read metric from raw JHU data files."""
    # Load file
    file_path = os.path.join(PATHS.INTERNAL_INPUT_JHU_DIR, f"time_series_covid19_{metric}_{region}.csv")
    df = pd.read_csv(file_path).drop(columns=["Lat", "Long"])

    # Get actual metric name
    if metric == "confirmed":
        metric = "total_cases"
    elif metric == "deaths":
        metric = "total_deaths"
    else:
        print_err("Unknown metric requested.\n")
        sys.exit(1)

    df = (
        df.pipe(_correct_regions)
        .pipe(_subregion_to_region)
        .melt(id_vars=["Country/Region"], var_name="date", value_name=metric)
        .pipe(_format_date)
        .pipe(_start_cutoff, metric)
        .pipe(_get_daily_metric, metric)
    )
    return df


def _correct_regions(df: pd.DataFrame):
    """Correct region names"""
    # Relabel as 'International'
    df.loc[df["Country/Region"].isin(["Diamond Princess", "MS Zaandam"]), "Country/Region"] = "International"
    # Exclude special entities
    df = df[-df["Country/Region"].isin(["Summer Olympics 2020", "Winter Olympics 2022", "Antarctica"])]
    return df


def _subregion_to_region(df: pd.DataFrame):
    """Subregions to regions"""
    subregion_to_region = [
        "Anguilla",
        "Aruba",
        "Bermuda",
        "Bonaire, Sint Eustatius and Saba",
        "British Virgin Islands",
        "Cayman Islands",
        "Channel Islands",
        "Cook Islands",
        "Curacao",
        "England",
        "Falkland Islands (Malvinas)",
        "Faroe Islands",
        "French Polynesia",
        "Gibraltar",
        "Greenland",
        "Guernsey",
        "Hong Kong",
        "Isle of Man",
        "Jersey",
        "Macau",
        "Montserrat",
        "Northern Ireland",
        "New Caledonia",
        "Saint Helena, Ascension and Tristan da Cunha",
        "Saint Pierre and Miquelon",
        "Scotland",
        "Turks and Caicos Islands",
        "Wallis and Futuna",
        "Wales",
    ]
    msk = df["Province/State"].isin(subregion_to_region)
    df_ = df.copy()
    df_.loc[msk, "Country/Region"] = df_.loc[msk, "Province/State"]
    return df_.drop(columns="Province/State").groupby("Country/Region", as_index=False).sum()


def _format_date(df: pd.DataFrame):
    """Format date"""
    df.loc[:, "date"] = pd.to_datetime(df["date"], format="%m/%d/%y").dt.date
    df = df.sort_values("date")
    return df


def _start_cutoff(df: pd.DataFrame, metric: str):
    """Only start country series when total_cases > 0 or total_deaths > 0 to minimize file size"""
    cutoff = (
        df.loc[df[metric] == 0, ["date", "Country/Region"]]
        .groupby("Country/Region", as_index=False)
        .max()
        .rename(columns={"date": "cutoff"})
    )
    df = df.merge(cutoff, on="Country/Region", how="left")
    df = df[(df.date >= df.cutoff) | (df.cutoff.isna())].drop(columns="cutoff")
    return df


def _get_daily_metric(df: pd.DataFrame, metric: str):
    """Get daily metric"""
    df.loc[:, metric.replace("total_", "new_")] = df[metric] - df.groupby("Country/Region")[metric].shift(1)
    return df


# Variables
LOCATIONS_BY_CONTINENT = load_owid_continents().groupby("continent")["location"].apply(list).to_dict()
LOCATIONS_BY_WB_INCOME_GROUP = load_wb_income_groups().groupby("income_group")["location"].apply(list).to_dict()
