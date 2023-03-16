import click

from cowidev.cmd.commons.utils import OrderedGroup, feedback_log
from cowidev.gmobility.etl import run_etl
from cowidev.gmobility.grapher import run_grapheriser, run_db_updater


@click.group(name="gmobility", chain=True, cls=OrderedGroup)
@click.pass_context
def click_gm(ctx):
    """Google Mobility data pipeline."""
    pass


@click.command(name="generate", short_help="Step 1: Get and generate hospitalization dataset.")
@click.pass_context
def click_gm_generate(ctx):
    """Download and generate our COVID-19 Hospitalization dataset."""
    feedback_log(
        func=run_etl,
        server=ctx.obj["server"],
        domain="Google Mobility",
        step="generate",
        hide_success=True,
    )


@click.command(name="grapher-io", short_help="Step 2: Generate grapher-ready files.")
@click.pass_context
def click_gm_grapherio(ctx):
    feedback_log(
        func=run_grapheriser,
        server=ctx.obj["server"],
        domain="Google Mobility",
        step="generate",
        hide_success=True,
    )


@click.command(name="grapher-db", short_help="Step 3: Update Grapher database with generated files.")
@click.pass_context
def click_gm_grapherdb(ctx):
    feedback_log(
        func=run_db_updater,
        server=ctx.obj["server"],
        domain="Google Mobility",
        step="generate",
        hide_success=True,
    )


click_gm.add_command(click_gm_generate)
click_gm.add_command(click_gm_grapherio)
click_gm.add_command(click_gm_grapherdb)
