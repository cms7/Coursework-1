"""Get excess mortality dataset and publish it in public/data."""


from datetime import datetime, timedelta

import pandas as pd

from cowidev import PATHS
from cowidev.utils.utils import export_timestamp
from cowidev.utils.clean import clean_date

from owid import catalog


COLUMNS = [
    "location",
    "date",
    "p_scores_all_ages",
    "p_scores_15_64",
    "p_scores_65_74",
    "p_scores_75_84",
    "p_scores_85plus",
    "deaths_2020_all_ages",
    "average_deaths_2015_2019_all_ages",
    "deaths_2015_all_ages",
    "deaths_2016_all_ages",
    "deaths_2017_all_ages",
    "deaths_2018_all_ages",
    "deaths_2019_all_ages",
    "deaths_2010_all_ages",
    "deaths_2011_all_ages",
    "deaths_2012_all_ages",
    "deaths_2013_all_ages",
    "deaths_2014_all_ages",
    "deaths_2021_all_ages",
    "time",
    "time_unit",
    "p_scores_0_14",
    "projected_deaths_since_2020_all_ages",
    "excess_proj_all_ages",
    "cum_excess_proj_all_ages",
    "cum_proj_deaths_all_ages",
    "cum_p_proj_all_ages",
    "p_proj_all_ages",
    "p_proj_0_14",
    "p_proj_15_64",
    "p_proj_65_74",
    "p_proj_75_84",
    "p_proj_85p",
    "cum_excess_per_million_proj_all_ages",
    "excess_per_million_proj_all_ages",
    "deaths_2022_all_ages",
    "deaths_since_2020_all_ages",
]


class XMortalityETL:
    def extract(self):
        cat = catalog.RemoteCatalog(channels=["grapher"])
        t = cat.find_latest(namespace="excess_mortality", dataset="excess_mortality", table="excess_mortality")
        date_accessed = max(s.date_accessed for s in t.metadata.dataset.sources)
        return pd.DataFrame(t), date_accessed

    def pipeline(self, df: pd.DataFrame):
        # Rename columns
        df = df.rename(
            columns={
                "country": "location",
                "year": "date",
                "p_avg_all_ages": "p_scores_all_ages",
                "p_avg_0_14": "p_scores_0_14",
                "p_avg_15_64": "p_scores_15_64",
                "p_avg_65_74": "p_scores_65_74",
                "p_avg_75_84": "p_scores_75_84",
                "p_avg_85p": "p_scores_85plus",
                "deaths_2020_all_ages": "deaths_2020_all_ages",
                "average_deaths_2015_2019_all_ages": "average_deaths_2015_2019_all_ages",
            }
        )
        df = df[COLUMNS]
        # Fix date
        df.loc[:, "date"] = [clean_date(datetime(2020, 1, 1) + timedelta(days=d)) for d in df.date]
        # Sort rows
        df = df.sort_values(["location", "date"])
        return df

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.pipe(self.pipeline)

    def load(self, df: pd.DataFrame, output_path: str, date_accessed: str) -> None:
        ts_accessed = datetime.strptime(date_accessed, "%Y-%m-%d").isoformat()
        df_current = pd.read_csv(output_path)
        if not df.equals(df_current):
            # Export data
            df.to_csv(output_path, index=False)
            export_timestamp(PATHS.DATA_TIMESTAMP_XM_FILE, timestamp=ts_accessed)

    def run(self):
        df, date_accessed = self.extract()
        df = self.transform(df)
        self.load(df, PATHS.DATA_XM_MAIN_FILE, date_accessed)


def run_etl():
    etl = XMortalityETL()
    etl.run()
