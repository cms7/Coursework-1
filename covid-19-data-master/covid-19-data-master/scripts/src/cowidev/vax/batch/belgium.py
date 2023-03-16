import pandas as pd

from cowidev.utils.utils import check_known_columns
from cowidev.vax.utils.base import CountryVaxBase
from cowidev.vax.utils.utils import build_vaccine_timeline


class Belgium(CountryVaxBase):
    def __init__(self) -> None:
        self.location = "Belgium"
        self.source_url = "https://epistat.sciensano.be/Data/COVID19BE_VACC.csv"
        self.source_url_ref = "https://epistat.wiv-isp.be/covid/"

    def read(self) -> pd.DataFrame:
        df = pd.read_csv(self.source_url)
        check_known_columns(df, ["DATE", "REGION", "AGEGROUP", "SEX", "BRAND", "DOSE", "COUNT"])
        return df[["DATE", "DOSE", "COUNT"]]

    def pipe_dose_check(self, df: pd.DataFrame) -> pd.DataFrame:
        doses_wrong = set(df.DOSE).difference(["A", "B", "C", "E", "E2", "E3"])
        if doses_wrong:
            raise ValueError(f"Invalid dose type {doses_wrong}")
        return df

    def pipe_aggregate(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.groupby(["DATE", "DOSE"], as_index=False)
            .sum()
            .sort_values("DATE")
            .pivot(index="DATE", columns="DOSE", values="COUNT")
            .reset_index()
            .fillna(0)
        )

    def pipe_rename_columns(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.rename(
            columns={
                "DATE": "date",
            }
        )

    def pipe_add_totals(self, df: pd.DataFrame) -> pd.DataFrame:
        df = df.assign(
            total_vaccinations=df.A + df.B + df.C + df.E + df.E2 + df.E3,
            people_vaccinated=df.A + df.C,
            people_fully_vaccinated=df.B + df.C,
            total_boosters=df.E + df.E2 + df.E3,
        )
        return df.drop(columns=["A", "B", "C", "E"])

    def pipe_cumsum(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.assign(
            total_vaccinations=df.total_vaccinations.cumsum().astype(int),
            people_vaccinated=df.people_vaccinated.cumsum().astype(int),
            people_fully_vaccinated=df.people_fully_vaccinated.cumsum().astype(int),
            total_boosters=df.total_boosters.cumsum().astype(int),
        )

    def pipe_vaccine_name(self, df: pd.DataFrame) -> pd.DataFrame:
        # Source:
        # https://datastudio.google.com/embed/u/0/reporting/c14a5cfc-cab7-4812-848c-0369173148ab/page/p_j1f02pfnpc
        return build_vaccine_timeline(
            df,
            {
                "Pfizer/BioNTech": "2020-12-28",
                "Moderna": "2021-01-11",
                "Oxford/AstraZeneca": "2021-02-12",
                "Johnson&Johnson": "2021-04-28",
                "Novavax": "2022-01-19",
            },
        )

    def pipe_metadata(self, df: pd.DataFrame) -> pd.DataFrame:
        return df.assign(location=self.location, source_url=self.source_url_ref)

    def pipeline(self, df: pd.DataFrame) -> pd.DataFrame:
        return (
            df.pipe(self.pipe_dose_check)
            .pipe(self.pipe_aggregate)
            .pipe(self.pipe_rename_columns)
            .pipe(self.pipe_add_totals)
            .pipe(self.pipe_cumsum)
            .pipe(self.pipe_vaccine_name)
            .pipe(self.pipe_metadata)
        )

    def export(self):
        df = self.read().pipe(self.pipeline)
        self.export_datafile(df)


def main():
    Belgium().export()
