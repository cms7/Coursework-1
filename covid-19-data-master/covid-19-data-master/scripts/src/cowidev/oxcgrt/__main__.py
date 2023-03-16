import os

from cowidev import PATHS
from .etl import run_etl
from .grapher import run_grapheriser, run_db_updater
from ._parser import _parse_args


FILE_DS = os.path.join(PATHS.INTERNAL_INPUT_BSG_DIR, "latest.csv")
FILE_DIFF_DS = os.path.join(PATHS.INTERNAL_INPUT_BSG_DIR, "latest-differentiated.csv")
FILE_GRAPHER = os.path.join(PATHS.INTERNAL_GRAPHER_DIR, "COVID Government Response (OxBSG).csv")
FILE_COUNTRY_STD = os.path.join(PATHS.INTERNAL_INPUT_BSG_DIR, "bsg_country_standardised.csv")


def run_step(step: str):
    if step == "etl":
        run_etl(FILE_DS, FILE_DIFF_DS)
    elif step == "grapher-file":
        run_grapheriser(FILE_DS, FILE_COUNTRY_STD, FILE_GRAPHER)
    elif step == "grapher-db":
        run_db_updater(FILE_GRAPHER)


if __name__ == "__main__":
    args = _parse_args()
    run_step(args.step)
