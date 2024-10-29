from datetime import datetime, timezone
from functools import lru_cache
import re
from pathlib import Path
from typing import Any, cast, Dict, List, Optional, Tuple, Union
from urllib.parse import urljoin, urlsplit, urlunsplit, parse_qs

import jwt
import requests
from requests.models import Response
from requests.auth import AuthBase, HTTPBasicAuth

from apistar import Client
from apistar.client.auth import TokenAuthentication
from apistar.exceptions import ErrorResponse, ClientError

from adk.exceptions import ApiClientError, NotLoggedIn
from adk.managers.auth_manager import AuthManager
from adk.parsers.encoders import JSONEncoder
from adk.type_aliases import (ActionsType, ParametersType, TemplateType, NodeType, ChannelType, NetworkType,
                              ApplicationType, AppVersionType, AppSourceType, AppConfigType, AppResultType,
                              RoundSetType, AssetType, ExperimentType, ResultType, FinalResultType, BackendType,
                              NetworkListType, UserType, BackendTypeType, TokenType, AppSourceFilesType)


class ApiStarClient(Client):  # type: ignore
    """ Fix from https://github.com/encode/apistar/issues/657 """
    def __init__(self, *args: Optional[Any], base_url: Optional[str] = None, **kwargs: Optional[Any]) -> None:
        # Let apistar do its parsing
        super().__init__(*args, **kwargs)

        # Strip scheme, hostname and absolute path from all link URLs
        for link_info in self.document.walk_links():
            original_url = urlsplit(link_info.link.url)
            new_url = ('', '', *original_url[2:])
            link_info.link.url = urlunsplit(new_url).lstrip('/')

        if base_url:
            # Ensure the base URL ends with a slash to prevent issues:
            # urljoin('http://a/b', 'c') → http://a/c
            # urljoin('http://a/b/', 'c') → http://a/b/c
            if not base_url.endswith('/'):
                base_url += '/'

            self.document.url = base_url


class QneClient:
    """Client to connect to the api-router.

    A client to make a connection to the api-router via OpenAPI. For each user a specific client is created with user
    credentials.

    Args:
        auth_manager: authentication manager
    """
    def __init__(self, auth_manager: AuthManager) -> None:
        self.__auth_manager = auth_manager
        self.__base_uri = self.__auth_manager.get_active_host()
        self.__email: Optional[str] = self.__auth_manager.get_email(self.__base_uri)
        self.__password: Optional[str] = self.__auth_manager.get_password(self.__base_uri)
        self.__use_username: Optional[bool] = self.__auth_manager.get_use_username(self.__base_uri)
        self.__refresh_token: Optional[str] = self.__auth_manager.load_token(self.__base_uri)

        self._headers: Dict[str, str] = {}
        self.__openapi_client_class = ApiStarClient
        self.__client: Optional[ApiStarClient] = None

    def _set_open_api_client(self, auth: Optional[AuthBase] = None) -> None:
        """Sets or updates the open api client mainly because of access tokens changing.

        The reason we do not override __client is because _call_with_retries might be "keeping" a reference
        to the previous in callable_. For example, if we reached here because of an access token refresh
        the callable_ still holds the action that raised the initial 401 with a reference of __client with
        an invalid access token. If we don't "fix" that reference the retried action will raise a 401 again.
        """
        encoders = [JSONEncoder]

        if self.__client:
            self.__client.transport = self.__client.init_transport(encoders=encoders,
                                                                   headers=self._headers,
                                                                   auth=auth)
        else:
            schema_url = urljoin(self.__base_uri, 'schema/')
            schema = self._client_get(schema_url, headers=self._headers).json()
            self.__client = self.__openapi_client_class(base_url=self.__base_uri,
                                                        schema=schema,
                                                        encoders=encoders,
                                                        headers=self._headers,
                                                        auth=auth)

    def _refresh_token_expired(self) -> None:
        """Checks and sets to None the refresh token if it is expired."""

        if not self.__refresh_token:
            return

        decoded = jwt.decode(self.__refresh_token, options={"verify_signature": False})
        exp = int(decoded['exp'])
        # https://github.com/jpadilla/pyjwt/issues/321#issuecomment-354126200
        now = int(datetime.utcnow().replace(tzinfo=timezone.utc).timestamp())

        if exp <= now:
            self.__refresh_token = None

    def _authentication_access_token(self) -> str:
        """Get the JWT access token for the user either by authenticating with the provided credentials or using the
        refresh token from earlier authentication.
        """

        self._refresh_token_expired()

        jwt_url = urljoin(self.__base_uri, 'jwt/')

        if self.__refresh_token:
            jwt_url = urljoin(jwt_url, 'refresh/')
            payload = {'refresh': self.__refresh_token}
        else:
            assert self.__email is not None
            assert self.__password is not None
            if self.__use_username:
                payload = {
                    'username': self.__email,
                    'password': self.__password
                }
            else:
                payload = {
                    'email': self.__email,
                    'password': self.__password
                }

        response = self._client_post(jwt_url, data=payload).json()
        self.__refresh_token = response.get("refresh", self.__refresh_token)
        assert self.__refresh_token is not None
        self.__auth_manager.set_token(self.__base_uri, self.__refresh_token)

        return str(response['access'])

    def _authenticate(self) -> None:

        self._headers = {}
        access_token = self._authentication_access_token()
        self._headers = {'Authorization': f'JWT {access_token}'}

        auth_mech = TokenAuthentication(access_token, scheme="JWT")
        self._set_open_api_client(auth_mech)

    def login(self, email: str, password: str, host: str, use_username: bool) -> str:
        # pylint: disable=R0801
        self.__refresh_token = None
        self.__base_uri = host
        self.__email = email
        self.__password = password
        self.__use_username = use_username

        self._authenticate()
        assert self.__refresh_token is not None
        return self.__refresh_token

    def logout(self, host: str) -> None:
        self.__client = None
        self.__base_uri = self.__auth_manager.get_active_host()
        self.__email = None
        self.__password = None
        self.__use_username = None

    def is_logged_in(self) -> bool:
        if self.__client is None:
            if self.__email is None or self.__password is None:
                return False
        return True

    @staticmethod
    def _client_get(url: str, **params: ParametersType) -> Any:
        result = requests.get(url, timeout=10, **params)  # type: ignore
        if isinstance(result, Response):
            result.raise_for_status()
        return result

    @staticmethod
    def _client_post(url: str, **params: ParametersType) -> Any:
        result = requests.post(url, timeout=10, **params)  # type: ignore
        if isinstance(result, Response):
            result.raise_for_status()
        return result

    def _action(self, operation_id: ActionsType, **params: ParametersType) -> Any:
        if self.__client is None:
            if self.__email is not None and self.__password is not None:
                self._authenticate()
            else:
                raise NotLoggedIn()
        assert self.__client is not None
        try:
            return self.__client.request(operation_id, **params)
        except ClientError as error:
            message_text = ''
            for message in error.messages:
                message_text += f"API ClientError ({message.code}): " \
                                f"{message.text} {str(message.index) if message.index is not None else ''}\n"
            raise ApiClientError(message_text)  # pylint: disable=W0707
        except ErrorResponse as error:
            if error.status_code != 401:
                message_text = f"API ClientError ({error.status_code}): {error.content}"
                raise ApiClientError(message_text)  # pylint: disable=W0707

            self._authenticate()
            return self.__client.request(operation_id, **params)

    @staticmethod
    def _cast_parameter_type(param_set1: Dict[str, Any],
                             param_set2: Optional[Dict[str, Any]] = None) -> ParametersType:
        """Helper function that merges and casts two dictionaries into a proper parameter dictionary.

        Args:
            param_set1: Set of parameters to be send to the api-router.
            param_set2: Optional set of parameters.

        Returns:
            To parameters_type cast set of parameters.
        """
        if param_set2 is None:
            param_set2 = {}
        return cast(ParametersType, {**param_set1, **param_set2})

    @property
    def base_uri(self) -> str:
        return self.__base_uri

    @property
    def email(self) -> Optional[str]:
        return self.__email

    @property
    def password(self) -> Optional[str]:
        return self.__password

    @staticmethod
    def parse_url(url: str) -> Tuple[str, str]:
        """Parse an API url to extract the resource type and id.

        Example: parse_url("http://localhost/api/backends/1/") returns the tuple ("backends", "1").

        Args:
            url: the URL to parse.

        Returns:
            A tuple of the type of endpoint and the corresponding id.
        """
        matches = re.match(r'.*/([^/]+)/([0-9]+)/', url)
        if matches is None:
            raise ValueError("unable to parse url")
        return matches.group(1), matches.group(2)


class QneFrontendClient(QneClient):  # pylint: disable-msg=R0904
    """
        For testing front end functionality.
        All possible endpoints are implemented which can be reached by a front end.
    """
    def create_token(self) -> TokenType:
        response = self._action('createToken')
        return cast(TokenType, response)

    def retrieve_user(self) -> UserType:
        response = self._action('retrieveMeAPIUser')
        return cast(UserType, response)

    @staticmethod
    def __get_query_params(url: str) -> Tuple[Union[str, Any], Union[str, Any]]:
        """
        Given a URL, get limit and offset parameters of the URL, and return them.
        """
        limit = ''
        offset = ''
        (_, _, _, query, _) = urlsplit(url)
        query_dict = parse_qs(query, keep_blank_values=True)
        if "limit" in query_dict:
            limit = query_dict["limit"][0]
        if "offset" in query_dict:
            offset = query_dict["offset"][0]

        return limit, offset

    def list_applications(self) -> List[ApplicationType]:
        """
        Get the applications. Currently this method supports paginated and non paginated results to be backwards
        compatible. The application data fields that are used in ADK is unchanged.
        """
        response = self._action('listApplications')
        if isinstance(response, list):
            return cast(List[ApplicationType], response)

        application_list: List[ApplicationType] = []
        application_list.extend(response['applications'])
        while response['next'] is not None:
            limit, offset = self.__get_query_params(response['next'])
            response = self._action('listApplications', limit=limit, offset=offset)
            application_list.extend(response['applications'])

        assert len(application_list) == response['total_applications']
        return application_list

    def retrieve_application(self, application_url: str) -> ApplicationType:
        _, application_id = QneClient.parse_url(application_url)
        response = self._action('retrieveApplication', id=application_id)
        return cast(ApplicationType, response)

    def destroy_application(self, application_id: str) -> None:
        self._action('destroyApplication', id=application_id)

    def partial_update_application(self, application_id: str, application: ApplicationType) -> ApplicationType:
        params = self._cast_parameter_type({
            'name': application['name'],
            'description': application['description']
        })
        response = self._action('partialUpdateApplication', id=application_id, application=params)
        return cast(ApplicationType, response)

    def create_application(self, application: ApplicationType) -> ApplicationType:
        params = self._cast_parameter_type(application)
        response = self._action('createApplication', application=params)
        return cast(ApplicationType, response)

    def partial_update_app_version(self, app_version_url: str, app_version: AppVersionType) -> AppVersionType:
        _, app_version_id = QneClient.parse_url(app_version_url)
        params = self._cast_parameter_type({
            'application': app_version['application'],
            'is_disabled': app_version['is_disabled']
        })
        response = self._action('partialUpdateAppVersion', id=app_version_id, appversion=params)
        return cast(AppVersionType, response)

    def create_app_version(self, app_version: AppVersionType) -> AppVersionType:
        params = self._cast_parameter_type(app_version)
        response = self._action('createAppVersion', appversion=params)
        return cast(AppVersionType, response)

    def create_app_config(self, app_config: AppConfigType) -> AppConfigType:
        params = self._cast_parameter_type(app_config)
        response = self._action('createAppConfig', appconfig=params)
        return cast(AppConfigType, response)

    def create_app_result(self, app_result: AppResultType) -> AppResultType:
        params = self._cast_parameter_type(app_result)
        response = self._action('createAppResult', appresult=params)
        return cast(AppResultType, response)

    def create_app_source(self, app_source_files: AppSourceFilesType) -> AppSourceType:
        """
        Upload source files for an application to the api-router. This uses an alternative approach because of
        the file that has to be uploaded.
        """
        app_source_url = urljoin(self.base_uri, 'app-sources/')
        if self.email is None or self.password is None:
            raise NotLoggedIn()
        auth = HTTPBasicAuth(self.email, self.password)
        response = self._client_post(url=app_source_url, files=app_source_files, auth=auth)
        return cast(AppSourceType, response.json())

    def app_versions_application(self, application_url: str) -> List[AppVersionType]:
        _, application_id = QneClient.parse_url(application_url)
        response = self._action('appVersionsApplication', id=application_id)
        return cast(List[AppVersionType], response)

    def app_config_application(self, application_url: str) -> AppConfigType:
        _, application_id = QneClient.parse_url(application_url)
        response = self._action('appConfigApplication', id=application_id)
        return cast(AppConfigType, response)

    def app_result_application(self, application_url: str) -> AppResultType:
        _, application_id = QneClient.parse_url(application_url)
        response = self._action('appResultApplication', id=application_id)
        return cast(AppResultType, response)

    def app_source_application(self, application_url: str) -> AppSourceType:
        _, application_id = QneClient.parse_url(application_url)
        response = self._action('appSourceApplication', id=application_id)
        return cast(AppSourceType, response)

    def retrieve_appversion(self, appversion_url: str) -> AppVersionType:
        _, appversion_id = QneClient.parse_url(appversion_url)
        response = self._action('retrieveAppVersion', id=appversion_id)
        return cast(AppVersionType, response)

    def app_config_appversion(self, appversion_url: str) -> AppConfigType:
        _, appversion_id = QneClient.parse_url(appversion_url)
        response = self._action('appConfigAppVersion', id=appversion_id)
        return cast(AppConfigType, response)

    def app_result_appversion(self, appversion_url: str) -> AppResultType:
        _, appversion_id = QneClient.parse_url(appversion_url)
        response = self._action('appResultAppVersion', id=appversion_id)
        return cast(AppResultType, response)

    def app_source_appversion(self, appversion_url: str) -> AppSourceType:
        _, appversion_id = QneClient.parse_url(appversion_url)
        response = self._action('appSourceAppVersion', id=appversion_id)
        return cast(AppSourceType, response)

    def retrieve_appconfig(self, appconfig_url: str) -> AppConfigType:
        _, appconfig_id = QneClient.parse_url(appconfig_url)
        response = self._action('retrieveAppConfig', id=appconfig_id)
        return cast(AppConfigType, response)

    def retrieve_appresult(self, appresult_url: str) -> AppResultType:
        _, appresult_id = QneClient.parse_url(appresult_url)
        response = self._action('retrieveAppResult', id=appresult_id)
        return cast(AppResultType, response)

    def create_asset(self, asset: AssetType) -> AssetType:
        params = self._cast_parameter_type(asset)
        response = self._action('createAsset', asset=params)
        return cast(AssetType, response)

    def retrieve_asset(self, asset_url: str) -> AssetType:
        _, asset_id = QneClient.parse_url(asset_url)
        response = self._action('retrieveAsset', id=asset_id)
        return cast(AssetType, response)

    def update_asset(self, asset_url: str, asset: AssetType) -> AssetType:
        _, asset_id = QneClient.parse_url(asset_url)
        params = self._cast_parameter_type(asset)
        response = self._action('updateAsset', id=asset_id, asset=params)
        return cast(AssetType, response)

    def partial_update_asset(self, asset_url: str, asset: AssetType) -> AssetType:
        _, asset_id = QneClient.parse_url(asset_url)
        params = self._cast_parameter_type({
            'network': asset['network'],
            'application': asset['application']
        })
        response = self._action('partialUpdateAsset', id=asset_id, asset=params)
        return cast(AssetType, response)

    def list_default_backendtypes(self) -> BackendTypeType:
        response = self._action('listDefaultBackendTypes')
        return cast(BackendTypeType, response)

    @lru_cache
    def list_backendtypes(self) -> List[BackendTypeType]:
        response = self._action('listBackendTypes')
        return cast(List[BackendTypeType], response)

    def retrieve_backendtypes(self, backendtype_url: str) -> BackendTypeType:
        _, backendtype_id = QneClient.parse_url(backendtype_url)
        response = self._action('retrieveBackendType', id=backendtype_id)
        return cast(BackendTypeType, response)

    def list_backends(self) -> List[BackendType]:
        response = self._action('listBackends')
        return cast(List[BackendType], response)

    def retrieve_backend(self, backend_url: str) -> BackendType:
        _, backend_id = QneClient.parse_url(backend_url)
        response = self._action('retrieveBackend', id=backend_id)
        return cast(BackendType, response)

    def list_backends_networks(self) -> List[Any]:
        response = self._action('listBackendsNetworks')
        return cast(List[Any], response)


    def list_experiments(self) -> List[ExperimentType]:
        response = self._action('listExperiments')
        return cast(List[ExperimentType], response)

    def create_experiment(self, experiment: ExperimentType) -> ExperimentType:
        params = self._cast_parameter_type(experiment)
        response = self._action('createExperiment', experiment=params)
        return cast(ExperimentType, response)

    def retrieve_experiment(self, experiment_url: str) -> ExperimentType:
        _, experiment_id = QneClient.parse_url(experiment_url)
        response = self._action('retrieveExperiment', id=experiment_id)
        return cast(ExperimentType, response)

    def update_experiment(self, experiment_url: str, experiment: ExperimentType) -> ExperimentType:
        _, experiment_id = QneClient.parse_url(experiment_url)
        params = self._cast_parameter_type(experiment)
        response = self._action('updateExperiment', id=experiment_id, experiment=params)
        return cast(ExperimentType, response)

    def partial_update_experiment(self, experiment_url: str, experiment: ExperimentType) -> ExperimentType:
        _, experiment_id = QneClient.parse_url(experiment_url)
        params = self._cast_parameter_type({
            'personal_note': experiment['personal_note'],
            'is_marked': experiment['is_marked']
        })
        response = self._action('partialUpdateExperiment', id=experiment_id, experiment=params)
        return cast(ExperimentType, response)

    def destroy_experiment(self, experiment_id: str) -> None:
        self._action('destroyExperiment', id=experiment_id)

    def assets_latest_experiment(self, experiment_url: str) -> AssetType:
        _, experiment_id = QneClient.parse_url(experiment_url)
        response = self._action('assetsLatestExperiment', id=experiment_id)
        return cast(AssetType, response)

    def final_results_latest_experiment(self, experiment_url: str) -> FinalResultType:
        _, experiment_id = QneClient.parse_url(experiment_url)
        response = self._action('finalResultsLatestExperiment', id=experiment_id)
        return cast(FinalResultType, response)

    def results_experiments(self, experiment_url: str) -> List[ResultType]:
        _, experiment_id = QneClient.parse_url(experiment_url)
        response = self._action('resultsExperiment', id=experiment_id)
        return cast(List[ResultType], response)

    def round_sets_experiment(self, experiment_url: str) -> List[RoundSetType]:
        _, experiment_id = QneClient.parse_url(experiment_url)
        response = self._action('roundSetsExperiment', id=experiment_id)
        return cast(List[RoundSetType], response)

    def round_sets_latest_experiment(self, experiment_url: str) -> RoundSetType:
        _, experiment_id = QneClient.parse_url(experiment_url)
        response = self._action('roundSetsLatestExperiment', id=experiment_id)
        return cast(RoundSetType, response)

    def list_roundsets(self) -> List[RoundSetType]:
        response = self._action('listRoundSets')
        return cast(List[RoundSetType], response)

    def create_roundset(self, roundset: RoundSetType) -> RoundSetType:
        params = self._cast_parameter_type(roundset)
        response = self._action('createRoundSet', roundset=params)
        return cast(RoundSetType, response)

    def retrieve_roundset(self, roundset_url: str) -> RoundSetType:
        _, roundset_id = QneClient.parse_url(roundset_url)
        response = self._action('retrieveRoundSet', id=roundset_id)
        return cast(RoundSetType, response)

    def final_results_roundset(self, roundset_url: str) -> FinalResultType:
        _, roundset_id = QneClient.parse_url(roundset_url)
        response = self._action('finalResultsRoundSet', id=roundset_id)
        return cast(FinalResultType, response)

    def results_roundset(self, roundset_url: str) -> List[ResultType]:
        _, roundset_id = QneClient.parse_url(roundset_url)
        response = self._action('resultsRoundSet', id=roundset_id)
        return cast(List[ResultType], response)

    def retrieve_result(self, result_url: str) -> ResultType:
        _, result_id = QneClient.parse_url(result_url)
        response = self._action('retrieveResult', id=result_id)
        return cast(ResultType, response)

    def retrieve_finalresult(self, finalresult_url: str) -> FinalResultType:
        _, finalresult_id = QneClient.parse_url(finalresult_url)
        response = self._action('retrieveFinalResult', id=finalresult_id)
        return cast(FinalResultType, response)

    def list_templates(self) -> List[TemplateType]:
        response = self._action('listTemplates')
        return cast(List[TemplateType], response)

    def retrieve_template(self, template_url: str) -> TemplateType:
        _, template_id = QneClient.parse_url(template_url)
        response = self._action('retrieveTemplate', id=template_id)
        return cast(TemplateType, response)

    def list_networks(self) -> List[NetworkListType]:
        response = self._action('listNetworks')
        return cast(List[NetworkListType], response)

    def retrieve_network(self, network_url: str) -> NetworkType:
        _, network_id = QneClient.parse_url(network_url)
        response = self._action('retrieveNetwork', id=network_id)
        return cast(NetworkType, response)

    def list_channels(self) -> List[ChannelType]:
        response = self._action('listChannels')
        return cast(List[ChannelType], response)

    def retrieve_channel(self, channel_url: str) -> ChannelType:
        _, channel_id = QneClient.parse_url(channel_url)
        response = self._action('retrieveChannel', id=channel_id)
        return cast(ChannelType, response)

    def list_nodes(self) -> List[NodeType]:
        response = self._action('listNodes')
        return cast(List[NodeType], response)

    def retrieve_node(self, node_url: str) -> NodeType:
        _, node_id = QneClient.parse_url(node_url)
        response = self._action('retrieveNode', id=node_id)
        return cast(NodeType, response)

    def download_source_files(self, source_url: str, dest_dir: Path, file_name: str) -> None:
        """Download source files for an application to the download location.

        The files are downloaded from the `source_url` and stored in the `dest_dir`.

        Args:
            source_url: remote location from which to download the source files.
            dest_dir: local directory to which the source files should be downloaded.
            file_name: name of the file it should have on the local disk.
        """
        with self._client_get(source_url, headers=self._headers, stream=True) as response:

            if not dest_dir.exists():
                dest_dir.mkdir(parents=True, exist_ok=True)

            with open(str(dest_dir / file_name), 'wb') as fp:
                fp.write(response.raw.read())
