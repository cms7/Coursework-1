import os

from cowidev import PATHS
from cowidev.variants.etl import run_etl
from cowidev.variants.grapher import run_grapheriser, run_explorerizer, run_db_updater
from cowidev.variants._parser import _parse_args


FILE_DS = "s3://covid-19/internal/variants/covid-variants.csv"
FILE_SEQ_DS = "s3://covid-19/internal/variants/covid-sequencing.csv"
# FILE_DS = "covid-variants.csv"
# FILE_SEQ_DS = "covid-sequencing.csv"
# FILE_SEQ_DS = os.path.join(PATHS.DATA_DIR, "variants", "covid-sequencing.csv")
FILE_GRAPHER = os.path.join(PATHS.INTERNAL_GRAPHER_DIR, "COVID-19 - Variants.csv")
FILE_SEQ_GRAPHER = os.path.join(PATHS.INTERNAL_GRAPHER_DIR, "COVID-19 - Sequencing.csv")
FILE_EXPLORER = os.path.join(PATHS.DATA_INTERNAL_DIR, "megafile--variants.json")


def run_step(step: str):
    if step == "etl":
        run_etl()
    elif step == "grapher-file":
        # Filter by num_seq
        run_grapheriser()
    elif step == "explorer-file":
        # Filter by num_seq
        run_explorerizer()
    elif step == "grapher-db":
        run_db_updater()


if __name__ == "__main__":
    args = _parse_args()
    run_step(args.step)
