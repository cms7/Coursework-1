import click

from cowidev.cmd.commons.utils import OrderedGroup, feedback_log
from cowidev.cases_deaths.generate import generate_dataset, update_db


@click.group(name="casedeath", chain=True, cls=OrderedGroup)
@click.pass_context
def click_cases_deaths(ctx):
    """COVID-19 Cases/Deaths data pipeline."""
    pass


@click.command(name="generate", short_help="Step 1: Generate dataset.")
@click.pass_context
def click_cd_generate(ctx):
    feedback_log(
        func=generate_dataset,
        server=ctx.obj["server"],
        server_mode=ctx.obj["server"],
        domain="Cases/Deaths",
        step="generate",
        text_success="Public data files generated.",
        logger=ctx.obj["logger"],
    )


@click.command(name="grapher-db", short_help="Step 2: Update Grapher database with generated files.")
@click.pass_context
def click_cd_db(ctx):
    feedback_log(
        func=update_db,
        server=ctx.obj["server"],
        domain="Cases/Deaths",
        step="grapher-db",
        text_success="Files uploaded to the database.",
        hide_success=True,
    )


click_cases_deaths.add_command(click_cd_generate)
click_cases_deaths.add_command(click_cd_db)
