import pandas as pd

METADATA = {
    "source_url": "https://health-infobase.canada.ca/src/data/covidLive/covid19-epiSummary-hospVentICU.csv",
    "source_url_ref": "https://health-infobase.canada.ca/covid-19/",
    "source_name": "Government of Canada",
    "entity": "Canada",
}


def main():
    df = (
        pd.read_csv(
            METADATA["source_url"],
            usecols=[
                "Date",
                "COVID_HOSP",
                "COVID_ICU",
            ],
        )
        .rename(columns={"Date": "date"})
        .melt("date", ["COVID_HOSP", "COVID_ICU"], "indicator")
        .replace(
            {
                "COVID_HOSP": "Daily hospital occupancy",
                "COVID_ICU": "Daily ICU occupancy",
            }
        )
        .assign(entity=METADATA["entity"])
    )

    return df, METADATA


if __name__ == "__main__":
    main()
