import re

import pandas as pd
from bs4 import BeautifulSoup

from cowidev.utils import clean_date, clean_date_series, get_soup
from cowidev.utils.web.download import read_xlsx_from_url
from cowidev.vax.utils.base import CountryVaxBase
from cowidev.vax.utils.utils import build_vaccine_timeline


class NewZealand(CountryVaxBase):
    # Consider: https://github.com/minhealthnz/nz-covid-data/tree/main/vaccine-data
    source_url_ref = "https://www.health.govt.nz/our-work/diseases-and-conditions/covid-19-novel-coronavirus/covid-19-data-and-statistics/covid-19-vaccine-data"
    base_url = "https://www.health.govt.nz"
    location = "New Zealand"
    rename_columns = {
        "First doses": "people_vaccinated",
        "Second doses": "people_fully_vaccinated",
        "Third primary doses": "third_dose",
        "First Boosters": "total_boosters",
        "Second Boosters": "total_boosters_2",
        "Date": "date",
    }
    vaccines_start_date = {
        "Pfizer/BioNTech": "2021-01-01",
        "Oxford/AstraZeneca": "2021-11-26",
        "Novavax": "2022-03-14",
    }
    columns_cumsum = [
        "people_vaccinated",
        "people_fully_vaccinated",
        "third_dose",
        "total_boosters",
        "total_boosters_2",
    ]

    def read(self) -> pd.DataFrame:
        """Reads the data from the source."""
        soup = get_soup(self.source_url_ref)
        # self._read_latest(soup)
        link = self._parse_file_link(soup)
        df = read_xlsx_from_url(link, sheet_name="Date")
        return df

    def _read_latest(self, soup):
        """Reads the latest data from the soup."""
        tables = pd.read_html(str(soup))
        latest = tables[0].set_index("Unnamed: 0")
        latest_kids = tables[1].set_index("Unnamed: 0")
        latest_date = re.search(r"Data in this section is as at 11:59pm ([\d]+ [A-Za-z]+ 20\d{2})", soup.text).group(1)
        self.latest = pd.DataFrame(
            {
                "people_vaccinated": latest.loc["First dose", "Cumulative total"]
                + latest_kids.loc["First dose", "Cumulative total"],
                "people_fully_vaccinated": latest.loc["Second dose", "Cumulative total"]
                + latest_kids.loc["Second dose", "Cumulative total"],
                "total_boosters": latest.loc["Boosters", "Cumulative total"]
                + latest.loc["Third primary", "Cumulative total"],
                "date": [clean_date(latest_date, "%d %B %Y")],
            }
        )

    def _parse_file_link(self, soup: BeautifulSoup) -> str:
        """Parses the link from the soup."""
        href = soup.find(id="download").find_next("a")["href"]
        link = f"{self.base_url}{href}"
        return link

    def pipe_cumsum(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates cumulative sum of the columns."""
        df[self.columns_cumsum] = df[self.columns_cumsum].cumsum()
        return df

    def pipe_date(self, df: pd.DataFrame) -> pd.DataFrame:
        """Formats the date column."""
        return df.assign(date=clean_date_series(df.date, "%d/%m/%Y"))

    def pipe_boosters(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates the total boosters."""
        return df.assign(total_boosters=df.total_boosters + df.third_dose + df.total_boosters_2)

    def pipe_latest_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        """pipes the latest metrics."""
        return df.sort_values("date").append(self.latest, ignore_index=True).drop_duplicates("date", keep="last")

    def pipe_total_vaccinations(self, df: pd.DataFrame) -> pd.DataFrame:
        """Calculates the total vaccinations."""
        return df.assign(total_vaccinations=df.people_vaccinated + df.people_fully_vaccinated + df.total_boosters)

    def pipe_vaccine(self, df: pd.DataFrame) -> pd.DataFrame:
        """Builds the vaccine timeline."""
        return build_vaccine_timeline(df, self.vaccines_start_date)

    def pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        """Pipeline for the data"""
        return (
            df.pipe(self.pipe_rename_columns)
            .pipe(self.pipe_cumsum)
            .pipe(self.pipe_date)
            .pipe(self.pipe_boosters)
            # .pipe(self.pipe_latest_metrics)
            .pipe(self.pipe_total_vaccinations)
            .pipe(self.pipe_vaccine)
            .pipe(self.pipe_metadata)
            .pipe(self.make_monotonic)
        )

    def export(self):
        """Exports the data to CSV"""
        df = self.read().pipe(self.pipeline)
        self.export_datafile(df, valid_cols_only=True)


def main():
    NewZealand().export()
