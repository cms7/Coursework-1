from datetime import datetime

from cowidev.cases_deaths.utils import load_eu_country_names, load_owid_continents, load_wb_income_groups
from cowidev.utils.slackapi import SlackAPI


DATASET_NAME = "COVID-19 Cases and deaths - WHO"


########################################################################################
# Slack
########################################################################################
API = SlackAPI()


########################################################################################
# ZERO day (Grapher)
########################################################################################


ZERO_DAY = "2020-01-21"
zero_day = datetime.strptime(ZERO_DAY, "%Y-%m-%d")


########################################################################################
# Functions to load region data
########################################################################################

LOCATIONS_BY_CONTINENT = load_owid_continents().groupby("continent")["location"].apply(list).to_dict()
LOCATIONS_BY_WB_INCOME_GROUP = load_wb_income_groups().groupby("income_group")["location"].apply(list).to_dict()


########################################################################################
# Specs on various regions
########################################################################################
AGGREGATE_REGIONS_SPEC = {
    # World
    "World": {"include": None, "exclude": None},
    "World excl. China": {"exclude": ["China"]},
    "World excl. China and South Korea": {"exclude": ["China", "South Korea"]},
    "World excl. China, South Korea, Japan and Singapore": {"exclude": ["China", "South Korea", "Japan", "Singapore"]},
    # European Union
    "European Union": {"include": load_eu_country_names()},
    # OWID continents
    **{continent: {"include": locations, "exclude": None} for continent, locations in LOCATIONS_BY_CONTINENT.items()},
    "Asia excl. China": {"include": list(set(LOCATIONS_BY_CONTINENT["Asia"]) - set(["China"]))},
    # World Bank income groups
    **{
        income_group: {"include": locations, "exclude": None}
        for income_group, locations in LOCATIONS_BY_WB_INCOME_GROUP.items()
    },
}


########################################################################################
# Data corrections
########################################################################################
# add here country-dates where data should be set to NaN
LARGE_DATA_CORRECTIONS = [
    # ("Australia", "2022-04-01", "deaths"),
    # ("Austria", "2022-04-21", "deaths"),
    # ("Austria", "2022-04-22", "deaths"),
    # ("Brazil", "2021-09-18", "cases"),
    # ("Chile", "2020-07-17", "deaths"),
    # ("Chile", "2022-03-21", "deaths"),
    # ("China", "2020-04-17", "deaths"),
    # ("Denmark", "2021-12-21", "deaths"),
    # ("Ecuador", "2020-09-07", "deaths"),
    # ("Ecuador", "2021-07-20", "deaths"),
    # ("Finland", "2022-03-07", "deaths"),
    # ("Iceland", "2022-05-17", "deaths"),
    # ("India", "2021-06-10", "deaths"),
    # ("Mexico", "2020-10-05", "deaths"),
    # ("Mexico", "2021-06-01", "deaths"),
    # ("Moldova", "2021-12-31", "deaths"),
    # ("Norway", "2022-03-17", "deaths"),
    # ("Oman", "2022-06-16", "deaths"),
    # ("Peru", "2022-12-26", "cases"),
    # ("South Africa", "2021-11-23", "cases"),
    # ("South Africa", "2022-01-06", "deaths"),
    # ("Spain", "2020-06-19", "deaths"),
    # ("Turkey", "2020-12-10", "cases"),
    # ("United Kingdom", "2022-01-31", "cases"),
    # ("United Kingdom", "2022-02-01", "deaths"),
    # ("United Kingdom", "2022-04-06", "deaths"),
    # ("United Kingdom", "2022-08-22", "deaths"),
    # ("United Kingdom", "2023-01-05", "deaths"),
    # ("Vietnam", "2022-08-04", "cases"),
    # ("Vietnam", "2022-08-06", "cases"),
]


########################################################################################
# Doubling days
########################################################################################

DOUBLING_DAYS_SPEC = {
    "doubling_days_total_cases_3_day_period": {
        "value_col": "total_cases",
        "periods": 3,
    },
    "doubling_days_total_cases_7_day_period": {
        "value_col": "total_cases",
        "periods": 7,
    },
    "doubling_days_total_deaths_3_day_period": {
        "value_col": "total_deaths",
        "periods": 3,
    },
    "doubling_days_total_deaths_7_day_period": {
        "value_col": "total_deaths",
        "periods": 7,
    },
}


########################################################################################
# Rolling averages
########################################################################################

ROLLING_AVG_SPEC = {
    "new_cases_7_day_avg_right": {
        "col": "new_cases",
        "window": 7,
        "min_periods": 6,
        "center": False,
    },
    "new_deaths_7_day_avg_right": {
        "col": "new_deaths",
        "window": 7,
        "min_periods": 6,
        "center": False,
    },
    "new_cases_per_million_7_day_avg_right": {
        "col": "new_cases_per_million",
        "window": 7,
        "min_periods": 6,
        "center": False,
    },
    "new_deaths_per_million_7_day_avg_right": {
        "col": "new_deaths_per_million",
        "window": 7,
        "min_periods": 6,
        "center": False,
    },
}


########################################################################################
# Days since
########################################################################################

DAYS_SINCE_SPEC = {
    "days_since_100_total_cases": {
        "value_col": "total_cases",
        "value_threshold": 100,
        "positive_only": False,
    },
    "days_since_5_total_deaths": {
        "value_col": "total_deaths",
        "value_threshold": 5,
        "positive_only": False,
    },
    "days_since_1_total_cases_per_million": {
        "value_col": "total_cases_per_million",
        "value_threshold": 1,
        "positive_only": False,
    },
    "days_since_0_1_total_deaths_per_million": {
        "value_col": "total_deaths_per_million",
        "value_threshold": 0.1,
        "positive_only": False,
    },
}


########################################################################################
# Metric names
########################################################################################
KEYS = ["date", "location"]
METRICS_BASE = [
    "new_cases",
    "new_deaths",
    "total_cases",
    "total_deaths",
    "weekly_cases",
    "weekly_deaths",
    "biweekly_cases",
    "biweekly_deaths",
]
METRICS_PER_MILLION = ["%s_per_million" % m for m in METRICS_BASE]
METRICS_DAYS_SINCE = list(DAYS_SINCE_SPEC.keys())
# Should keep these append-only in case someone external depends on the order
COLUMNS_BASE = [*KEYS, *METRICS_BASE]


########################################################################################
# Grapher
########################################################################################
GRAPHER_COL_NAMES = {
    "location": "Country",
    "date": "Year",
    # Absolute values
    "new_cases": "Daily new confirmed cases of COVID-19",
    "new_deaths": "Daily new confirmed deaths due to COVID-19",
    "total_cases": "Total confirmed cases of COVID-19",
    "total_deaths": "Total confirmed deaths due to COVID-19",
    # Per million
    "new_cases_per_million": "Daily new confirmed cases of COVID-19 per million people",
    "new_deaths_per_million": "Daily new confirmed deaths due to COVID-19 per million people",
    "total_cases_per_million": "Total confirmed cases of COVID-19 per million people",
    "total_deaths_per_million": "Total confirmed deaths due to COVID-19 per million people",
    # Days since
    "days_since_100_total_cases": "Days since the total confirmed cases of COVID-19 reached 100",
    "days_since_5_total_deaths": "Days since the total confirmed deaths of COVID-19 reached 5",
    "days_since_1_total_cases_per_million": (
        "Days since the total confirmed cases of COVID-19 per million people reached 1"
    ),
    "days_since_0_1_total_deaths_per_million": (
        "Days since the total confirmed deaths of COVID-19 per million people reached 0.1"
    ),
    # Rolling averages
    "new_cases_7_day_avg_right": "Daily new confirmed cases due to COVID-19 (rolling 7-day average, right-aligned)",
    "new_deaths_7_day_avg_right": "Daily new confirmed deaths due to COVID-19 (rolling 7-day average, right-aligned)",
    # Rolling averages - per million
    "new_cases_per_million_7_day_avg_right": (
        "Daily new confirmed cases of COVID-19 per million people (rolling 7-day average, right-aligned)"
    ),
    "new_deaths_per_million_7_day_avg_right": (
        "Daily new confirmed deaths due to COVID-19 per million people (rolling 7-day average, right-aligned)"
    ),
    # Case fatality ratio
    "cfr": "Case fatality rate of COVID-19 (%)",
    "cfr_100_cases": "Case fatality rate of COVID-19 (%) (Only observations with ≥100 cases)",
    # Exemplars variables
    "days_since_100_total_cases_and_5m_pop": (
        "Days since the total confirmed cases of COVID-19 reached 100 (with population ≥ 5M)"
    ),
    "5m_pop_and_21_days_since_100_cases_and_testing": (
        "Has population ≥ 5M AND had ≥100 cases ≥21 days ago AND has testing data"
    ),
    # Weekly aggregates
    "weekly_cases": "Weekly cases",
    "weekly_deaths": "Weekly deaths",
    "weekly_pct_growth_cases": "Weekly case growth (%)",
    "weekly_pct_growth_deaths": "Weekly death growth (%)",
    # Biweekly aggregates
    "biweekly_cases": "Biweekly cases",
    "biweekly_deaths": "Biweekly deaths",
    "biweekly_pct_growth_cases": "Biweekly case growth (%)",
    "biweekly_pct_growth_deaths": "Biweekly death growth (%)",
    # Weekly aggregates per capita
    "weekly_cases_per_million": "Weekly cases per million people",
    "weekly_deaths_per_million": "Weekly deaths per million people",
    # Biweekly aggregates per capita
    "biweekly_cases_per_million": "Biweekly cases per million people",
    "biweekly_deaths_per_million": "Biweekly deaths per million people",
}
