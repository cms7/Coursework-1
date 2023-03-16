"""Collect Cases/Deaths data"""
import os

from cowidev import PATHS
from cowidev.cases_deaths.extract import load_data
from cowidev.cases_deaths.transform import process_data
from cowidev.cases_deaths.load import export_grapher_file
from cowidev.cases_deaths.params import DATASET_NAME, ZERO_DAY
from cowidev.utils.utils import export_timestamp
from cowidev.grapher.db.utils.db_imports import import_dataset


def generate_dataset(logger, server_mode):
    """Generate Cases/Deaths dataset."""
    # Load data
    logger.info("Cases/Deaths: Loading data…")
    df = load_data(server_mode)

    # Process data
    logger.info("Cases/Deaths: Processing data…")
    df = process_data(df)

    # Export data
    export_grapher_file(df, logger)

    # logger.info("Generating subnational file…")
    # create_subnational()

    # Export timestamp
    export_timestamp(PATHS.DATA_TIMESTAMP_CASES_DEATHS_FILE)


def update_db():
    import_dataset(
        dataset_name=DATASET_NAME,
        namespace="owid",
        csv_path=os.path.join(PATHS.DATA_CASES_DEATHS_DIR, DATASET_NAME + ".csv"),
        default_variable_display={"yearIsDay": True, "zeroDay": ZERO_DAY},
        source_name="World Health Organization",
        slack_notifications=False,
    )
