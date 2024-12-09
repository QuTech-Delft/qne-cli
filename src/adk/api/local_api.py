import copy
import filecmp
import fnmatch
import os
from pathlib import Path
import re
import shutil
from typing import Any, cast, Dict, List, Optional

from adk import utils
from adk.exceptions import (ApplicationDoesNotExist,
                            ExperimentDirectoryNotValid, ExperimentValueError, JsonFileNotFound, MalformedJsonFile,
                            NetworkNotFound, NoNetworkAvailable, PackageNotComplete, SchemaError)
from adk.managers.config_manager import ConfigManager
from adk.managers.roundset_manager import RoundSetManager
from adk.managers.vanilla_netsquid_roundet_manager import VanillaNetSquidRoundSetManager
from adk.generators.network_generator import FullyConnectedNetworkGenerator
from adk.parsers.output_converter import OutputConverter
from adk.settings import BASE_DIR, DEFAULT_BACKEND_TYPE, SUPPORTED_BACKEND_TYPES
from adk.type_aliases import (AppConfigType, AppResultType, ApplicationType, ApplicationDataType, app_configNetworkType,
                              app_configApplicationType, AssetType, assetApplicationType, assetNetworkType,
                              ErrorDictType, ExperimentDataType, ResultType,
                              RoundSetType, ChannelData, MetaType, NetworkData, NodeData, TemplateData,
                              AssetNodeListType, AssetChannelListType)
from adk.validators import validate_json_file, validate_json_schema


# pylint: disable=R0904
# Too many public methods
# pylint: disable=C0302
# too-many-lines
class LocalApi:
    """
    Defines the methods used for local handling of the commands
    """
    def __init__(self, config_manager: ConfigManager) -> None:
        self.__config_manager = config_manager
        self.__read_network_data()

    def __read_network_data(self) -> None:
        """
        Initialize the data for 'networks', 'channels', 'nodes', 'templates'
        """
        base_path = Path(BASE_DIR) / 'networks'
        file_name = base_path / 'networks.json'
        try:
            self.__networks_data: NetworkData = utils.read_json_file(file_name)
            file_name = base_path / 'channels.json'
            self.__channels_data: ChannelData = utils.read_json_file(file_name)
            file_name = base_path / 'nodes.json'
            self.__nodes_data: NodeData = utils.read_json_file(file_name)
            file_name = base_path / 'templates.json'
            self.__templates_data: TemplateData = utils.read_json_file(file_name)
        except JsonFileNotFound:
            raise PackageNotComplete(str(file_name)) from None

    def _get_network_info(self, identifier_value: str, identifier_type: str = "slug") -> Optional[Dict[str, Any]]:
        """
        Get the network information containing name, slug and channel list

        Args:
            identifier_value: Value of the identifier used to select/match the network
            identifier_type: Possible values for identifier_type are slug, name. Default is slug

        Returns:
            Network information containing name, slug, and channel list
        """

        for _, data in self.__networks_data["networks"].items():
            if data[identifier_type].lower() == identifier_value.lower():
                return data

        return None

    def _get_network_slug(self, network_name: str) -> Optional[str]:
        """
        Get the slug associated with the network based on the name of the network

        Args:
            network_name: Name of the network

        Returns:
            The slug for the given network
        """
        network_data = self._get_network_info(identifier_value=network_name, identifier_type="name")
        if network_data:
            if 'slug' in network_data:
                return str(network_data['slug'])

        return None

    def _get_network_name(self, network_slug: str) -> Optional[str]:
        """
        Get the name associated with the network based on the slug of the network

        Args:
            network_slug: Slug of the network

        Returns:
            The Name for the given network
        """
        network_data = self._get_network_info(network_slug)
        if network_data:
            if 'name' in network_data:
                return str(network_data['name'])

        return None

    def _get_qne_network_name(self, network_name: str) -> Optional[str]:
        """
        Get the case-sensitive name of the network as defined in the networks.json

        Args:
            network_name: Provided name of the network (can be in any case)

        Returns:
            The Name for the given network as available in the networks.json
        """
        network_data = self._get_network_info(identifier_value=network_name, identifier_type="name")
        if network_data:
            if "name" in network_data:
                return str(network_data["name"])

        return None

    def _get_channels_for_network(self, network_slug: str) -> Optional[List[str]]:
        """
        Get the list of channels available in the network

        Args:
            network_slug: Slug of the network

        Returns:
            List of channels
        """
        network_data = self._get_network_info(network_slug)
        if network_data:
            if "channels" in network_data:
                return cast(List[str], network_data["channels"])

        return None

    def _get_channel_info(self, channel_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get the channel information containing node & parameter information

        Args:
            channel_slug: Slug of the channel

        Returns:
            Channel information containing node & parameter information
        """

        for channel in self.__channels_data["channels"]:
            if channel["slug"] == channel_slug:
                return channel

        return None

    def _get_node_info(self, node_slug: str) -> Optional[Dict[str, Any]]:
        """
        Get the node information containing node parameters & qubit information

        Args:
            node_slug: Slug of the Node

        Returns:
            Node information containing node parameters & information
        """

        for node in self.__nodes_data["nodes"]:
            if node["slug"] == node_slug:
                return node

        return None

    def _get_templates(self) -> Dict[str, Dict[str, Any]]:
        """
        Get all the templates information

        Returns:
            A dictionary containing key as template slug and value as template information
        """
        return {template["slug"]: template for template in self.__templates_data["templates"]}

    def _get_networks(self) -> List[Dict[str, Any]]:
        """
        Get all the networks

        Returns:
            A dictionary containing key as network slug and value as network information
        """
        return [self.__networks_data["networks"][network] for network in self.__networks_data["networks"]]

    def _get_template_params_max_min_range(self) -> Dict[str, Dict[str, Dict[str, Any]]]:
        """
        Get the maximum and minimum value for all the template parameters

        Returns:
            A dictionary containing key as template slug and value as the dictionary containing:
            { name of the sub-parameter : { maximum_value: 1, minimum_value: 0 } }
        """
        max_min_dict: Dict[str, Dict[str, Dict[str, Any]]] = {}
        for template in self.__templates_data["templates"]:
            max_min_dict[template["slug"]] = {}
            for value in template["values"]:
                max_min_dict[template["slug"]][value["name"]] = {
                    "maximum_value": value["maximum_value"],
                    "minimum_value": value["minimum_value"],
                }

        return max_min_dict

    def _get_network_nodes(self) -> Dict[str, List[str]]:
        """
        Loops through all the networks in networks/networks.json and gets all the nodes within this network.

        returns:
        Returns a dict of networks, each having their own list including the nodes:
        E.g.: {"randstad": ["leiden", "amsterdam", "the-hague"], "the-netherlands": ["etc..",]}
        """
        # Read network
        network_nodes: Dict[str, List[str]] = {}

        data_networks = self.__networks_data
        data_channels = self.__channels_data

        for network in data_networks["networks"]:
            channel_lst = []
            for channel in data_channels["channels"]:
                if channel["slug"] in data_networks["networks"][network]["channels"]:
                    if channel["node1"] not in channel_lst:
                        channel_lst.append(channel["node1"])
                    if channel["node2"] not in channel_lst:
                        channel_lst.append(channel["node2"])

            network_nodes[data_networks["networks"][network]["slug"]] = channel_lst

        return network_nodes

    def get_application_id(self, application_path: Path) -> Optional[str]:
        """
        Get the application id from manifest.json

        Args:
            application_path: The location of the application

        Returns:
            Application id or None
        """
        application_data = self.get_application_data(application_path)
        if "application_id" in application_data["remote"]:
            return str(application_data["remote"]["application_id"])
        return None

    @staticmethod
    def set_application_data(application_path: Path, application_data: ApplicationDataType) -> None:
        """
        Write the application data to manifest.json

        Args:
            application_path: The location of the application
            application_data: New or updated application data

        """
        manifest_json_file = application_path / 'manifest.json'
        utils.write_json_file(manifest_json_file, application_data)

    @staticmethod
    def get_application_data(application_path: Path) -> ApplicationDataType:
        """
        Get the application data from manifest.json

        Args:
            application_path: The location of the application

        Returns:
            A dictionary containing the application data
        """
        manifest_json_file = application_path / 'manifest.json'
        application_data = utils.read_json_file(manifest_json_file)
        return cast(ApplicationDataType, application_data)

    def init_application(self, application_name: str, application_path: Path) -> None:
        """
        Initializes the application directory structure for an existing set of files. The files are moved to the right
        directory when needed. The files are not created if they do not exist (we have application create command for
        that). Only manifest.json is created when it doesn't exist or adjusted when it exists. The application name
        is written/updated to it. The application is added to the application configuration.

        Args:
            application_name: name of the application
            application_path: the path where the application is stored

        Raises:
            DirectoryAlreadyExists: Raised when directory (or file) application_name already exists
        """
        application_name = application_name.lower()

        # init the config files
        app_config_path = application_path / 'config'
        if not app_config_path.exists():
            # create config directory and move all config-files to config
            app_config_path.mkdir(parents=True, exist_ok=True)

        # Move the config files to the config directory
        utils.move_files(application_path, app_config_path,
                         files_list=self.__get_config_file_names())

        app_src_path = application_path / 'src'
        if not app_src_path.exists():
            # create src and move all python files to src
            app_src_path.mkdir(parents=True, exist_ok=True)

        # Move all python files to the src directory
        python_files = self.get_application_file_names(application_path)
        utils.move_files(application_path, app_src_path,
                         files_list=python_files)

        # prepare manifest
        if not (application_path / 'manifest.json').is_file():
            application_data = utils.get_default_manifest(application_name)
        else:
            application_data = self.get_application_data(application_path)
            application_data["application"]["name"] = application_name
            # reset remote
            application_data["remote"] = {}
        # write manifest
        self.set_application_data(application_path, application_data)

        # add application to the local administration
        self.__config_manager.add_application(application_name=application_name,
                                              application_path=application_path)

    def clone_application(self, application_name: str, new_application_name: str,
                          new_application_path: Path) -> None:
        """
        Clone the application by copying the required files in the local application structure.

        Creates the application directory structure and copies the necessary files from the source application.
        Each application will consist of a manifest.json and two directories: src and config.
        In the directory config, the files network.json, application.json and
        result.json will be copied. In the directory src, python files will be copied according to the value of
        the roles in the source application.

        Args:
            application_name: name of the application to be cloned
            new_application_name: name of the application after cloning
            new_application_path: location of application files

        """
        application_name = application_name.lower()
        new_application_name = new_application_name.lower()

        application_path = self.__config_manager.get_application_path(application_name)
        if application_path is None:
            # This will never happen because of checks done earlier
            return
        source_app_path = Path(application_path)

        dest_app_src_path = new_application_path / 'src'
        dest_app_config_path = new_application_path / 'config'
        dest_app_src_path.mkdir(parents=True, exist_ok=True)
        dest_app_config_path.mkdir(parents=True, exist_ok=True)

        utils.copy_files(source_app_path, new_application_path, files_list=['manifest.json'])
        utils.copy_files(source_app_path / 'config', dest_app_config_path,
                         files_list=self.__get_config_file_names())
        utils.copy_files(source_app_path / 'src', dest_app_src_path,
                         files_list=self.get_application_file_names(app_src_path=source_app_path))
        application_data = self.get_application_data(source_app_path)
        # only fill the fields that change with a new application
        application_data["application"]["name"] = new_application_name
        application_data["application"]["description"] = "add description"
        # reset remote
        application_data["remote"] = {}
        self.set_application_data(new_application_path, application_data)
        # add application to the local administration
        self.__config_manager.add_application(application_name=new_application_name,
                                              application_path=new_application_path)

    def create_application(self, application_name: str, roles: List[str], application_path: Path) -> None:
        """
        Creates the application directory structure. Each application will consist of a manifest.json and two
        directories: src and config. In the directory config, the files network.json, application.json and
        result.json will be generated. In the directory src, python files will be generated according to the value of
        the list roles.

        Args:
            application_name: name of the application
            roles: a list of roles
            application_path: the path where the application is stored

        Raises:
            DirectoryAlreadyExists: Raised when directory (or file) application_name already exists
        """
        application_name = application_name.lower()

        # code to create the local application in root dir
        app_src_path = application_path / 'src'
        app_config_path = application_path / 'config'
        app_src_path.mkdir(parents=True, exist_ok=True)
        app_config_path.mkdir(parents=True, exist_ok=True)

        for role in roles:
            utils.write_file(app_src_path / f'app_{role.lower()}.py', utils.get_py_dummy())

        # Network.json configuration
        networks = {"networks": [], "roles": roles}
        temp_list = []

        # Check if the network there are more network nodes available for this network compared to the
        # amount of roles given by the user
        for network in self._get_network_nodes().items():
            if len(roles) <= len(network[1]):
                temp_list.append(network[0])

        networks["networks"] = temp_list

        # Remove already created application structure
        if not networks["networks"]:
            shutil.rmtree(application_path)
            raise NoNetworkAvailable()

        utils.write_json_file(app_config_path / 'network.json', networks)

        # Application.json configuration
        data = utils.get_dummy_application(roles)
        utils.write_json_file(app_config_path / 'application.json', data)

        # Result.json configuration
        utils.write_json_file(app_config_path / 'result.json', {"round_result_view": [],
                                                                "cumulative_result_view": [],
                                                                "final_result_view": []
                                                                })

        # Manifest.json configuration
        self.set_application_data(application_path, utils.get_default_manifest(application_name))
        # add application to the local administration
        self.__config_manager.add_application(application_name=application_name, application_path=application_path)

    def list_applications(self) -> List[ApplicationType]:
        """
        Function to list the applications

        Returns:
            A list of applications
        """
        local_applications = self.__config_manager.get_applications()
        return local_applications

    def _delete_src(self, application_path: Path) -> bool:
        """
        Delete src directory containing source files, we don't delete *.py here, only app_<role>.py

        Args:
            application_path: the path where the application is stored
        """
        src_dir_deleted = False
        application_src_path = application_path / 'src'
        # read the network config for the app file names in src
        application_config_path = application_path / 'config'
        if application_config_path.is_dir():
            config_network_file = application_config_path / 'network.json'
            if config_network_file.is_file():
                # Delete the app files for the roles from network.json from the
                # application/src directory
                application_file_names = [application_src_path / application_file_name for
                                          application_file_name in
                                          self.__get_role_file_names(application_config_path)]
                for app_file in application_file_names:
                    if app_file.is_file():
                        app_file.unlink()

        try:
            os.rmdir(application_src_path)
            src_dir_deleted = True
        except OSError:  # The directory is not empty
            pass

        return src_dir_deleted

    def _delete_config(self, application_path: Path) -> bool:
        """
        Delete config directory containing configuration files

        Args:
            application_path: the path where the application is stored
        """
        config_dir_deleted = False
        application_config_path = application_path / 'config'
        config_files_list = self.__get_config_file_names()
        for config_file in config_files_list:
            file_to_delete = application_config_path / config_file
            if file_to_delete.is_file():
                file_to_delete.unlink()

        try:
            os.rmdir(application_config_path)
            config_dir_deleted = True
        except OSError:  # The directory is not empty
            pass

        return config_dir_deleted

    def delete_application(self, application_name: Optional[str], application_path: Path) -> bool:
        """
        Deletes the application files.
        The application files and subdirectories are deleted. Only when the current directory is the
        application directory the current directory cannot be deleted, leaving a trace of the application.
        Only files that belong to an application are deleted. When a directory is not empty it is not deleted.

        Args:
            application_name: Optional. The application directory deleted will be ./application_name, the
            current directory or the application path registered in application config for application_name
            application_path: The location of the application

        Returns:
            True if the complete application (including directory application_name) was deleted, otherwise false
            (leaving traces of the application)

        Raises:
            ExperimentDirectoryNotValid when the application path is not recognized as an application
        """
        application_dir_deleted = False
        all_subdir_deleted = True

        # check if the application exists and save the app name to delete it later
        application_name_from_config, _ = self.__config_manager.get_application_from_path(application_path)

        # Check if application path exists
        if application_path.is_dir():
            application_src_path = application_path / 'src'
            if application_src_path.is_dir():
                all_subdir_deleted = self._delete_src(application_path) and all_subdir_deleted

            application_config_path = application_path / 'config'
            if application_config_path.is_dir():
                all_subdir_deleted = self._delete_config(application_path) and all_subdir_deleted

            # Delete manifest.json
            manifest_json = application_path / 'manifest.json'
            if manifest_json.is_file():
                manifest_json.unlink()

            # only when we called application delete from the parent directory and all subdirs were removed try to
            # remove application dir
            if all_subdir_deleted and application_name is not None:
                try:
                    os.rmdir(application_path)
                    application_dir_deleted = True
                except OSError:  # The directory is not empty
                    pass
        else:
            raise ApplicationDoesNotExist(str(application_path))

        # remove application from configuration
        self.__config_manager.delete_application(application_name_from_config)
        return all_subdir_deleted and application_dir_deleted

    @staticmethod
    def __is_manifest_valid_json(application_path: Path, error_dict: ErrorDictType) -> None:
        """
        This function validates if manifest.json contains valid json and if it passes schema validation.

        Args:
            application_path: The location of the application
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        manifest_json_file = application_path / 'manifest.json'

        # Validate manifest.json (does it exist and is valid json according to the schema)
        manifest_schema = Path(os.path.join(BASE_DIR, 'schema', 'applications', 'manifest.json', ''))
        valid, message = validate_json_schema(manifest_json_file, manifest_schema)
        if not valid:
            error_dict["error"].append(message)

    def validate_application(self, application_name: str, application_path: Path) -> ErrorDictType:
        """
        Function that checks if:
        - The application is valid by validating if it exists in .qne/application.json
        - The file and directory structure is correct
        - The json files in the config directory contain valid json
        - The json files passes against schema validation
        - The python source files have valid syntax
        - The main() in app_{role}.py has app_config as one of the parameters
        - The main() in app_{role}.py has the parameters which are listed in application config
        - Variables listed in result.json are returned by the main() in app_{role}.py

        Args:
            application_name: Name of the application
            application_path: Path of where the application is located

        returns:
            Returns empty list when all validations pass
            Returns dict containing error messages of the validations that failed
        """
        error_dict: ErrorDictType = utils.get_empty_errordict()
        application_exists, _ = self.__config_manager.application_exists(application_name)

        if application_exists:
            self.__is_manifest_valid_json(application_path, error_dict)
            self.__is_structure_valid(application_path, error_dict)
            self.__is_application_config_valid(application_path, error_dict)
            self.__is_config_valid_json(application_path, error_dict)
            self.__is_python_valid(application_path, error_dict)
            self.__is_result_config_valid(application_path, error_dict)
        else:
            error_dict["error"].append(f"Application '{application_name}' does not exist")

        return error_dict

    def get_application_result(self, application_name: str) -> Optional[AppResultType]:
        """
        Get the result containing round_result_view, cumulative_result_view and final_result_view
        for the application

        Args:
            application_name: Name of the application for which to get the result structures

        Returns:
            A dictionary containing application result structures
        """
        app_details = self.__config_manager.get_application(application_name)

        if app_details and "path" in app_details:
            app_config_path = Path(app_details["path"]) / 'config'
            result_json_path = app_config_path / 'result.json'

            app_result: AppResultType = utils.read_json_file(result_json_path)

            return app_result

        return None

    def get_application_config(self, application_name: str) -> Optional[AppConfigType]:
        """
        Get the configuration containing input, network and roles information for the application

        Args:
            application_name: Name of the application for which to get the configuration

        Returns:
            A dictionary containing application configuration information

        """
        app_details = self.__config_manager.get_application(application_name)

        if app_details and "path" in app_details:
            app_config_path = Path(app_details["path"]) / 'config'
            application_json_path = app_config_path / 'application.json'
            network_json_path = app_config_path / 'network.json'

            app_config_application: app_configApplicationType = utils.read_json_file(application_json_path)
            app_config_network: app_configNetworkType = utils.read_json_file(network_json_path)

            app_config = {"application": app_config_application, "network": app_config_network}
            return cast(AppConfigType, app_config)

        return None

    def __is_config_valid_json(self, application_path: Path, error_dict: ErrorDictType) -> None:
        # Validate if json string is correct and validate against json schema's
        app_schema_path = Path(BASE_DIR) / 'schema/applications'
        app_config_path = application_path / 'config'

        for config_file in self.__get_config_file_names():
            if (app_config_path / config_file).is_file():
                schema_valid, ve = validate_json_schema(app_config_path / config_file, app_schema_path / config_file)
                if not schema_valid:
                    error_dict["error"].append(ve)

    @staticmethod
    def __get_config_file_names() -> List[str]:
        return ['application.json', 'network.json', 'result.json']

    @staticmethod
    def __get_simulator_file_names() -> List[str]:
        return ['roles.yaml', 'network.yaml']

    @staticmethod
    def __get_application_role_names(app_config_path: Path) -> List[str]:
        """
        Get the roles used in this application/experiment from config/application.json
        """
        app_config_application: app_configApplicationType = utils.read_json_file(app_config_path / 'application.json')
        roles = []

        for input_template in app_config_application:
            for role in input_template['roles']:
                if role not in roles:
                    roles.append(role)

        return roles

    @staticmethod
    def __get_role_names(app_config_path: Path) -> List[str]:
        """
        Get the roles used in this application/experiment from config/network.json
        """
        config_network_data = utils.read_json_file(app_config_path / 'network.json')
        config_application_roles: List[str] = config_network_data["roles"] if "roles" in config_network_data else []

        return config_application_roles

    def __get_role_file_names(self, app_config_path: Path) -> List[str]:
        """
        Add app_ and .py to each role in config/network.json so that it matches the application python files
        Note that these file names are lower case, role names can be upper case
        """
        config_application_roles = self.__get_role_names(app_config_path)
        application_file_names = ['app_' + role.lower() + '.py' for role in config_application_roles]

        return application_file_names

    @staticmethod
    def __get_role_name_from_role_file(role_file: str) -> Optional[str]:
        result = re.search('app_(.*).py', role_file)
        return result.group(1) if result else None

    @staticmethod
    def get_application_file_names(app_src_path: Path) -> List[str]:
        """
        Given that the source files provided by the application developer can have any format (not just app_*.py, but
        also *.py) get the application python files (*.py) for the given directory
        """
        application_file_names = fnmatch.filter(os.listdir(app_src_path), '*.py')
        return application_file_names

    def __is_application_config_valid(self, application_path: Path, error_dict: ErrorDictType) -> None:
        """
        Only when network.json and application.json are valid check roles from application.json if they are
        in network.json
        """
        app_config_path = application_path / 'config'

        valid_network, _ = validate_json_file(app_config_path / 'network.json')
        # if not valid network.json it will be reported in __is_config_valid_json
        valid_application, _ = validate_json_file(app_config_path / 'application.json')
        # if not valid application.json it will be reported in __is_config_valid_json
        if valid_network and valid_application:
            application_roles = self.__get_application_role_names(app_config_path)
            network_roles = self.__get_role_names(app_config_path)

            # Check if the roles in the config/application.json match as roles in the config/network.json
            application_files_not_in_network = [role for role in application_roles if role not in network_roles]
            for application_role_name in application_files_not_in_network:
                error_dict["error"].append(
                    f"The application role '{application_role_name}' in "
                    f"'{app_config_path / 'application.json'}' not found in "
                    f"'{app_config_path / 'network.json'}'")

    def __is_structure_valid(self, application_path: Path, error_dict: ErrorDictType) -> None:
        app_config_path = application_path / 'config'
        app_src_path = application_path / 'src'

        # Check if the config directory is complete
        if app_config_path.is_dir():
            for file in self.__get_config_file_names():
                if not (app_config_path / file).is_file():
                    error_dict["error"].append(f"{app_config_path} should contain the file '{file}'")
        else:
            error_dict["error"].append(f"{application_path} should contain a 'config' directory")

        if app_src_path.is_dir():
            valid, _ = validate_json_file(app_config_path / 'network.json')
            # if not valid network.json it will be reported in __is_config_valid_json
            if valid:
                role_file_names = self.__get_role_file_names(app_config_path)
                # Get all the files in the src directory
                src_dir_files = self.get_application_file_names(app_src_path)

                # Check if the roles in the config/network.json match as file names in the src directory
                role_files_not_in_src = [role for role in role_file_names if role not in src_dir_files]
                for role_file_name in role_files_not_in_src:
                    error_dict["error"].append(
                        f"The application file '{role_file_name}' for the corresponding role in "
                        f"'{app_config_path / 'network.json'}' not found in '{app_src_path}'")
        else:
            error_dict["error"].append(f"{application_path} should contain a 'src' directory")

        # Validate that the manifest.json exists
        if not (application_path / 'manifest.json').is_file():
            error_dict["warning"].append(f"{application_path} should contain the file 'manifest.json'")

    def __is_python_valid(self, application_path: Path, error_dict: ErrorDictType) -> None:
        """
        Validate if the python code in src/*.py has valid syntax

        Args:
            application_path: Path of where the application is located
            error_dict: A dictionary for storing the validation errors

        """
        app_config_path = application_path / 'config'
        app_src_path = application_path / 'src'

        role_file_names = self.__get_role_file_names(app_config_path)
        src_dir_files = self.get_application_file_names(app_src_path)
        for python_file in src_dir_files:
            valid, validation_message = utils.check_python_syntax(app_src_path / python_file)
            if not valid:
                error_dict["error"].append(f"The application source file {python_file} has syntax errors"
                                           f"\n {validation_message}")
            elif python_file in role_file_names:
                # The syntax is valid. For role app-files we can now check for the input params to the main()
                self.__is_valid_input_params_for_role(application_path, python_file, error_dict)

    def __is_valid_input_params_for_role(self, application_path: Path, role_file: str, error_dict: ErrorDictType) \
            -> None:
        """
        Validate if the inputs defined in application config are passed as parameters to main() in app_{role}.py

        Args:
            application_path: Path of where the application is located
            role_file: Name of the file in which function is defined
            error_dict: A dictionary for storing the validation errors

        """
        role_name = self.__get_role_name_from_role_file(role_file)

        if role_name:
            role_inputs = self.__get_role_inputs(application_path, role_name)
            app_src_path = application_path / 'src'
            if (app_src_path / role_file).is_file():
                arg_list = utils.get_function_arguments(app_src_path / role_file, function_name='main')
                if arg_list:
                    for input_list_item in role_inputs:
                        if input_list_item not in arg_list:
                            error_dict['error'].append(f"main() in {role_file} is missing the {input_list_item} "
                                                       f"argument")
                else:
                    error_dict['error'].append(f"main() not found in file {role_file}")
        else:
            error_dict['error'].append(f"Name of {role_file} is not properly formatted")

    @staticmethod
    def __get_role_inputs(application_path: Path, role: str) -> List[str]:
        """
        Get the list of inputs which are defined for the role in application config file

        Args:
            application_path: Path of where the application is located
            role: Lower case name of the role for which inputs are needed

        Returns:
            A List containing inputs available for the role

        """
        app_config_path = application_path / 'config'
        app_config_application: app_configApplicationType = utils.read_json_file(app_config_path / 'application.json')
        role_inputs = ['app_config']

        for input_template in app_config_application:
            if role in map(str.lower, input_template['roles']):
                for value_item in input_template['values']:
                    role_inputs.append(value_item['name'])

        return role_inputs

    @staticmethod
    def __get_result_variables(application_path: Path, role_name: str) -> List[str]:

        with open(application_path / 'config' / 'result.json', encoding='utf-8') as f:
            result = f.read()

        variable_list = re.findall(r'\$\.app_'+role_name+r'\.([\w]+)', result)
        return variable_list

    def __is_result_config_valid(self, application_path: Path, error_dict: ErrorDictType) -> None:
        """
        Validate if the variables used in result config are returned by the main() in the app_{role}.py

        Args:
            application_path: Path of where the application is located
            error_dict: A dictionary for storing the validation errors

        """

        app_config_path = application_path / 'config'
        app_src_path = application_path / 'src'

        role_file_names = self.__get_role_file_names(app_config_path)
        for role_file in role_file_names:  # pylint: disable=R1702 too-many-nested-blocks
            if (app_src_path / role_file).is_file():
                return_list = utils.get_function_return_variables(app_src_path / role_file, function_name='main')
                role_name = self.__get_role_name_from_role_file(role_file)
                if role_name and return_list:
                    result_variables = self.__get_result_variables(application_path, role_name)
                    undefined_result_variables = set()
                    for return_item in return_list:
                        for result_var in result_variables:
                            if result_var not in return_item:
                                undefined_result_variables.add(result_var)

                    if undefined_result_variables:
                        for item in undefined_result_variables:
                            error_dict['error'].append(f'Variable {item} is used in result.json, but not found in '
                                                       f'return statement(s) of main() in file {role_file}')

    def experiments_create(self, experiment_name: str, application_name: str, network_name: str, local: bool,
                           path: Path, app_config: AppConfigType) -> None:
        """
        Create all the necessary resources for experiment creation
         - 1. Get the network data for the specified network_name
         - 2. Create the asset
         - 3. Create experiment.json containing the metadata and asset information

        Args:
            experiment_name: Name of the experiment
            application_name: Name of the application for which to create experiment
            network_name: Name of the network to use
            local: Are we going to run this experiment local (or remote)
            path: Location where the experiment directory is to be created
            app_config: A dictionary containing application configuration information

        """
        network_data: assetNetworkType = self.get_network_data(network_name=network_name)
        copied_network_data = copy.deepcopy(network_data)
        asset_network: assetNetworkType = self.create_asset_network(network_data=copied_network_data,
                                                                    app_config=app_config)

        self.__create_experiment(experiment_name=experiment_name, application_name=application_name,
                                 local=local, path=path, app_config=app_config, asset_network=asset_network)

    def get_network_data(self, network_name: str) -> assetNetworkType:
        """
        Fetch the data for the specified network_name from the json files in networks folder
        Args:
            network_name: Name of the network whose data needs to be fetched
        Returns:
            The complete network information with channels & nodes
        """
        channels_list = []
        nodes_list = []

        network_slug = self._get_network_slug(network_name)

        if network_slug:
            channels = self._get_channels_for_network(network_slug=network_slug)
            if channels:
                for channel_slug in channels:
                    channel_info = self._get_channel_info(channel_slug=channel_slug)
                    channels_list.append(channel_info)

            network_nodes = self._get_network_nodes()
            if network_slug in network_nodes:
                for node_slug in network_nodes[network_slug]:
                    nodes_list.append(self._get_node_info(node_slug=node_slug))
            else:
                raise NetworkNotFound(network_name)

            qne_network_name = self._get_qne_network_name(network_name)

            return {
                "name": qne_network_name,
                "slug": network_slug,
                "channels": channels_list,
                "nodes": nodes_list,
            }

        raise NetworkNotFound(network_name)

    def __create_experiment(self, experiment_name: str, application_name: str, local: bool, path: Path,
                            app_config: AppConfigType, asset_network: assetNetworkType) -> None:
        """
        Create experiment.json with meta and asset information. We don't need to check if the network is compatible
        with the default backend type because the default backend type can run all networks.

        Args:
            experiment_name: Name of the directory where experiment.json will be created
            application_name: Name of the application for which to create the experiment
            local: Are we going to run this experiment local (or remote)
            app_config: A dictionary containing application configuration information
            path: Location where experiment directory needs to be created
            asset_network: Filled Network parameters with default values
        """
        experiment_path = path / experiment_name
        experiment_path.mkdir(parents=True)

        if local:
            experiment_input_path = experiment_path / 'input'
            experiment_input_path.mkdir(parents=True)
            self.__copy_input_files_from_application(application_name, experiment_input_path)

        experiment_json_file = experiment_path / 'experiment.json'
        experiment_meta = {
            "application": {
                "slug": application_name,
                "app_version": "" if local else app_config["app_version"],
                "multi_round": False if local else app_config["multi_round"]
            },
            "backend": {
                "location": "local" if local else "remote",
                "type": DEFAULT_BACKEND_TYPE
            },
            "description": f"description of {experiment_name} here",
            "number_of_rounds": 1,
            "name": experiment_name
        }
        asset_application = self.__create_asset_application(app_config)
        asset = {"network": asset_network, "application": asset_application}

        experiment_data = {"meta": experiment_meta, "asset": asset}
        utils.write_json_file(experiment_json_file, experiment_data)

    @staticmethod
    def __create_asset_application(app_config: AppConfigType) -> assetApplicationType:
        """
        Prepare the asset by filling the application input parameters with default values
        Args:
            app_config: A dictionary containing application configuration information
        Returns:
            Filled Application input parameters with default values
        """
        input_list = []
        if "application" in app_config:
            for input_param in cast(app_configApplicationType, app_config["application"]):
                item = {
                    "roles": input_param["roles"],
                    "values": []
                }
                for value in input_param["values"]:
                    value_item = {
                        "name": value["name"],
                        "value": value["default_value"],
                        "scale_value": value["scale_value"]
                    }
                    item["values"].append(value_item)

                input_list.append(item)

        return input_list

    @staticmethod
    def __fill_asset_role_information(network_data: assetNetworkType, app_config: AppConfigType,
                                      node_list: AssetNodeListType) -> None:
        network_data["roles"] = {}
        if "network" in app_config:
            app_config_network: app_configNetworkType = cast(app_configNetworkType, app_config["network"])
            if "roles" in app_config_network:
                for index, role in enumerate(app_config_network["roles"]):
                    network_data["roles"][role] = node_list[index]["slug"]

    def __fill_asset_channel_information(self, channel_list: AssetChannelListType,
                                         templates: Dict[str, Dict[str, Any]]) -> None:
        for channel in channel_list:
            filled_params_channel = []
            for param in channel["parameters"]:
                filled_parameter_item = self.__get_filled_template_parameter(param=param, templates=templates)
                filled_params_channel.append(filled_parameter_item)

            channel["parameters"] = filled_params_channel

    def __fill_asset_node_information(self, node_list: AssetNodeListType, templates: Dict[str, Dict[str, Any]]) -> None:
        for node in node_list:
            filled_params_node = []
            for param in node["node_parameters"]:
                filled_parameter_item = self.__get_filled_template_parameter(param=param, templates=templates)
                filled_params_node.append(filled_parameter_item)

            node["node_parameters"] = filled_params_node

            number_of_qubits = node["number_of_qubits"]
            node["qubits"] = []
            for qubit_number in range(number_of_qubits):
                qubit_item: Dict[str, Any] = {
                    "qubit_id": qubit_number,
                    "qubit_parameters": []
                }
                for param in node["qubit_parameters"]:
                    filled_parameter_item = self.__get_filled_template_parameter(param=param, templates=templates)
                    qubit_item["qubit_parameters"].append(filled_parameter_item)

                node["qubits"].append(qubit_item)

            del node["number_of_qubits"]
            del node["qubit_parameters"]

    def create_asset_network(self, network_data: assetNetworkType, app_config: AppConfigType) -> assetNetworkType:
        """
        Prepare the asset by filling the network parameters with default values

        Args:
            network_data: Network information containing channels and nodes list
            app_config: A dictionary containing application configuration information

        Returns:
            Filled Network parameters with default values

        """

        templates = {template["slug"]: template for template in self.__templates_data["templates"]}
        node_list = network_data["nodes"]
        channel_list = network_data["channels"]

        # Fill roles information
        self.__fill_asset_role_information(network_data, app_config, node_list)

        # Fill channel information (parameters)
        self.__fill_asset_channel_information(channel_list, templates)

        # Fill Nodes information (parameters)
        self.__fill_asset_node_information(node_list, templates)

        return network_data

    @staticmethod
    def __get_filled_template_parameter(param: str, templates: Dict[str, Dict[str, Any]]) -> Dict[str, Any]:
        """
        Prepare the template parameter by filling it with default values

        Args:
            param: Name of the template parameter
            templates: A dictionary containing information for all template parameters

        Returns:
            Filled Template parameter with default values

        """
        filled_parameter_item: Dict[str, Any] = {
            "slug": param,
            "values": []
        }
        template_data_value = templates[param]["values"]
        for val in template_data_value:
            item = {
                "name": val["name"],
                "value": val["default_value"],
                "scale_value": val["scale_value"]
            }
            filled_parameter_item["values"].append(item)

        return filled_parameter_item

    def __copy_input_files_from_application(self, application_name: str, input_directory: Path) -> None:
        """
        Copy the config and src files of the 'application' to the 'input_directory'

        Args:
            application_name: The application name for which the config and source files need to be copied
            input_directory: The destination where application files need to be stored

        """
        application_exists, app_path = self.__config_manager.application_exists(application_name=application_name)
        if application_exists:
            app_path = Path(app_path)
            utils.copy_files(app_path / 'config', input_directory, files_list=self.__get_config_file_names())
            utils.copy_files(app_path / 'src', input_directory,
                             files_list=self.get_application_file_names(app_src_path=app_path / 'src'))

    def is_network_available(self, network_name: str, app_config: AppConfigType) -> bool:
        """
        Check if the network_name is available for use in the application's app_config

        Args:
            network_name: The network name
            app_config: Application Configuration containing the available networks

        Returns:
            bool: True if the given network name is available in application configuration, False otherwise
        """
        network_slug = self._get_network_slug(network_name)
        if network_slug:
            if "network" in app_config:
                app_config_network: app_configNetworkType = cast(app_configNetworkType, app_config["network"])
                if "networks" in app_config_network:
                    if network_slug in app_config_network["networks"]:
                        return True

        return False

    @staticmethod
    def is_valid_experiment_path(experiment_path: Path) -> bool:
        """
        Check if experiment.json exists and we're dealing with an experiment directory
        Args:
            experiment_path: path of experiment

        Returns True when path exists and experiment.json is found
        """
        experiment_json_file = experiment_path / 'experiment.json'
        if experiment_path.is_dir() and experiment_json_file.is_file():
            return True
        return False

    # TODO make a separate class to handle experiment.json" getters and setters
    def is_experiment_local(self, experiment_path: Path) -> bool:
        """
        Check if the experiment at the 'path' is remote or local

        Args:
            experiment_path: The location of the experiment

        Returns:
            bool: True if the experiment at given path is local, False when remote

        Raises:
            ExperimentValueError when not remote or local
        """
        experiment_json_file = experiment_path / 'experiment.json'
        experiment_data = self.get_experiment_data(experiment_path)
        if experiment_data["meta"]["backend"]["location"].strip().lower() == "local":
            return True

        if experiment_data["meta"]["backend"]["location"].strip().lower() != "remote":
            raise ExperimentValueError(f"Experiment backend location should be 'local' or 'remote' in "
                                       f"'{experiment_json_file}'")
        return False

    def get_experiment_id(self, experiment_path: Path) -> Optional[str]:
        """
        Get the experiment id for this experiment (from meta data)

        Args:
            experiment_path: The location of the experiment

        Returns:
            experiment id
        """
        if not self.is_experiment_local(experiment_path):
            experiment_data = self.get_experiment_data(experiment_path)
            if "experiment_id" in experiment_data["meta"]:
                return str(experiment_data["meta"]["experiment_id"])
        return None

    def get_experiment_application(self, experiment_path: Path) -> str:
        """
        Get the application name (slug) for this experiment

        Args:
            experiment_path: The location of the experiment

        Returns:
            str: application slug
        """
        experiment_data = self.get_experiment_data(experiment_path)
        return cast(str, experiment_data["meta"]["application"]["slug"])

    def get_experiment_name(self, experiment_path: Path) -> str:
        """
        Get the name of experiment

        Args:
            experiment_path: The location of the experiment

        Returns:
            str: experiment name
        """
        experiment_data = self.get_experiment_data(experiment_path)
        return cast(str, experiment_data["meta"]["name"])

    def get_experiment_rounds(self, experiment_path: Path) -> int:
        """
        Get the number of rounds in an experiment

        Args:
            experiment_path: The location of the experiment

        Returns:
            int: Value of the number of rounds
        """
        experiment_data = self.get_experiment_data(experiment_path)
        return cast(int, experiment_data["meta"]["number_of_rounds"])

    def get_experiment_asset(self, experiment_path: Path) -> AssetType:
        """
            Get the asset from experiment.json

            Args:
                experiment_path: The location of the experiment

            Returns:
                A dictionary containing the asset information
        """
        experiment_data = self.get_experiment_data(experiment_path)
        return cast(AssetType, experiment_data["asset"])

    def get_experiment_meta(self, experiment_path: Path) -> MetaType:
        """
        Get the meta-data for this experiment

        Args:
            experiment_path: The location of the experiment

        Returns:
            MetaType: meta-structure
        """
        experiment_data = self.get_experiment_data(experiment_path)
        return experiment_data["meta"]

    def get_experiment_round_set(self, experiment_path: Path) -> Optional[str]:
        """
        Get the round set url from experiment.json (stored for remote experiments)

        Args:
            experiment_path: The location of the experiment

        Returns:
            The round set from the experiment.json
        """
        if not self.is_experiment_local(experiment_path):
            experiment_meta = self.get_experiment_meta(experiment_path)
            if "round_set" in experiment_meta:
                return cast(str, experiment_meta["round_set"])
        return None

    @staticmethod
    def get_experiment_data(experiment_path: Path) -> ExperimentDataType:
        """
        Get the data (meta and asset) from experiment.json

        Args:
            experiment_path: The location of the experiment

        Returns:
            A dictionary containing the data information
        """
        experiment_json_file = experiment_path / 'experiment.json'
        # Check if experiment.json exists and we're dealing with an experiment directory
        if experiment_path.is_dir() and experiment_json_file.is_file():
            # Validate experiment.json (does it exist and is valid json according to the schema)
            experiment_schema = Path(os.path.join(BASE_DIR, 'schema', 'experiments', 'experiment.json', ''))
            valid, message = validate_json_schema(experiment_json_file, experiment_schema)
            if valid:
                experiment_data = utils.read_json_file(experiment_json_file)
                return cast(ExperimentDataType, experiment_data)

            raise SchemaError(message)

        raise ExperimentDirectoryNotValid(str(experiment_path))

    @staticmethod
    def set_experiment_id(experiment_id: str, experiment_path: Path) -> None:
        """
        Store the experiment id to experiment.json (stored for remote experiments)

        Args:
            experiment_id: the remote experiment id
            experiment_path: The location of the experiment
        """
        experiment_json_file = experiment_path / 'experiment.json'
        experiment_data = utils.read_json_file(experiment_json_file)
        experiment_data["meta"]["experiment_id"] = experiment_id
        utils.write_json_file(experiment_json_file, experiment_data)

    @staticmethod
    def set_experiment_round_set(round_set_url: str, experiment_path: Path) -> None:
        """
        Store the round set url to experiment.json (stored for remote experiments)

        Args:
            round_set_url: the round set url
            experiment_path: The location of the experiment
        """
        experiment_json_file = experiment_path / 'experiment.json'
        experiment_data = utils.read_json_file(experiment_json_file)
        experiment_data["meta"]["round_set"] = round_set_url
        utils.write_json_file(experiment_json_file, experiment_data)

    @staticmethod
    def set_experiment_asset_application(asset_application: assetApplicationType, experiment_path: Path) -> None:
        """
        Store the asset application to experiment.json

        Args:
            asset_application: the asset application data
            experiment_path: The location of the experiment
        """
        experiment_json_file = experiment_path / 'experiment.json'
        experiment_data = utils.read_json_file(experiment_json_file)
        experiment_data["asset"]["application"] = asset_application
        utils.write_json_file(experiment_json_file, experiment_data)

    def _delete_input(self, experiment_input_path: Path) -> bool:
        """
        Input directory contains inputs from the application and input created for the simulator
        """
        input_dir_deleted = False
        # Delete the config files
        config_files_list = self.__get_config_file_names()
        for config_file in config_files_list:
            file_to_delete = experiment_input_path / config_file
            if file_to_delete.is_file():
                if config_file == 'network.json':
                    # Delete the app files for the roles from network.json from the
                    # experiment/input directory
                    application_file_names = [experiment_input_path / application_file_name for
                                              application_file_name in
                                              self.__get_role_file_names(experiment_input_path)]
                    for app_file in application_file_names:
                        if app_file.is_file():
                            app_file.unlink()

                    simulator_role_files = [experiment_input_path / (simulator_role_file.lower() + '.yaml') for
                                            simulator_role_file in
                                            self.__get_role_names(experiment_input_path)]
                    for simulator_role_file in simulator_role_files:
                        if simulator_role_file.is_file():
                            simulator_role_file.unlink()

                file_to_delete.unlink()

        # delete other yaml files for the simulator
        simulator_file_names = [experiment_input_path / simulator_file_name for simulator_file_name in
                                self.__get_simulator_file_names()]
        for simulator_file in simulator_file_names:
            if simulator_file.is_file():
                simulator_file.unlink()

        try:
            os.rmdir(experiment_input_path)
            input_dir_deleted = True
        except OSError:  # The directory is not empty
            pass

        return input_dir_deleted

    @staticmethod
    def _delete_raw_output(raw_output_path: Path) -> bool:
        """
        Raw output is generated by the simulator. We can safely delete the raw outputs directory
        """
        shutil.rmtree(raw_output_path)

        return True

    @staticmethod
    def _delete_results(result_path: Path) -> bool:
        """
        Results directory contains processed.json
        """
        result_dir_deleted = False
        processed_result_json_file = result_path / 'processed.json'
        if processed_result_json_file.is_file():
            processed_result_json_file.unlink()
        # now try to remove the result directory
        try:
            os.rmdir(result_path)
            result_dir_deleted = True
        except OSError:  # The directory is not empty
            pass

        return result_dir_deleted

    def delete_experiment(self, experiment_name: Optional[str], experiment_path: Path) -> bool:
        """
        Deletes the experiment files.
        When experiment name is None the current directory is taken as experiment path, the experiment files and
        directories are deleted but the current directory cannot be deleted, leaving a trace of the experiment.
        When experiment name is given ./experiment_name is taken as experiment path and the
        experiment_name directory can also be deleted, deleting the complete experiment.
        Only files that belong to an experiment are deleted. When a directory is not empty it is not deleted.

        Args:
            experiment_name: Optional. The experiment directory deleted will be ./experiment_name, otherwise the
            current directory
            experiment_path: The location of the experiment

        Returns:
            True if the complete experiment (including directory experiment_name) was deleted, otherwise false (leaving
            traces of the experiment)

        Raises:
            ExperimentDirectoryNotValid when the experiment path is not recognized as an experiment
        """
        experiment_dir_deleted = False
        all_subdir_deleted = True

        experiment_json_file = experiment_path / 'experiment.json'
        # Check if experiment.json exists and we're dealing with an experiment directory
        if experiment_path.is_dir() and experiment_json_file.is_file():
            experiment_input_path = experiment_path / 'input'
            if experiment_input_path.is_dir():
                all_subdir_deleted = self._delete_input(experiment_input_path) and all_subdir_deleted

            experiment_raw_output_path = experiment_path / 'raw_output'
            if experiment_raw_output_path.is_dir():
                all_subdir_deleted = self._delete_raw_output(experiment_raw_output_path) and all_subdir_deleted

            experiment_results_path = experiment_path / 'results'
            if experiment_results_path.is_dir():
                all_subdir_deleted = self._delete_results(experiment_results_path) and all_subdir_deleted

            # Delete experiment.json
            experiment_json_file.unlink()

            # only when we called experiment delete from the parent directory and all the subdirectories were
            # removed try to remove experiment dir
            if all_subdir_deleted and experiment_name is not None:
                try:
                    os.rmdir(experiment_path)
                    experiment_dir_deleted = True
                except OSError:  # The directory is not empty
                    pass
        else:
            raise ExperimentDirectoryNotValid(str(experiment_path))

        return all_subdir_deleted and experiment_dir_deleted

    def run_experiment(self, experiment_path: Path, update: bool, timeout: Optional[int] = None) -> List[ResultType]:
        """
        An experiment is run on the backend.
        The application input files are copied for each run, they may have changed
        - Refresh ["asset"]["application"] when application.json changed
        Then the round set manager is set up and called to process the asset

        Args:
            experiment_path: The location of the experiment
            update: Update the application files before running the experiment
            timeout: Limit the wait for result

        Returns:
            A list containing the results of the run
        """
        if update:
            self.__prepare_input_files(experiment_path)
        local_round_set: RoundSetType = {"url": "local"}
        experiment_meta = self.get_experiment_meta(experiment_path)
        if experiment_meta['backend']['type'] == "NetSquid simulator":
            round_set_manager = RoundSetManager(round_set=local_round_set,
                                            asset=self.get_experiment_asset(experiment_path),
                                            experiment_path=experiment_path)
        elif experiment_meta['backend']['type'] == "Vanilla NetSquid simulator":
            round_set_manager = VanillaNetSquidRoundSetManager(round_set=local_round_set,
                                            asset=self.get_experiment_asset(experiment_path),
                                            experiment_path=experiment_path)
        results = round_set_manager.process(timeout)
        return results

    def __prepare_input_files(self, experiment_path: Path) -> None:
        """
        The application config and src files are copied for the experiment run, they may have changed
        - Refresh ["asset"]["application"] in experiment.json when application.json changed

        Args:
            experiment_path: The location of the experiment

        """
        application_name = self.get_experiment_application(experiment_path)
        _, app_path = self.__config_manager.application_exists(application_name=application_name)
        experiment_input_path = experiment_path / 'input'
        application_app = Path(app_path) / 'config' / 'application.json'
        application_exp = experiment_input_path / 'application.json'
        if application_app.exists() and application_exp.exists():
            application_changed = not filecmp.cmp(str(application_app),
                                                  str(application_exp),
                                                  shallow=False)
            if application_changed:
                application_config = self.get_application_config(application_name)
                if application_config:
                    asset_application = self.__create_asset_application(application_config)
                    self.set_experiment_asset_application(asset_application, experiment_path)
        self.__copy_input_files_from_application(application_name, experiment_input_path)

    @staticmethod
    def get_results(experiment_path: Path) -> List[ResultType]:
        """ Get the result from the output directory

        Args:
            experiment_path: The location of the experiment

        Returns:
            List of results (currently only from round_number 1)
        """
        # TODO: is this method used?
        output_converter = OutputConverter(
            round_set={"url": "local"},
            log_dir=str(experiment_path / 'raw_output'),
            output_dir='LAST',
            instruction_converter=FullyConnectedNetworkGenerator()
        )

        result = output_converter.convert(round_number=1)
        return [result]

    def validate_experiment(self, experiment_path: Path, error_dict: ErrorDictType) -> None:
        """
        Validates the experiment by checking:
        - if the structure is correct and consists of an experiment.json
        - (For local run) experiment directory contains an input directory with the correct files
        - content of experiment.json is valid JSON
        - asset in the experiment.json validated against a schema validator.
        - if the network used in experiment.json is existing
        - if the nodes and channels used in experiment.json are correct and valid for that network

        Args:
            experiment_path: The location of the experiment
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        local = self.is_experiment_local(experiment_path=experiment_path)

        self._validate_experiment_json(experiment_path=experiment_path, error_dict=error_dict)
        if local:
            self._validate_experiment_input(experiment_path=experiment_path, error_dict=error_dict)

    def _validate_experiment_json(self, experiment_path: Path, error_dict: ErrorDictType) -> None:
        """
        This function validates if experiment.json contains valid json and if it passes schema validation.

        Args:
            experiment_path: The location of the experiment
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        experiment_json_file = experiment_path / 'experiment.json'

        # Validate experiment.json (does it exist and is valid json according to the schema)
        experiment_schema = Path(os.path.join(BASE_DIR, 'schema', 'experiments', 'experiment.json', ''))
        valid, message = validate_json_schema(experiment_json_file, experiment_schema)
        if not valid:
            error_dict["error"].append(message)
        else:
            experiment_data = self.get_experiment_data(experiment_path)
            self._validate_experiment_backend(experiment_json_file, experiment_data, error_dict)
            # slug is now also a required field
            experiment_network_slug = experiment_data["asset"]["network"]["slug"]
            # Check if the chosen network exists
            if self._get_network_info(experiment_network_slug) is not None:
                # Validate experiment nodes
                self._validate_experiment_nodes(experiment_json_file, experiment_data, error_dict)
                # Validate experiment channels
                self._validate_experiment_channels(experiment_json_file, experiment_data, error_dict)
                # Validate experiment roles
                self._validate_experiment_roles(experiment_path, experiment_data, error_dict)
            else:
                error_dict["warning"].append(
                    f"In file '{experiment_json_file}': network '{experiment_network_slug}' "
                    f"does not exist")

            self._validate_experiment_application(experiment_path, experiment_data, error_dict)

    def __check_experiment_input_role_files(self, experiment_input_path: Path, error_dict: ErrorDictType) -> None:
        # Check if the app_<role>.py files for the roles from network.json exist in the
        # experiment/input directory
        role_file_names = self.__get_role_file_names(experiment_input_path)
        for role_file_name in role_file_names:
            if not (experiment_input_path / role_file_name).is_file():
                error_dict["error"].append(f"'{experiment_input_path}' is missing the file: "
                                           f"'{role_file_name}'")

    def __check_all_experiment_input_files_exist(self, experiment_input_path: Path, error_dict: ErrorDictType) -> None:
        for file in self.__get_config_file_names():
            if (experiment_input_path / file).is_file():
                app_schema_path = Path(os.path.join(BASE_DIR), 'schema', 'applications', '')
                valid, message = validate_json_schema(experiment_input_path / file, app_schema_path / file)
                if valid:
                    if file == 'network.json':
                        self.__check_experiment_input_role_files(experiment_input_path, error_dict)
                else:
                    error_dict["error"].append(message)
            else:
                error_dict["error"].append(f"'{experiment_input_path}' should contain the file '{file}'")

    def _validate_experiment_input(self, experiment_path: Path, error_dict: ErrorDictType) -> None:

        """
        Validates if the experiment file structures input directory containing a:
        - network.json, application.json, result.json, app_role1.py, app_role2.py, ...
        Validates the roles used in experiment if they are in input network.json from application

        Args:
            experiment_path: The location of the experiment
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        experiment_input_path = experiment_path / 'input'

        if experiment_input_path.is_dir():
            self.__check_all_experiment_input_files_exist(experiment_input_path, error_dict)
            self._validate_application_roles(experiment_path, error_dict)
        else:
            error_dict["error"].append(f"Required directory not found: '{experiment_input_path}'")

    def _validate_application_roles(self, experiment_path: Path, error_dict: ErrorDictType) -> None:
        """
        Validate if the roles information available in the network -> roles section contains:
            - valid name for roles (are application roles defined in network.json)

        Args:
            experiment_path: The location of the experiment directory
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        # Check if experiment is local or remote
        experiment_data = self.get_experiment_data(experiment_path)
        experiment_roles = experiment_data["asset"]["network"]["roles"]
        application_roles = self.__get_role_names(experiment_path / 'input')

        for role, _ in experiment_roles.items():
            if role not in application_roles:
                error_dict["error"].append(f"In file '{experiment_path / 'experiment.json'}': role '{role}' is not"
                                           f" valid for the application")

    def _validate_experiment_backend(self, experiment_file_path: Path, experiment_data: Dict[str, Any], error_dict:
                                     ErrorDictType) -> None:
        """
        Validate if the backend properties are valid. Backend property location must be local or remote.

        Args:
            experiment_file_path: The location of the experiment.json file
            experiment_data: contents of the experiment.json file
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        # Check if experiment backend location is local or remote
        # location is required field in schema
        location = experiment_data["meta"]["backend"]["location"].strip().lower()
        if location not in ["local", "remote"]:
            error_dict["warning"].append(f"In file '{experiment_file_path}': only 'local' or 'remote' is supported "
                                         f"for backend property 'location'")
        if location == "local":
            # local backend must be one of the supported backends
            if experiment_data["meta"]["backend"]["type"].strip().lower() not in [s.strip().lower() for s in SUPPORTED_BACKEND_TYPES]:
                error_dict["warning"].append(f"In file '{experiment_file_path}': local backend must "
                                             f"be {DEFAULT_BACKEND_TYPE}")

    def _validate_experiment_nodes(self, experiment_file_path: Path, experiment_data: Dict[str, Any], error_dict:
                                   ErrorDictType) -> None:
        """
        Validate if the amount of nodes (defined in the experiment.json file) are valid for 'network_slug' and if
        all the nodes exist and belong to this network. Validate if the parameters for node and qubits are valid and
        within range of minimum and maximum values

        Args:
            experiment_file_path: The location of the experiment.json file
            experiment_data: contents of the experiment.json file
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        experiment_network_slug = experiment_data["asset"]["network"]["slug"]

        # Check if the amount of nodes is valid for this network
        experiment_nodes = experiment_data["asset"]["network"]["nodes"]

        all_network_nodes = self._get_network_nodes()
        network_nodes = all_network_nodes[experiment_network_slug]
        if len(experiment_nodes) > len(network_nodes):
            error_dict["error"].append(f"In file '{experiment_file_path}': too many nodes used in network "
                                       f"'{experiment_network_slug}'. Maximum amount of nodes that can be used: "
                                       f"{len(network_nodes)}")

        # Check if all nodes exist and belong to this network
        for node in experiment_nodes:
            if node["slug"] not in network_nodes:
                error_dict["error"].append(f"In file '{experiment_file_path}': node '{node['slug']}' does not exist "
                                           f"or does not belong to the network '{experiment_network_slug}'")
            else:
                # check if node params are valid and their value is within range
                self._validate_template_parameters(entity="node", entity_slug=node["slug"],
                                                   entity_params=node["node_parameters"],
                                                   experiment_file_path=experiment_file_path,
                                                   error_dict=error_dict)

                # check if qubit params are valid and their value is within range
                for qubit in node["qubits"]:
                    self._validate_template_parameters(entity="node " + node["slug"] + " qubit",
                                                       entity_slug=str(qubit["qubit_id"]),
                                                       entity_params=qubit["qubit_parameters"],
                                                       experiment_file_path=experiment_file_path,
                                                       error_dict=error_dict)

    def _validate_experiment_channels(self, experiment_file_path: Path, experiment_data: Dict[str, Any], error_dict:
                                      ErrorDictType) -> None:
        """
        Validate if the amount of channels (defined in the experiment.json file) are valid for 'network_slug' and if
        all the channels exist and belong to this network. Validate if the node1 and node2 properties for the channel
        are valid node names. Validate if the parameters & their values are valid and within the range of maximum and
        minimum as defined for each parameter

        Args:
            experiment_file_path: The location of the experiment.json file
            experiment_data: contents of the experiment.json file
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        # Check if the amount of channels are valid for this network
        experiment_network_slug = experiment_data["asset"]["network"]["slug"]
        experiment_channels = experiment_data["asset"]["network"]["channels"]
        network_channels = self._get_channels_for_network(network_slug=experiment_network_slug)
        if network_channels is not None:
            if len(experiment_channels) > len(network_channels):
                error_dict["error"].append(f"In file {experiment_file_path}: too many channels used in network "
                                           f"'{experiment_network_slug}'. Maximum amount of channels that can be used: "
                                           f"{len(network_channels)}")

            # Check if the channels exist and belong to this network
            for channel in experiment_channels:
                if not channel["slug"] in network_channels:
                    error_dict["error"].append(f"In file '{experiment_file_path}': channel '{channel['slug']}' does "
                                               f"not exist or is not a valid channel for "
                                               f"network '{experiment_network_slug}'")
                else:
                    # check node1 and node2 are valid nodes for the selected network
                    expected_channel_info = self._get_channel_info(channel["slug"])

                    for node in ["node1", "node2"]:
                        if expected_channel_info and channel[node] != expected_channel_info[node]:
                            error_dict["error"].append(
                                f"In file '{experiment_file_path}': value '{channel[node]}' of node '{node}' in channel"
                                f" '{channel['slug']}' does not exist or is not a valid node for the channel")
                    # check parameters in channel are valid and their value is within max and min range
                    self._validate_template_parameters(entity="channel", entity_slug=channel["slug"],
                                                       entity_params=channel["parameters"],
                                                       experiment_file_path=experiment_file_path,
                                                       error_dict=error_dict)
        else:
            error_dict["error"].append(f"No channels found for network '{experiment_network_slug}'")

    def _validate_template_parameters(self, entity: str, entity_slug: str, entity_params: List[Dict[str, Any]],
                                      experiment_file_path: Path, error_dict: ErrorDictType) -> None:
        """
        Validate the template parameters by checking:
         - if the type of value is valid (integer or float)
         - the value is within the range specified by the max and min value for the parameter

        Args:
            entity: The entity to which parameters belong to
            entity_slug: The slug to identify the entity
            entity_params: A dictionary containing the parameters to be validated
            experiment_file_path: The location of the experiment.json file
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        param_templates = self._get_templates()
        param_max_min_dict = self._get_template_params_max_min_range()

        for param in entity_params:  # pylint: disable=R1702 too-many-nested-blocks
            if param["slug"] in param_templates:
                for value in param["values"]:
                    if value["name"] in param_max_min_dict[param["slug"]]:
                        min_val = param_max_min_dict[param["slug"]][value['name']]['minimum_value']
                        max_val = param_max_min_dict[param["slug"]][value['name']]['maximum_value']
                        val = value["value"]
                        if isinstance(val, (int, float)):
                            if val < min_val or val > max_val:
                                error_dict["error"].append(
                                    f"In file '{experiment_file_path}': value '{val}' of param"
                                    f" '{param['slug']}' -> '{value['name']}' in {entity} '{entity_slug}'"
                                    f" is not within the allowed range of minimum ({min_val}) and maximum ({max_val})")
                        else:
                            error_dict["error"].append(
                                f"In file '{experiment_file_path}': value '{val}' of param"
                                f" '{param['slug']}' -> '{value['name']}' in {entity} '{entity_slug}'"
                                f" is not of the required type (integer or float)")

                    else:
                        error_dict["error"].append(
                            f"In file '{experiment_file_path}': '{value['name']}' is not valid for param"
                            f" '{param['slug']}' in {entity} '{entity_slug}'")
            else:
                error_dict["error"].append(
                    f"In file '{experiment_file_path}': parameter '{param['slug']}' in {entity}"
                    f" '{entity_slug}' does not exist")

    def _validate_experiment_roles(self, experiment_path: Path, experiment_data: Dict[str, Any],
                                   error_dict: ErrorDictType) -> None:
        """
        Validate if the roles information available in the network -> roles section contains:
            - valid name for assigned nodes
            - No duplicate nodes

        Args:
            experiment_path: The location of the experiment directory
            experiment_data: contents of the experiment.json file
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """
        experiment_roles = experiment_data["asset"]["network"]["roles"]

        experiment_network_slug = experiment_data["asset"]["network"]["slug"]
        all_network_nodes = self._get_network_nodes()
        network_nodes = all_network_nodes[experiment_network_slug]

        nodes_used = list(experiment_roles.values())
        duplicate_nodes = []

        for role, node in experiment_roles.items():
            if node not in network_nodes:
                error_dict["error"].append(f"In file '{experiment_path / 'experiment.json'}': node '{node}' used for"
                                           f" role '{role}' is not valid for the application")
            if nodes_used.count(node) > 1:
                duplicate_nodes.append(node)

        for item in set(duplicate_nodes):
            error_dict["error"].append(f"In file '{experiment_path / 'experiment.json'}': node '{item}' is used for"
                                       f" multiple roles")

    @staticmethod
    def _validate_experiment_application(experiment_path: Path, experiment_data: Dict[str, Any],
                                         error_dict: ErrorDictType) -> None:
        """
        Validate the ['application'] key defined in the asset of experiment.json. Check if the roles match the roles
        that are defined in input/network.json

        Args:
            experiment_path: The location of the experiment
            experiment_data: contents of the experiment.json file
            error_dict: Dictionary containing error and warning messages of the validations that failed
        """

        experiment_application_data = experiment_data["asset"]["application"]
        experiment_input_path = experiment_path / 'input'

        # Check if the roles defined in experiment.json ['application'] match the roles defined in input/network.json
        if (experiment_input_path / 'network.json').is_file():
            try:
                application_network_data = utils.read_json_file(experiment_input_path / 'network.json')
                application_roles = application_network_data["roles"] if "roles" in application_network_data else []
                for experiment_application_item in experiment_application_data:
                    experiment_roles = experiment_application_item["roles"]
                    if not set(experiment_roles).issubset(application_roles):
                        error_dict["warning"].append(f"In file '{experiment_path / 'experiment.json'}': not all "
                                                     f"experiment roles {experiment_roles} are defined as application "
                                                     f"roles {application_roles} in "
                                                     f"'{experiment_input_path / 'network.json'}'")
            except MalformedJsonFile:
                # The file 'network.json' will be checked against the schema in validate_experiment_input
                pass

    def list_networks(self) -> List[Dict[str, Any]]:
        """
        List the local networks.

        Returns:
            A list of networks
        """
        return self._get_networks()
