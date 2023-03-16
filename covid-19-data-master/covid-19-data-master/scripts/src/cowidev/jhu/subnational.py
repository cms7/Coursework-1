import pandas as pd
from cowidev.utils.s3 import obj_to_s3


def clean_global_subnational(metric):
    url = f"https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_{metric}_global.csv"
    metric = "cases" if metric == "confirmed" else "deaths"

    df = (
        pd.read_csv(url, na_values="")
        .drop(columns=["Lat", "Long"])
        .dropna(subset=["Province/State"])
        .melt(id_vars=["Country/Region", "Province/State"], var_name="date", value_name=f"total_{metric}")
        .rename(columns={"Country/Region": "location1", "Province/State": "location2"})
    )
    df["date"] = pd.to_datetime(df.date).dt.date.astype(str)
    df = df.sort_values(["location1", "location2", "date"])
    df[f"new_{metric}"] = df[f"total_{metric}"] - df.groupby(["location1", "location2"])[f"total_{metric}"].shift(1)
    df[f"new_{metric}_smoothed"] = (
        df.groupby(["location1", "location2"]).rolling(7)[f"new_{metric}"].mean().droplevel(level=[0, 1]).round(2)
    )
    df["location3"] = pd.NA
    return df


def clean_us_subnational(metric):
    url = f"https://raw.githubusercontent.com/CSSEGISandData/COVID-19/master/csse_covid_19_data/csse_covid_19_time_series/time_series_covid19_{metric}_US.csv"
    metric = "cases" if metric == "confirmed" else "deaths"

    df = (
        pd.read_csv(url)
        .drop(
            columns=[
                "UID",
                "iso2",
                "iso3",
                "code3",
                "FIPS",
                "Country_Region",
                "Lat",
                "Long_",
                "Combined_Key",
                "Population",
            ],
            errors="ignore",
        )
        .melt(id_vars=["Province_State", "Admin2"], var_name="date", value_name=f"total_{metric}")
        .rename(columns={"Province_State": "location2", "Admin2": "location3"})
    )
    df["date"] = pd.to_datetime(df.date).dt.date.astype(str)
    df = df.sort_values(["location2", "location3", "date"])
    df[f"new_{metric}"] = df[f"total_{metric}"] - df.groupby(["location2", "location3"])[f"total_{metric}"].shift(1)
    df[f"new_{metric}_smoothed"] = (
        df.groupby(["location2", "location3"]).rolling(7)[f"new_{metric}"].mean().droplevel(level=[0, 1]).round(2)
    )
    df["location1"] = "United States"
    return df


def create_subnational():
    global_cases = clean_global_subnational("confirmed")
    global_deaths = clean_global_subnational("deaths")
    us_cases = clean_us_subnational("confirmed")
    us_deaths = clean_us_subnational("deaths")

    df = pd.concat(
        [
            pd.merge(global_cases, global_deaths, on=["location1", "location2", "location3", "date"], how="outer"),
            pd.merge(us_cases, us_deaths, on=["location1", "location2", "location3", "date"], how="outer"),
        ]
    ).sort_values(["location1", "location2", "location3", "date"])[
        [
            "location1",
            "location2",
            "location3",
            "date",
            "total_cases",
            "new_cases",
            "new_cases_smoothed",
            "total_deaths",
            "new_deaths",
            "new_deaths_smoothed",
        ]
    ]
    df = df[df.total_cases > 0]
    filename = "subnational_cases_deaths"
    compression = {"method": "zip", "archive_name": f"{filename}.csv"}
    # df.to_csv(os.path.join(OUTPUT_PATH, f"{filename}.zip"), index=False, compression=compression)
    obj_to_s3(df, s3_path="s3://covid-19/public/jhu/{filename}.zip", compression=compression, public=True)
