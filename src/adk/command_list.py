"""
Entry point for the qne command-line.
Creates the Typer app and its commands
"""

import logging
from pathlib import Path
from typing import List, Optional, Tuple
from tabulate import tabulate

import typer
from typer import Typer

from adk.api.local_api import LocalApi
from adk.api.remote_api import RemoteApi
from adk.command_processor import CommandProcessor
from adk.decorators import catch_qne_adk_exceptions
from adk.exceptions import (ApplicationAlreadyExists, ApplicationNotFound, ApplicationFailedValidation,
    ExperimentDirectoryNotValid, ExperimentFailedValidation, ExperimentExecutionError, RolesNotUnique)
from adk.managers.config_manager import ConfigManager
from adk.settings import Settings
from adk.type_aliases import ErrorDictType
from adk.utils import reorder_data, validate_path_name

app = Typer(add_completion=False)
applications_app = Typer()
app.add_typer(applications_app, name="application", help="Manage applications")
experiments_app = Typer()
app.add_typer(experiments_app, name="experiment", help="Manage experiments")
networks_app = Typer()
app.add_typer(networks_app, name="network", help="Manage networks")

settings = Settings()
config_manager = ConfigManager(config_dir=settings.config_dir)
local_api = LocalApi(config_manager=config_manager)
remote_api = RemoteApi(config_manager=config_manager)
processor = CommandProcessor(local_api=local_api, remote_api=remote_api)

logging.basicConfig(level=logging.INFO)


@app.command("login")
@catch_qne_adk_exceptions
def login(
    host: str = typer.Argument(None),
    email: str = typer.Option(..., prompt=True, help="Email of the remote user"),
    password: str = typer.Option(..., prompt=True, hide_input=True, help="Password of the remote user"),
    username: Optional[bool] = typer.Option(False, "--username", help="Email is sent as username to login"),
) -> None:
    """
    Log in to a Quantum Network Explorer
    """
    processor.login(host=host, email=email, password=password, use_username=username)
    host = remote_api.get_active_host()
    typer.echo(f"Log in to '{host}' as user '{email}' succeeded")


@app.command("logout")
@catch_qne_adk_exceptions
def logout(host: Optional[str] = typer.Argument(None)) -> None:
    """
    Log out from a Quantum Network Explorer
    """
    if processor.logout(host=host):
        logout_host = "active host" if host is None else f"'{host}'"
        typer.echo(f"Logging out from {logout_host} succeeded")
    else:
        typer.echo("Not logged in to a host")


def retrieve_application_name_and_path(application_name: Optional[str]) -> Tuple[Path, str]:
    """
    For local applications only
    Retrieve the application_path and application_name from the configuration, cwd and parameters given
    """
    if application_name is not None:
        validate_path_name("Application", application_name)
        application_path_temp = config_manager.get_application_path(application_name)
        if application_path_temp is None:
            application_path = application_path_temp
        else:
            application_path = Path(application_path_temp)
    else:
        application_path = Path.cwd()
        application_name, _ = config_manager.get_application_from_path(application_path)

    if application_path is None or not application_path.is_dir():
        raise ApplicationNotFound(application_name)

    return application_path, application_name


def format_validation_messages(validation_dict: ErrorDictType) -> str:
    """
    Format the error, warnings and info messages collected during validation for printing to the terminal.
    """
    message = ""
    for key in validation_dict:
        if validation_dict[key]:
            for item in validation_dict[key]:
                if message:
                    message += "\n"
                message += f"{key.capitalize()}: {item}"
    return message


@applications_app.command("init")
@catch_qne_adk_exceptions
def applications_init(
    application_name: str = typer.Argument(..., help="Name of the application to initialize")
) -> None:
    """
    Initialize an existing application in the current path which is not already registered to QNE-ADK.
    This is needed for applications not created with QNE-ADK, for example when the files come from a
    repository or are directly copied to the file system.

    ./application_name is taken as application directory

    For example: qne application init application_name
    """
    validate_path_name("Application", application_name)

    application_exists, existing_application_path = config_manager.application_exists(application_name)
    if application_exists:
        raise ApplicationAlreadyExists(application_name, existing_application_path)

    cwd = Path.cwd()
    application_path = cwd / application_name
    processor.applications_init(application_name=application_name, application_path=application_path)
    typer.echo(f"Application '{application_name}' initialized successfully in directory '{str(application_path)}'")


@applications_app.command("create")
@catch_qne_adk_exceptions
def applications_create(
    application_name: str = typer.Argument(..., help="Name of the application"),
    roles: List[str] = typer.Argument(..., help="Names of the roles to be created"),
) -> None:
    """
    Create new application.

    For example: qne application create application_name Alice Bob
    """

    # Lower case roles for testing for the same role
    lower_case_roles = [role.lower() for role in roles]
    if not all(lower_case_roles.count(role) == 1 for role in lower_case_roles):
        raise RolesNotUnique()

    validate_path_name("Application", application_name)

    application_exists, existing_application_path = config_manager.application_exists(application_name)
    if application_exists:
        raise ApplicationAlreadyExists(application_name, existing_application_path)

    for role in roles:
        validate_path_name("Role", role)

    cwd = Path.cwd()
    application_path = cwd / application_name
    processor.applications_create(application_name=application_name,
                                  roles=list(roles),
                                  application_path=application_path)
    typer.echo(f"Application '{application_name}' created successfully in directory '{str(application_path)}'")


@applications_app.command("fetch")
@catch_qne_adk_exceptions
def applications_fetch(
    application_name: str = typer.Argument(..., help="Name of the application to fetch"),
) -> None:
    """
    An application developer can fetch an existing remote application.
    This command only makes sense for the original developer of the application to do additional development when
    the files were deleted locally.

    For example: qne application fetch existing_remote_application
    """

    cwd = Path.cwd()
    new_application_path = cwd / application_name

    # check for existence
    validate_path_name("Application", application_name)

    application_exists, existing_application_path = config_manager.application_exists(application_name)
    if application_exists:
        raise ApplicationAlreadyExists(application_name, existing_application_path)

    processor.applications_fetch(application_name=application_name,
                                 new_application_path=new_application_path)

    typer.echo(f"Application '{application_name}' fetched successfully in directory '{str(new_application_path)}'")


@applications_app.command("clone")
@catch_qne_adk_exceptions
def applications_clone(
    application_name: str = typer.Argument(..., help="Name of the application to clone"),
    remote: Optional[bool] = typer.Option(False, "--remote", help="Clone remote application"),
    new_application_name: Optional[str] = typer.Argument(None, help="New name for the cloned application"),
) -> None:
    """
    An application developer can clone an existing remote or local application and use it as a starting point for new
    application development.

    For example: qne application clone existing_application new_application
    """
    local = not remote
    if new_application_name is None:
        if local:
            typer.echo("Cloning a local application requires a new application name")
            return
        new_application_name = application_name

    cwd = Path.cwd()
    new_application_path = cwd / new_application_name

    # check for existence
    validate_path_name("Application", new_application_name)

    application_exists, existing_application_path = config_manager.application_exists(new_application_name)
    if application_exists:
        raise ApplicationAlreadyExists(new_application_name, existing_application_path)

    if local:
        application_path, application_name = retrieve_application_name_and_path(application_name=application_name)
        validate_dict = processor.applications_validate(application_name=application_name,
                                                        application_path=application_path)
        if validate_dict["error"] or validate_dict["warning"]:
            typer.echo("Local application was not cloned")
            validation_messages = format_validation_messages(validate_dict)
            raise ApplicationFailedValidation(application_name, validation_messages)

    processor.applications_clone(application_name=application_name,
                                 local=local,
                                 new_application_name=new_application_name,
                                 new_application_path=new_application_path)

    typer.echo(f"Application '{application_name}' cloned successfully in directory '{str(new_application_path)}'")


@applications_app.command("delete")
@catch_qne_adk_exceptions
def applications_delete(
    application_name: Optional[str] = typer.Argument(None, help="Name of the application")
) -> None:
    """
    Delete application files from the local application directory and delete the remote application under construction.
    A published application cannot be deleted remotely.

    When application_name is given ./application_name is taken as application directory, when this directory does not
    contain an application the application directory is fetched from the application configuration.
    When application_name is not given, the current directory is taken as application directory.
    """
    application_path, application_name = retrieve_application_name_and_path(application_name=application_name)

    deleted_completely = processor.applications_delete(application_name=application_name,
                                                       application_path=application_path)
    if deleted_completely:
        typer.echo("Application deleted successfully")
    else:
        if application_name is None:
            typer.echo("Application files deleted")
        else:
            typer.echo("Application files deleted, directory not empty")


@applications_app.command("upload")
@catch_qne_adk_exceptions
def applications_upload(
    application_name: Optional[str] = typer.Argument(None, help="Name of the application")
) -> None:
    """
    Request the application to be uploaded remote for testing purposes. Only when one or more successful experiment
    runs are done for this application, it can be published.

    When application_name is given ./application_name is taken as application directory, when this directory does not
    contain an application the application directory is fetched from the application configuration.
    When application_name is not given, the current directory is taken as application directory.
    """
    application_path, application_name = retrieve_application_name_and_path(application_name=application_name)
    validate_dict = processor.applications_validate(application_name=application_name,
                                                    application_path=application_path)
    validation_messages = format_validation_messages(validate_dict)

    if validate_dict["error"] or validate_dict["warning"]:
        typer.echo("Application was not uploaded")
        raise ApplicationFailedValidation(application_name, validation_messages)

    uploaded_success = processor.applications_upload(application_name=application_name,
                                                     application_path=application_path)
    if uploaded_success:
        typer.echo(f"Application '{application_name}' uploaded successfully")
    else:
        typer.echo(f"Application '{application_name}' not uploaded")


@applications_app.command("publish")
@catch_qne_adk_exceptions
def applications_publish(
    application_name: Optional[str] = typer.Argument(None, help="Name of the application")
) -> None:
    """
    Request the application to be published remote. When published successfully, the application can be run by other
    users.

    When application_name is given ./application_name is taken as application directory, when this directory does not
    contain an application the application directory is fetched from the application configuration.
    When application_name is not given, the current directory is taken as application directory.
    """
    application_path, application_name = retrieve_application_name_and_path(application_name=application_name)
    validate_dict = processor.applications_validate(application_name=application_name,
                                                    application_path=application_path)
    validation_messages = format_validation_messages(validate_dict)

    if validate_dict["error"] or validate_dict["warning"]:
        typer.echo("Application was not published")
        raise ApplicationFailedValidation(application_name, validation_messages)

    publish_success = processor.applications_publish(application_path=application_path)
    if publish_success:
        typer.echo(f"Application '{application_name}' published successfully")
    else:
        typer.echo(f"Application '{application_name}' not published")


@applications_app.command("list")
@catch_qne_adk_exceptions
def applications_list(
    remote: Optional[bool] = typer.Option(
        False, "--remote", help="List remote applications"
    ),
    local: Optional[bool] = typer.Option(
        False, "--local", help="List local applications"
    ),
) -> None:
    """
    List applications available to the user.
    """
    if not remote and not local:
        local = True
        remote = True

    applications = processor.applications_list(remote=remote, local=local)

    if local:
        if len(applications["local"]) == 0:
            typer.echo("There are no local applications available")
        else:
            desired_order_columns = ["name", "id", "path"]
            local_app_list = reorder_data(applications["local"], desired_order_columns)
            typer.echo(tabulate(local_app_list, headers={"name": "application name",
                                                         "id": "application id",
                                                         "path": "path"}))
            typer.echo(f'{len(applications["local"])} local application(s)')
            typer.echo()

    if remote:
        if len(applications["remote"]) == 0:
            typer.echo("There are no remote applications available")
        else:
            desired_order_columns = ["slug", "name", "id", "is_public", "is_disabled"]
            remote_app_list = reorder_data(applications["remote"], desired_order_columns)
            typer.echo(tabulate(remote_app_list, headers={"slug": "application name",
                                                          "name": "application full name",
                                                          "id": "application id",
                                                          "is_public": "public",
                                                          "is_disabled": "disabled"}))
            typer.echo(f'{len(applications["remote"])} remote application(s)')


@applications_app.command("validate")
@catch_qne_adk_exceptions
def applications_validate(
    application_name: Optional[str] = typer.Argument(None, help="Name of the application")
) -> None:
    """
    Validate the application created locally.

    When application_name is given ./application_name is taken as application directory, when this directory does not
    contain an application the application directory is fetched from the application configuration.
    When application_name is not given, the current directory is taken as application directory.
    """
    application_path, application_name = retrieve_application_name_and_path(application_name=application_name)

    validate_dict = processor.applications_validate(application_name=application_name,
                                                    application_path=application_path)
    validation_messages = format_validation_messages(validate_dict)

    if validate_dict["error"] or validate_dict["warning"]:
        raise ApplicationFailedValidation(application_name, validation_messages)

    typer.echo(f"Application '{application_name}' is valid")
    if validation_messages:
        typer.echo(f"{validation_messages}")


@experiments_app.command("create")
@catch_qne_adk_exceptions
def experiments_create(
    experiment_name: str = typer.Argument(..., help="Name of the experiment"),
    application_name: str = typer.Argument(..., help="Name of the application"),
    network_name: str = typer.Argument(..., help="Name of the network to use"),
    remote: bool = typer.Option(
        False, "--remote", help="Use remote application configuration"
    )
) -> None:
    """
    Create new experiment.
    """
    local = not remote
    validate_path_name("Experiment", experiment_name)

    cwd = Path.cwd()
    application_path = Path()
    if local:
        application_path, application_name = retrieve_application_name_and_path(application_name=application_name)

    validate_dict = processor.applications_validate(application_name=application_name,
                                                    application_path=application_path, local=local)
    if validate_dict["error"] or validate_dict["warning"]:
        typer.echo("Experiment was not created")
        validation_messages = format_validation_messages(validate_dict)
        raise ExperimentFailedValidation(validation_messages)

    processor.experiments_create(experiment_name=experiment_name, application_name=application_name,
                                 network_name=network_name, local=local, path=cwd)
    typer.echo(f"Experiment '{experiment_name}' created successfully in directory '{cwd}'")


@experiments_app.command("list")
@catch_qne_adk_exceptions
def experiments_list() -> None:
    """
    List remote experiments.
    """
    experiments = processor.experiments_list()
    if len(experiments) == 0:
        typer.echo("There are no remote experiments available")
    else:
        desired_order_columns = ["id", "created_at", "is_marked", "name"]
        remote_experiment_list = reorder_data(experiments, desired_order_columns)
        typer.echo(tabulate(remote_experiment_list, headers={"id": "experiment id",
                                                             "created_at": "created at",
                                                             "is_marked": "is marked",
                                                             "name": "application"}))
        typer.echo(f"{len(experiments)} remote experiment(s)")
        typer.echo()


def retrieve_experiment_name_and_path(experiment_name: Optional[str]) -> Tuple[Path, str]:
    """
    Retrieve the experiment_path and experiment_name from the cwd and parameters given.
    """
    path = Path.cwd()
    if experiment_name is not None:
        validate_path_name("Experiment", experiment_name)
        experiment_path = path / experiment_name
    else:
        experiment_name = path.name
        experiment_path = path

    if not local_api.is_valid_experiment_path(experiment_path):
        raise ExperimentDirectoryNotValid(str(experiment_path))

    return experiment_path, experiment_name


@experiments_app.command("delete")
@catch_qne_adk_exceptions
def experiments_delete(
    experiment_name_or_id: Optional[str] = typer.Argument(None, help="Name of the experiment or remote id"),
    remote: bool = typer.Option(
        False, "--remote", help="Delete a remote experiment"
    )
) -> None:
    """
    Delete experiment files.

    Local: When deleting an experiment locally, argument EXPERIMENT_NAME_OR_ID is the local experiment name, which is
    the subdirectory containing the experiment files. When the argument is empty the current directory is taken as
    experiment directory.
    The local experiment files are deleted, when the experiment was created with '--remote' and the experiment was run
    remotely, the remote experiment is also deleted.

    Remote: the argument EXPERIMENT_NAME_OR_ID is the remote experiment id to delete. No local files are deleted.
    """
    arg_experiment_name = experiment_name_or_id
    if remote:
        if arg_experiment_name is None:
            typer.echo("Remote experiment not deleted. No remote experiment id given")
        else:
            deleted_completely = processor.experiments_delete_remote_only(experiment_name_or_id)
            if deleted_completely:
                typer.echo(f"Remote experiment with experiment name or id '{experiment_name_or_id}' deleted "
                           f"successfully")
            else:
                typer.echo("Remote experiment not deleted. No valid experiment id given")
    else:
        # local
        experiment_path, experiment_name = retrieve_experiment_name_and_path(experiment_name=experiment_name_or_id)

        deleted_completely = processor.experiments_delete(experiment_name=experiment_name,
                                                          experiment_path=experiment_path)
        if deleted_completely:
            typer.echo("Experiment deleted successfully")
        else:
            if arg_experiment_name is None:
                typer.echo("Experiment files deleted")
            else:
                typer.echo("Experiment files deleted, directory not empty")


@experiments_app.command("run")
@catch_qne_adk_exceptions
def experiments_run(
    experiment_name: Optional[str] = typer.Argument(None, help="Name of the experiment"),
    block: bool = typer.Option(False, "--block", help="Wait for the (remote) experiment to finish"),
    update: bool = typer.Option(False, "--update", help="Update the application files"),
    timeout: Optional[int] = typer.Option(None, "--timeout", help="Limit the wait for the experiment to finish")
) -> None:
    """
    Run an experiment.

    When experiment_name is given ./experiment_name is taken as experiment directory. When experiment_name is not
    given, the current directory is taken as experiment directory.
    Block (remote experiment runs only) waits for the experiment to finish before returning (and results are available).
    Local experiment runs are blocked by default.
    Update (local experiment runs only) updates the application files for the experiment first.
    Timeout (optional) limits the wait (in seconds) for a blocked experiment to finish. In case of a local experiment,
    a timeout will cancel the experiment run. A remote experiment run is not canceled after a timeout and results can be
    fetched at a later moment.
    """
    experiment_path, _ = retrieve_experiment_name_and_path(experiment_name=experiment_name)
    local = local_api.is_experiment_local(experiment_path=experiment_path)
    # Validate the experiment before executing the run command
    validate_dict = processor.experiments_validate(experiment_path=experiment_path, local=local)

    if validate_dict["error"] or validate_dict["warning"]:
        typer.echo("Experiment did not run")
        validation_messages = format_validation_messages(validate_dict)
        raise ExperimentFailedValidation(validation_messages)

    if local:
        block = True
    if update:
        if local:
            # When updating the application files in the experiment, first validate the app again
            application_name = local_api.get_experiment_application(experiment_path)
            application_path, application_name = retrieve_application_name_and_path(
                application_name=application_name)

            validate_dict = processor.applications_validate(application_name=application_name,
                                                            application_path=application_path, local=local)
            if validate_dict["error"] or validate_dict["warning"]:
                typer.echo("Experiment cannot be updated")
                validation_messages = format_validation_messages(validate_dict)
                raise ApplicationFailedValidation(application_name, validation_messages)
        else:
            typer.echo("Update only valid for local experiment runs")
            return

    if block:
        typer.echo(f"Experiment is sent to the {'local' if local else 'remote'} server. "
                   f"Please wait until the results are received...")
    results = processor.experiments_run(experiment_path=experiment_path, block=block, update=update,
                                        timeout=timeout)
    if results is not None:
        if results and "error" in results[0]["round_result"]:
            raise ExperimentExecutionError(results[0]["round_result"]["error"])

        typer.echo("Experiment run successfully. Check the results using command 'experiment results'")
    else:
        typer.echo("Experiment sent successfully to server. Check the results using command 'experiment results'")


@experiments_app.command("validate")
@catch_qne_adk_exceptions
def experiments_validate(
    experiment_name: Optional[str] = typer.Argument(None, help="Name of the experiment")
) -> None:
    """
    Validate the local experiment.

    When experiment_name is given ./experiment_name is taken as experiment directory. When experiment_name is not
    given, the current directory is taken as experiment directory.
    """
    experiment_path, experiment_name = retrieve_experiment_name_and_path(experiment_name=experiment_name)

    validate_dict = processor.experiments_validate(experiment_path=experiment_path, local=True)
    validation_messages = format_validation_messages(validate_dict)

    if validate_dict["error"] or validate_dict["warning"]:
        raise ExperimentFailedValidation(validation_messages)

    typer.echo("Experiment is valid")
    if validation_messages:
        typer.echo(f"{validation_messages}")


@experiments_app.command("results")
@catch_qne_adk_exceptions
def experiments_results(
    experiment_name: Optional[str] = typer.Argument(None, help="Name of the experiment"),
    all_results: bool = typer.Option(False, "--all", help="Get all results for this experiment"),
    show: bool = typer.Option(False, "--show", help="Show the results on screen instead of saving to file"),
) -> None:
    """
    Get results for an experiment that run successfully.

    When experiment_name is given ./experiment_name is taken as experiment directory. When experiment_name is not
    given, the current directory is taken as experiment directory.
    """
    experiment_path, _ = retrieve_experiment_name_and_path(experiment_name=experiment_name)
    results = processor.experiments_results(all_results=all_results, experiment_path=experiment_path)
    if results is not None:
        if show:
            typer.echo(results)
        else:
            result_noun = "Results are" if all_results else "Result is"
            typer.echo(f"{result_noun} stored at location '{experiment_path / 'results' / 'processed.json'}'")
    else:
        typer.echo("No results received from backend yet. Check again later using command 'experiment results'")


@networks_app.command("list")
@catch_qne_adk_exceptions
def networks_list(
    remote: Optional[bool] = typer.Option(
        False, "--remote", help="List remote networks"
    ),
    local: Optional[bool] = typer.Option(
        True, "--local", help="List local networks"
    ),
) -> None:
    """
    List networks.
    """
    if not remote and not local:
        local = True

    networks = processor.networks_list(remote=remote, local=local)
    if local:
        if len(networks["local"]) == 0:
            typer.echo("There are no local networks available")
        else:
            desired_order_columns = ["name", "slug"]
            local_network_list = reorder_data(networks["local"], desired_order_columns)
            typer.echo(tabulate(local_network_list, headers={"name": "network name",
                                                             "slug": "network slug"}))
            typer.echo(f'{len(networks["local"])} local network(s)')
            typer.echo()

    if remote:
        if len(networks["remote"]) == 0:
            typer.echo("There are no remote networks available")
        else:
            desired_order_columns = ["id", "name", "slug"]
            remote_network_list = reorder_data(networks["remote"], desired_order_columns)
            typer.echo(tabulate(remote_network_list, headers={"id": "network id",
                                                              "name": "network name",
                                                              "slug": "network slug"}))
            typer.echo(f'{len(networks["remote"])} remote network(s)')


@networks_app.command("update")
@catch_qne_adk_exceptions
def networks_update(
    overwrite: Optional[bool] = typer.Option(
        False, "--overwrite", help="Overwrite local networks"
    )
) -> None:
    """
    Get remote networks and update local network files.
    """
    updated = processor.networks_update(overwrite=overwrite)
    if updated:
        typer.echo("The local networks are updated")
    else:
        typer.echo("The local networks are not updated completely")
