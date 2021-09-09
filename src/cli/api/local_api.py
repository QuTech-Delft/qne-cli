from pathlib import Path
from typing import List, Optional, Tuple, Dict, Any

from cli.managers.config_manager import ConfigManager
from cli.managers.roundset_manager import RoundSetManager
from cli.output_converter import OutputConverter
from cli.type_aliases import (AppConfigType, ApplicationType, ExperimentType,
                              ResultType)
from cli.utils import read_json_file, write_json_file


class LocalApi:
    def __init__(self, config_manager: ConfigManager) -> None:
        self.__config_manager = config_manager

    def create_application(self, application: str, roles: List[str], app_path: Path) -> None:
        if self.__is_application_unique(application):
            self.__create_application_structure(application, roles, app_path)
        else:
            pass

    def init_application(self, path: Path) -> None:
        # Find out application name & roles from the files in 'path'
        application = ''
        roles = ['', '']

        if self.__is_application_unique(application):
            self.__create_application_structure(application, roles, path)


    def __create_application_structure(
        self, application: str, roles: List[str], path: Path
    ) -> None:
        self.__config_manager.add_application(application, path)

    def list_applications(self) -> List[ApplicationType]:
        return self.__config_manager.get_applications()

    def __is_application_unique(self, application: str) -> bool:
        return self.__config_manager.application_exists(application)

    def is_application_valid(self, application: str) -> Tuple[bool, str]:
        if self.__is_structure_valid(application) and \
               self.__is_application_unique(application) and \
               self.__is_config_valid(application):
            return True, "Valid"

        return False, "Invalid"

    def __is_structure_valid(self, application: str) -> bool:
        pass

    def __is_config_valid(self, application: str) -> bool:
        pass

    def get_application_config(self, application: str) -> AppConfigType:
        app_details = self.__config_manager.get_application(application)

        app_config_path = Path(app_details['path']) / 'config'
        application_json_path = app_config_path / 'application.json'
        network_json_path = app_config_path / 'network.json'

        application_data = read_json_file(application_json_path)
        network_data = read_json_file(network_json_path)

        app_config = {"application": application_data, "network": network_data}
        return app_config

    def create_experiment(
        self, name: str, app_config: AppConfigType, network: str, path: Path, application: str
    ) -> Tuple[bool, str]:

        experiment_directory = path / name
        if experiment_directory.is_dir():
            return False, f'Experiment directory {name} already exists.'

        experiment_directory.mkdir(parents=True)

        input_directory = experiment_directory / 'input'
        input_directory.mkdir(parents=True)
        self.__copy_input_files_from_application(application, input_directory)

        experiment_json_file = experiment_directory / 'experiment.json'
        experiment_meta = {
            "backend": {
                "location": "local",
                "type": "local_netsquid"
             },
            "number_of_rounds": 1,
            "description": f"{name}: experiment description"
        }

        asset_application = self.__create_asset_application(app_config)
        asset_network = self.__create_asset_network(network, app_config)
        asset = {"network": asset_network, "application": asset_application}

        experiment_data = {'meta': experiment_meta, 'asset': asset}
        write_json_file(experiment_json_file, experiment_data)

        return True, "Success"

    def __create_asset_application(self,  app_config: AppConfigType) -> List[Dict[str, Any]]:
        return []

    def __create_asset_network(self,  network: str, app_config: AppConfigType) ->  Dict[str, Any]:
        return {}

    def __copy_input_files_from_application(self,  application: str, input_directory: Path) -> None:
        """
        Copy the input/source files of the 'application' to the 'input_directory'

        Args:
            application: The application name for which the input files need to be copied
            input_directory: The destination where application files need to be stored

        """


    def check_valid_network(self, network: str, app_config: AppConfigType) -> bool:
        """
        Check if the network name is a valid network for the Application

        Args:
            network: The network name
            app_config: Application Configuration containing the available networks

        Returns:
            bool: True if the given network name is available in application configuration, False otherwise
        """
        return True

    def delete_experiment(self, path: Path) -> None:
        pass


    def run_experiment(self, path: Path, block: bool) -> Optional[List[ResultType]]:
        roundSetManager = RoundSetManager()
        roundSetManager.prepare_input(str(path.resolve()))
        roundSetManager.process()
        roundSetManager.terminate()
        return []

    def get_experiment(self, name: str) -> ExperimentType:
        pass

    def get_results(self, name: str) -> List[ResultType]:
        outputConverter = OutputConverter('log_dir', 'output_dir')
        round_number = 1
        result_list: List[ResultType] = []
        output_result: List[ResultType] = []
        output_result.append(outputConverter.convert(round_number, result_list))
        return output_result

    def validate_experiment(self, path: Path) -> Tuple[bool, str]:
        experiment_json = path / 'experiment.json'
        if not experiment_json.is_file():
            return False, 'File experiment.json not found in the current working directory'

        roundSetManager = RoundSetManager()
        return roundSetManager.validate_asset(path)
