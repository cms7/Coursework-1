import pandas as pd


class OxCGRTETL:
    def __init__(self) -> None:
        self.source_url = (
            "https://raw.githubusercontent.com/OxCGRT/covid-policy-tracker/master/data/OxCGRT_nat_latest.csv"
        )
        self.source_url_diff = [
            "https://github.com/OxCGRT/covid-policy-tracker/raw/master/data/OxCGRT_nat_differentiated_withnotes_2020.csv",
            "https://github.com/OxCGRT/covid-policy-tracker/raw/master/data/OxCGRT_nat_differentiated_withnotes_2021.csv",
            "https://github.com/OxCGRT/covid-policy-tracker/raw/master/data/OxCGRT_nat_differentiated_withnotes_2022.csv",
        ]

    def extract(self):
        # print(1)
        df = pd.read_csv(self.source_url, low_memory=False)
        # print(2)
        df_diff = self._load_diff_data()
        return df, df_diff

    def _load_diff_data(self):
        dfs = []
        for url in self.source_url_diff:
            # print(url)
            dfs.append(
                pd.read_csv(
                    url,
                    usecols=[
                        "Date",
                        "RegionCode",
                        # "Country",
                        "CountryName",
                        "StringencyIndex_NonVaccinated",
                        "StringencyIndex_Vaccinated",
                        "StringencyIndex_WeightedAverage",
                    ],
                    low_memory=False,
                )
            )
        return pd.concat(
            dfs,
            ignore_index=True,
        )

    def transform(self, df: pd.DataFrame) -> pd.DataFrame:
        return df

    def load(self, df: pd.DataFrame, output_path: str):
        df.to_csv(output_path, index=False)

    def run(self, output_path: str, output_path_diff: str):
        df, df_diff = self.extract()
        self.load(df, output_path)
        self.load(df_diff, output_path_diff)


def run_etl(output_path: str, output_path_diff: str):
    etl = OxCGRTETL()
    etl.run(output_path, output_path_diff)
