import os
from termcolor import colored

import pandas as pd

from cowidev import PATHS
from cowidev.cases_deaths.params import (
    zero_day,
    DATASET_NAME,
    AGGREGATE_REGIONS_SPEC,
    METRICS_BASE,
    COLUMNS_BASE,
    METRICS_PER_MILLION,
    GRAPHER_COL_NAMES,
)


def export_grapher_file(df, logger):
    # The rest of the CSVs
    succeed = _export_grapher_file(df, PATHS.DATA_CASES_DEATHS_DIR, DATASET_NAME)
    if succeed:
        logger.info(
            "Successfully exported CSVs to %s\n" % colored(os.path.abspath(PATHS.DATA_CASES_DEATHS_DIR), "magenta")
        )
    else:
        logger.error("Case/Death export failed.\n")
        raise ValueError("Case/Death export failed.")


def _export_grapher_file(df, output_path, grapher_name):
    # Grapher
    df_grapher = df.copy()
    df_grapher["date"] = pd.to_datetime(df_grapher["date"]).map(lambda date: (date - zero_day).days)
    df_grapher = (
        df_grapher[GRAPHER_COL_NAMES.keys()]
        .rename(columns=GRAPHER_COL_NAMES)
        .to_csv(os.path.join(output_path, "%s.csv" % grapher_name), index=False)
    )

    # Table & public extracts for external users
    # Excludes aggregates
    excluded_aggregates = list(
        set(AGGREGATE_REGIONS_SPEC.keys())
        - set(
            [
                "World",
                "North America",
                "South America",
                "Europe",
                "Africa",
                "Asia",
                "Oceania",
                "European Union",
                "High income",
                "Upper middle income",
                "Lower middle income",
                "Low income",
            ]
        )
    )
    df_table = df[~df["location"].isin(excluded_aggregates)]
    # full_data.csv
    full_data_cols = existsin(COLUMNS_BASE, df_table.columns)
    df_table[full_data_cols].dropna(subset=METRICS_BASE, how="all").to_csv(
        os.path.join(output_path, "full_data.csv"), index=False
    )
    # Pivot variables (wide format)
    for col_name in [*METRICS_BASE, *METRICS_PER_MILLION]:
        df_pivot = df_table.pivot(index="date", columns="location", values=col_name)
        # move World to first column
        cols = df_pivot.columns.tolist()
        cols.insert(0, cols.pop(cols.index("World")))
        df_pivot[cols].to_csv(os.path.join(output_path, "%s.csv" % col_name))
    return True


def existsin(l1, l2):
    return [x for x in l1 if x in l2]
