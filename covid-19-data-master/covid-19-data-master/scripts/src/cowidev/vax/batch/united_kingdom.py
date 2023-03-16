import pandas as pd
from uk_covid19 import Cov19API

from cowidev.vax.utils.base import CountryVaxBase


class UnitedKingdom(CountryVaxBase):
    location = "United Kingdom"
    source_url = "https://coronavirus.data.gov.uk/details/vaccinations"

    def read(self):
        dfs = [
            self._read_metrics("areaType=overview"),
            self._read_metrics("areaType=nation"),
        ]
        df = pd.concat(dfs).reset_index(drop=True)
        return df

    def _read_metrics(self, filters):
        metrics = {
            "date": "date",
            "location": "areaName",
            "areaCode": "areaCode",
            "people_vaccinated": "cumPeopleVaccinatedFirstDoseByPublishDate",
            "people_fully_vaccinated": "cumPeopleVaccinatedSecondDoseByPublishDate",
            "total_vaccinations": "cumVaccinesGivenByPublishDate",
            "total_boosters": "cumPeopleVaccinatedThirdInjectionByPublishDate",
            "vaccinations_age": "vaccinationsAgeDemographics",
        }
        api = Cov19API(
            filters=[filters],
            structure=metrics,
        )
        df = api.get_dataframe()
        return df

    def pipe_source_url(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.assign(source_url=self.source_url)

    def pipe_vaccine(self, df: pd.DataFrame) -> pd.DataFrame:
        def _enrich_vaccine(date: str) -> str:
            if date < "2021-01-04":
                return "Pfizer/BioNTech"
            elif "2021-04-07" > date >= "2021-01-04":
                return "Oxford/AstraZeneca, Pfizer/BioNTech"
            elif date >= "2021-04-07":
                # https://www.reuters.com/article/us-health-coronavirus-britain-moderna-idUSKBN2BU0KG
                return "Moderna, Oxford/AstraZeneca, Pfizer/BioNTech"

        return df.assign(vaccine=df.date.apply(_enrich_vaccine))

    def pipe_add_autumn_boosters(self, df: pd.DataFrame) -> pd.DataFrame:
        # total_boosters does not include autumn 22 boosters, but this data can be collected from vaccinations_age field.
        autum22_boosters = df["vaccinations_age"].apply(lambda x: _sum_all_autumn_boosters_age(x))
        # autum22_boosters = (
        #     df["total_vaccinations"] - df["people_vaccinated"] - df["people_fully_vaccinated"] - df["total_boosters"]
        # ).fillna(0)
        df = df.assign(total_boosters=df["total_boosters"] + autum22_boosters)
        return df

    def pipe_select_output_cols(self, df: pd.DataFrame) -> pd.DataFrame:
        return df[
            [
                "location",
                "date",
                "vaccine",
                "source_url",
                "total_vaccinations",
                "people_vaccinated",
                "people_fully_vaccinated",
                "total_boosters",
            ]
        ]

    def pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.pipe(self.pipe_source_url)
            .pipe(self.pipe_vaccine)
            .pipe(self.pipe_add_autumn_boosters)
            .pipe(self.pipe_select_output_cols)
            .sort_values(by=["location", "date"])
            .dropna(
                subset=["total_vaccinations", "people_vaccinated", "people_fully_vaccinated", "total_boosters"],
                how="all",
            )
        )

    def _filter_location(self, df: pd.DataFrame, location: str) -> pd.DataFrame:
        return df[df.location == location].assign(location=location)

    def export(self):
        df_base = self.read().pipe(self.pipeline)

        # Maximum removed rows by make_monotonic, by UK nation
        max_removed_rows_dict = {
            "United Kingdom": 10,
            "England": 10,
            "Scotland": 10,
            "Wales": 48,
            "Northern Ireland": 300,
        }
        # Dates to filter by nation
        dates_filter = {
            "Northern Ireland": ["2023-02-03"],
        }
        for location in set(df_base.location):
            df = df_base.pipe(self._filter_location, location)
            if location in dates_filter:
                df = df[~df.date.isin(dates_filter[location])]
            df = df.pipe(self.make_monotonic, max_removed_rows=max_removed_rows_dict[location])
            self.export_datafile(df, filename=location)


def _sum_all_autumn_boosters_age(vaccinations_age):
    if vaccinations_age:
        values = [v.get("cumPeopleVaccinatedAutumn22ByVaccinationDate", 0) for v in vaccinations_age]
        return sum(v if v else 0 for v in values)
    return 0


def main():
    UnitedKingdom().export()
