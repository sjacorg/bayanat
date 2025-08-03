# -*- coding: utf-8 -*-
import json
from multiprocessing import Pool, cpu_count
from typing import Any, Generator, Literal

import click
import pandas as pd
from flask import Blueprint, current_app, render_template, Response, request
from flask.cli import with_appcontext
from flask_security import auth_required
from flask_security import roles_required, roles_accepted, current_user
from sqlalchemy import desc
from sqlalchemy.sql.expression import func

from enferno.deduplication.models import DedupRelation
from enferno.extensions import db, rds
from enferno.tasks import start_dedup

from enferno.settings import Config as cfg
from enferno.utils.http_response import HTTPResponse

deduplication = Blueprint(
    "deduplication",
    __name__,
    static_folder="../static",
    template_folder="../deduplication/templates",
    cli_group=None,
    url_prefix="/deduplication",
)


@deduplication.before_request
@auth_required("session")
def dedup_before_request():
    pass


@deduplication.app_context_processor
def deduplication_app_context() -> dict:
    """
    pass a global flag to indicate that the deduplication plugin(Blueprint) is enabled.
    used to display/hide deduplication menu item inside templates

    Returns:
        - A dictionary with deduplication flag set to True if Blueprint is registered.
    """
    return {"deduplication": True}


@deduplication.route("/dashboard/")
@roles_accepted("Admin", "Mod")
def deduplication_dash() -> str:
    """
    Endpoint for rendering deduplication dashboard page.

    Returns:
        - The html content of the deduplication dashboard page.
    """
    return render_template("deduplication.html")


@deduplication.route("/api/deduplication/")
@roles_required("Admin")
def api_deduplication() -> Response:
    """
    Provides APIs for imported deduplication CSV data, supports paging.
    """
    page = request.args.get("page", 1, int)
    per_page = request.args.get("per_page", 1000, int)
    data = DedupRelation.query.order_by(desc(DedupRelation.updated_at)).paginate(
        page=page, per_page=per_page
    )
    # calculate the number of unprocessed items , this totally simplifies calculating progress
    pending = DedupRelation.query.filter(DedupRelation.status == 0).count()
    response = {
        "items": [item.to_dict() for item in data.items],
        "perPage": per_page,
        "total": data.total,
        "pending": pending,
    }
    return HTTPResponse.success(data=response)


@deduplication.route("/api/process", methods=["POST"])
@roles_required("Admin")
def api_process() -> Response:
    """
    Endpoint used to process all deduplication data.
    """
    start_dedup.delay(current_user.id)
    return HTTPResponse.success(message="Processing will start shortly.")


@deduplication.route("/api/stop", methods=["POST"])
@roles_required("Admin")
def api_process_stop() -> Response:
    """
    Endpoint used to stop processing dedup data.
    """
    # just remove the redis flag
    rds.set("dedup", 0)

    return HTTPResponse.success(message="Processing will stop shortly.")


@deduplication.cli.command()
@click.argument("file", type=click.File("r"))
@click.option(
    "-r", "--remove", is_flag=True, prompt="Are you sure you want to remove existing data?"
)
@click.option("-d", "--distance", type=float, default=0.7)
@with_appcontext
def dedup_import(file: str, remove: bool, distance: float) -> None:
    """
    Imports data from deduplication compatible file, with an option to clear existing data.

    Args:
        - file: The file to import.
        - remove: A flag to remove existing data.
        - distance: The distance to use for deduplication.

    Returns:
        None
    """
    if remove:
        DedupRelation.query.delete()
        db.session.commit()
        click.echo("Cleared all existing matches.")

    # create pandas data frame
    click.echo("Reading CSV file...")
    df = pd.read_csv(file)
    exts = ["." + ext for ext in cfg.ETL_VID_EXT]
    click.echo("Cleaning up...")
    df["match_video"] = df["match_video"].replace(r"_.{64}_vgg_features", "", regex=True)
    df["match_video"] = df["match_video"].replace("_vgg_features", "", regex=True)
    df["match_video"] = df["match_video"].replace(exts, "", regex=True)

    df["query_video"] = df["query_video"].replace(r"_.{64}_vgg_features", "", regex=True)
    df["query_video"] = df["query_video"].replace("_vgg_features", "", regex=True)
    df["query_video"] = df["query_video"].replace(exts, "", regex=True)

    click.echo("Droping self-referencing matches...")
    df = df[df.query_video != df.match_video]
    click.echo("Droping matches with out-of-scope distances...")
    df = df[df.distance < distance]
    click.echo("Droping duplicate matches based on unique_index column...")
    df.drop_duplicates(subset="unique_index", keep="first", inplace=True)
    click.echo("Droping duplicate matches for same query and match videos...")
    # to handle duplicate in both directions , generate a computed column first
    df["match_id"] = df.apply(lambda x: str(sorted([x.query_video, x.match_video])), axis=1)
    df.drop_duplicates(subset=["match_id"], keep="first", inplace=True)

    records = df.to_dict(orient="records")
    with click.progressbar(records, label="Importing Matches", show_pos=True) as bar:
        for item in bar:
            br = DedupRelation()
            br.query_video = item.get("query_video")
            br.match_video = item.get("match_video")
            br.distance = item.get("distance")
            # to create a unique string for the match and disallow duplicate matches
            br.match_id = sorted((br.query_video, br.match_video))
            br.notes = item.get("notes")
            if not br.save():
                click.echo(
                    "Error importing match {}-{}.".format(
                        item.get("query_video"), item.get("match_video")
                    )
                )
    click.echo("=== Done ===")


@deduplication.cli.command()
@click.option("-p", "--no-of-processes", type=int, default=int(cpu_count() / 2))
@with_appcontext
def fast_process(no_of_processes: int) -> None:
    """
    Process deduplication matches in a faster way.

    Args:
        - no_of_processes: The number of processes to use.

    Returns:
        None
    """
    rds.delete("dedup_processing")
    pool = Pool(processes=no_of_processes)
    items = DedupRelation.query.filter_by(status=0).order_by(func.random())
    if items:
        pool.map(DedupRelation.process, items, 1)


# statistics endpoints


@deduplication.get("/status")
def status() -> Response:
    """
    Endpoint to return deduplication backend status.
    """
    if status := rds.get("dedup"):
        response = {"status": status.decode()}
        return HTTPResponse.success(data=response)

    return HTTPResponse.error("Background tasks are not running correctly", status=503)
