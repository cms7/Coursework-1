"""Collect JHU Cases/Deaths data"""
import os

from termcolor import colored

from cowidev import PATHS
from cowidev.jhu.process import standardize_data, standard_export, inject_population, ZERO_DAY
from cowidev.jhu.utils import print_err
from cowidev.jhu.load import load_data, load_owid_continents, load_population
from cowidev.jhu.subnational import create_subnational
from cowidev.utils.utils import export_timestamp
from cowidev.grapher.db.utils.slack_client import send_warning
from cowidev.grapher.db.utils.db_imports import import_dataset
from cowidev.utils.slackapi import SlackAPI


ERROR = colored("[Error]", "red")
WARNING = colored("[Warning]", "yellow")

DATASET_NAME = "COVID-19 - Johns Hopkins University"


API = SlackAPI()


def check_data_correctness(df, logger, server):
    """Check that everything is alright in df"""
    errors = 0

    # Check that every country name is standardized
    df_uniq = df[["Country/Region", "location"]].drop_duplicates()
    if (msk := df_uniq["location"].isnull()).any():
        print_err("\n" + ERROR + " Could not find OWID names for:")
        print_err((countries := df_uniq.loc[msk, "Country/Region"].tolist()))
        if server:
            API.send_warning(
                channel="#corona-data-updates",
                title="JHU: Country missing!",
                message=f"Could not find OWID names for some countries: {countries}",
            )

    # Drop missing locations for the further checks – that error is addressed above
    df = df.dropna(subset=["location"])

    # Check for duplicate rows
    if df.duplicated(subset=["date", "location"]).any():
        print_err("\n" + ERROR + " Found duplicate rows:")
        print_err(df[df.duplicated(subset=["date", "location"])])
        errors += 1

    # Check for missing population figures
    df_pop = load_population()
    pop_entity_diff = set(df_uniq["location"]) - set(df_pop["location"]) - set(["International"])
    if len(pop_entity_diff) > 0:
        # this is not an error, so don't increment errors variable
        print("\n" + WARNING + " These entities were not found in the population dataset:")
        print(pop_entity_diff)
        print()
        formatted_msg = ", ".join(f"`{entity}`" for entity in pop_entity_diff)
        send_warning(
            channel="corona-data-updates",
            title="Some entities are missing from the population dataset",
            message=formatted_msg,
        )

    if errors == 0:
        logger.info("Data correctness check %s.\n" % colored("passed", "green"))
    else:
        logger.error("Data correctness check %s.\n" % colored("failed", "red"))
        raise ValueError("Data correctness check failed. Read the logs (run `cowid jhu generate`)")


def export(df, logger):
    # Export locations
    df_loc = df[["Country/Region", "location"]].drop_duplicates()
    df_loc = df_loc.merge(load_owid_continents(), on="location", how="left")
    df_loc = inject_population(df_loc)
    df_loc["population_year"] = df_loc["population_year"].round().astype("Int64")
    df_loc["population"] = df_loc["population"].round().astype("Int64")
    df_loc = df_loc.sort_values("location")
    df_loc.to_csv(os.path.join(PATHS.DATA_JHU_DIR, "locations.csv"), index=False)
    # Process/standardise data
    df = standardize_data(df)
    # The rest of the CSVs
    succeed = standard_export(df, PATHS.DATA_JHU_DIR, DATASET_NAME)
    if succeed:
        logger.info("Successfully exported CSVs to %s\n" % colored(os.path.abspath(PATHS.DATA_JHU_DIR), "magenta"))
    else:
        logger.error("JHU export failed.\n")
        raise ValueError("JHU export failed.")


def generate_dataset(logger, server_mode, skip_download=False):

    if not skip_download:
        logger.info("\nAttempting to download latest CSV files...")
        download_csv()
    # Load data
    df = load_data()

    check_data_correctness(df, logger, server_mode)

    export(df, logger)

    logger.info("Generating subnational file…")
    create_subnational()

    # Export timestamp
    export_timestamp(PATHS.DATA_TIMESTAMP_JHU_FILE)


def download_csv(logger):
    files = ["time_series_covid19_confirmed_global.csv", "time_series_covid19_deaths_global.csv"]
    for file in files:
        logger.info(file)
        os.system(
            f"curl --silent -f -o {PATHS.INTERNAL_INPUT_JHU_DIR}/{file} -L"
            f" https://github.com/CSSEGISandData/COVID-19/raw/master/csse_covid_19_data/csse_covid_19_time_series/{file}"
        )


def update_db():
    import_dataset(
        dataset_name=DATASET_NAME,
        namespace="owid",
        csv_path=os.path.join(PATHS.DATA_JHU_DIR, DATASET_NAME + ".csv"),
        default_variable_display={"yearIsDay": True, "zeroDay": ZERO_DAY},
        source_name="Johns Hopkins University CSSE COVID-19 Data",
        slack_notifications=False,
    )
