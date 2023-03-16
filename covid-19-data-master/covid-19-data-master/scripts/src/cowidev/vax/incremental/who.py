import pandas as pd
import numpy as np

# from cowidev.utils.log import get_logger
from cowidev.utils.utils import check_known_columns
from cowidev.vax.utils.extra_source import add_latest_from_acdc
from cowidev.vax.utils.checks import VACCINES_ONE_DOSE
from cowidev.vax.utils.orgs import WHO_VACCINES, WHO_COUNTRIES
from cowidev.vax.utils.base import CountryVaxBase

# logger = get_logger()


# Sometimes the WHO doesn't yet include a vaccine in a country's metadata
# while there is evidence that it has been administered in the country
ADDITIONAL_VACCINES_USED = {
    "Cayman Islands": ["Oxford/AstraZeneca"],
    "Gambia": ["Johnson&Johnson"],
    "Ethiopia": ["Sinovac"],
    "Burundi": ["Johnson&Johnson"],
}


class WHO(CountryVaxBase):
    location = "WHO"
    source_url = "https://covid19.who.int/who-data/vaccination-data.csv"
    source_url_ref = "https://covid19.who.int/"
    rename_columns = {
        "DATE_UPDATED": "date",
        "COUNTRY": "location",
        "VACCINES_USED": "vaccine",
    }

    def read(self) -> pd.DataFrame:
        return pd.read_csv(self.source_url)

    def pipe_checks(self, df: pd.DataFrame) -> pd.DataFrame:
        check_known_columns(
            df,
            [
                "COUNTRY",
                "WHO_REGION",
                "ISO3",
                "PERSONS_VACCINATED_1PLUS_DOSE_PER100",
                "PERSONS_FULLY_VACCINATED",
                "DATA_SOURCE",
                "TOTAL_VACCINATIONS",
                "NUMBER_VACCINES_TYPES_USED",
                "TOTAL_VACCINATIONS_PER100",
                "FIRST_VACCINE_DATE",
                "PERSONS_FULLY_VACCINATED_PER100",
                "PERSONS_VACCINATED_1PLUS_DOSE",
                "VACCINES_USED",
                "DATE_UPDATED",
                "PERSONS_BOOSTER_ADD_DOSE",
                "PERSONS_BOOSTER_ADD_DOSE_PER100",
            ],
        )
        if len(df) > 300:
            raise ValueError(f"Check source, it may contain updates from several dates! Shape found was {df.shape}")
        if df.groupby("COUNTRY").DATE_UPDATED.nunique().nunique() == 1:
            if df.groupby("COUNTRY").DATE_UPDATED.nunique().unique()[0] != 1:
                raise ValueError("Countries have more than one date update!")
        else:
            raise ValueError("Countries have more than one date update!")
        return df

    def pipe_rename_countries(self, df: pd.DataFrame) -> pd.DataFrame:
        df["COUNTRY"] = df.COUNTRY.replace(WHO_COUNTRIES)
        return df

    def pipe_filter_entries(self, df: pd.DataFrame) -> pd.DataFrame:
        """Get valid entries:

        - Countries not coming from OWID (avoid loop)
        - Rows with total_vaccinations >= people_vaccinated >= people_fully_vaccinated
        """
        df = df[df.DATA_SOURCE == "REPORTING"].copy()
        mask_1 = (
            df.TOTAL_VACCINATIONS >= df.PERSONS_VACCINATED_1PLUS_DOSE
        ) | df.PERSONS_VACCINATED_1PLUS_DOSE.isnull()
        mask_2 = (df.TOTAL_VACCINATIONS >= df.PERSONS_FULLY_VACCINATED) | df.PERSONS_FULLY_VACCINATED.isnull()
        mask_3 = (
            (df.PERSONS_VACCINATED_1PLUS_DOSE >= df.PERSONS_FULLY_VACCINATED)
            | df.PERSONS_VACCINATED_1PLUS_DOSE.isnull()
            | df.PERSONS_FULLY_VACCINATED.isnull()
        )
        df = df[(mask_1 & mask_2 & mask_3)]
        df = df[df.COUNTRY.isin(WHO_COUNTRIES.values())]
        return df

    def pipe_vaccine_checks(self, df: pd.DataFrame) -> pd.DataFrame:
        vaccines_used = set(df.VACCINES_USED.dropna().apply(lambda x: [xx.strip() for xx in x.split(",")]).sum())
        vaccines_unknown = vaccines_used.difference(set(WHO_VACCINES.keys()) | {"Unknown Vaccine"})
        if vaccines_unknown:
            raise ValueError(f"Unknown vaccines {vaccines_unknown}. Update `vax.utils.who.config` accordingly.")
        return df

    def _map_vaccines_func(self, row) -> tuple:
        """Replace vaccine names and create column `only_2_doses`."""
        if pd.isna(row.VACCINES_USED):
            raise ValueError("Vaccine field is NaN")
        vaccines = pd.Series(row.VACCINES_USED.split(",")).str.strip()
        vaccines = vaccines.replace(WHO_VACCINES)
        only_2doses = all(-vaccines.isin(pd.Series(VACCINES_ONE_DOSE)))

        # Add vaccines that aren't yet recorded by the WHO
        if row.COUNTRY in ADDITIONAL_VACCINES_USED.keys():
            vaccines = pd.concat([vaccines, pd.Series(ADDITIONAL_VACCINES_USED[row.COUNTRY])])

        vaccines = [v for v in vaccines.unique() if v != "Unknown Vaccine"]
        return pd.Series([", ".join(sorted(vaccines)), only_2doses])

    def pipe_map_vaccines(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Based on the list of known vaccines, identifies whether each country is using only 2-dose
        vaccines or also some 1-dose vaccines. This determines whether people_fully_vaccinated can be
        calculated as total_vaccinations - people_vaccinated.
        Vaccines check
        """
        df[["VACCINES_USED", "only_2doses"]] = df.apply(self._map_vaccines_func, axis=1)
        return df

    def pipe_calculate_metrics(self, df: pd.DataFrame) -> pd.DataFrame:
        df[["people_vaccinated", "people_fully_vaccinated"]] = (
            df[["PERSONS_VACCINATED_1PLUS_DOSE", "PERSONS_FULLY_VACCINATED"]].astype("Int64").fillna(pd.NA)
        )
        df = df.assign(
            source_url=self.source_url_ref,
            total_vaccinations=df["TOTAL_VACCINATIONS"].astype("Int64").fillna(np.nan),
            total_boosters=df["PERSONS_BOOSTER_ADD_DOSE"].astype("Int64").fillna(np.nan),
        )
        df = df.pipe(self.pipe_rename_columns)
        return df

    def pipe_add_boosters(self, df: pd.DataFrame) -> pd.DataFrame:
        return add_latest_from_acdc(df, ["total_boosters"], priority=True)

    def increment_countries(self, df: pd.DataFrame):
        locations = set(df.location)
        for location in locations:
            df_c = df[df.location == location]
            df_c = df_c.dropna(
                subset=["people_vaccinated", "people_fully_vaccinated", "total_vaccinations", "total_boosters"],
                how="all",
            )
            if not df_c.empty:
                self.export_datafile(df_c, filename=location, attach=True, valid_cols_only=True)
                # logger.info(f"\tcowidev.vax.incremental.who.{location}: SUCCESS ✅")

    def pipeline(self, df: pd.DataFrame):
        return (
            df.pipe(self.pipe_checks)
            .pipe(self.pipe_rename_countries)
            .pipe(self.pipe_filter_entries)
            .pipe(self.pipe_vaccine_checks)
            .pipe(self.pipe_map_vaccines)
            .pipe(self.pipe_calculate_metrics)
            # .pipe(self.pipe_add_boosters)
        )

    def export(self):
        df = self.read().pipe(self.pipeline)
        self.increment_countries(df)


def main():
    WHO().export()
