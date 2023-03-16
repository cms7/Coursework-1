import pandas as pd

from cowidev import PATHS


########################################################################################
# Functions to load population data
########################################################################################


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


def _find_closest_year_row(df, year=2021):
    """Returns the row which is closest to the year specified (in either direction)"""
    df = df.copy()
    df["year"] = df["year"].sort_values(ascending=True)
    return df.loc[df["year"].map(lambda x: abs(x - year)).idxmin()]


########################################################################################
# Functions to load region data
########################################################################################


def load_eu_country_names():
    """Load list with EU country names."""
    df = pd.read_csv(
        PATHS.INTERNAL_INPUT_OWID_EU_FILE,
        keep_default_na=False,
        header=0,
        names=["location", "eu"],
        usecols=["location"],
    )
    return df["location"].tolist()


def load_owid_continents():
    """Load table with OWID continent names."""
    return pd.read_csv(
        PATHS.INTERNAL_INPUT_OWID_CONT_FILE,
        keep_default_na=False,
        header=0,
        names=["location", "code", "year", "continent"],
        usecols=["location", "continent"],
    )


def load_wb_income_groups():
    """Load table with World Bank income group names."""
    return pd.read_csv(
        PATHS.INTERNAL_INPUT_WB_INCOME_FILE,
        keep_default_na=False,
        header=0,
        names=["location", "code", "income_group", "year"],
        usecols=["location", "income_group"],
    )
