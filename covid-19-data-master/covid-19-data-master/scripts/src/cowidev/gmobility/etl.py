import os

import pandas as pd
from cowidev.gmobility.dtypes import dtype

FILE_DS = os.path.join("/tmp", "google-mobility.csv")


class GMobilityETL:
    source_url = "https://www.gstatic.com/covid19/mobility/Global_Mobility_Report.csv"

    def extract(self):
        return pd.read_csv(
            self.source_url,
            usecols=dtype.keys(),
            # low_memory=False,
            dtype=dtype,
        )

    def load(self, df: pd.DataFrame) -> None:
        # Export data
        df.to_csv(FILE_DS, index=False)

    def run(self):
        df = self.extract()
        self.load(df)


def run_etl():
    etl = GMobilityETL()
    etl.run()
