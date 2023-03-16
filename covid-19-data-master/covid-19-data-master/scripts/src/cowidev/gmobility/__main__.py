import os

from cowidev import PATHS
from cowidev.gmobility.etl import run_etl
from cowidev.gmobility.grapher import run_grapheriser, run_db_updater
from cowidev.gmobility._parser import _parse_args


def run_step(step: str):
    if step == "etl":
        run_etl()
    elif step == "grapher-file":
        run_grapheriser()
    elif step == "grapher-db":
        run_db_updater()


if __name__ == "__main__":
    args = _parse_args()
    run_step(args.step)
