# pylint: disable=C0302
# Too many lines
import unittest
from pathlib import Path
from unittest.mock import call, patch, MagicMock, mock_open

from adk.api.local_api import LocalApi
from adk.exceptions import (ApplicationDoesNotExist, ExperimentDirectoryNotValid,
                            JsonFileNotFound, NoNetworkAvailable, PackageNotComplete)
from adk.managers.roundset_manager import RoundSetManager
from adk.parsers.output_converter import OutputConverter
from adk.settings import DEFAULT_BACKEND_TYPE
from adk.utils import get_empty_errordict


# pylint: disable=R0902
# Too many instance attributes
class AppValidate(unittest.TestCase):
    def setUp(self) -> None:
        self.config_manager = MagicMock(config_dir=Path("path/to/application"))
        self.local_api = LocalApi(config_manager=self.config_manager)

        self.application = "test_application"
        self.roles = ["Testrole1", "Testrole2"]
        self.path = Path("path/to/application")
        self.experiment_file_path = self.path / "experiment.json"
        self.config_files = ["application.json", "network.json", "result.json"]
        self.error_dict = {"error": [], "warning": [], "info": []}

        self.experiment_meta_local = {
            "application": {
                "slug": "app_name",
                "app_version": "",
                "multi_round": False
            },
            "backend": {
                "location": "local",
                "type": DEFAULT_BACKEND_TYPE
            },
            "description": "",
            "number_of_rounds": 1,
            "name": ""
        }

        self.experiment_data_local = {"meta": self.experiment_meta_local,
                                      "asset": {}
                                      }
        self.mock_app_manifest = {
            "application": {
                "name": "killer_app",
                "description": "add description",
                "multi_round": False
            },
            "remote": {}
        }
        self.mock_app_manifest_remote = {
            "application": {
                "name": "remote_app",
                "description": "add description",
                "multi_round": False
            },
            "remote": {
                "application": "https://fake.url/applications/20/",
                "application_id": 20,
                "slug": "remote_app",
                "app_version": {
                    "enabled": False,
                    "version": 1,
                    "app_version": "https://fake.url/app-versions/49/",
                    "app_config": "https://fake.url/app-configs/48/",
                    "app_result": "https://fake.url/app-results/47/",
                    "app_source": "https://fake.url/app-sources/44/"
                }
            }
        }
        self.mock_app_config = {"application": [
            {
                "title": "Qubit state of Sender",
                "slug": "qubit_state_sender",
                "description": "description",
                "values": [
                    {
                        "name": "phi",
                        "default_value": 0.0,
                        "minimum_value": -1.0,
                        "maximum_value": 1.0,
                        "scale_value": "pi"
                    },
                    {
                        "name": "theta",
                        "default_value": 0.0,
                        "minimum_value": 0.0,
                        "maximum_value": 1.0,
                        "scale_value": 2.0
                    }
                ],
                "input_type": "qubit",
                "roles": [
                    "Sender"
                ]
            }
        ],
            'network': {}
        }

        self.mock_application_json = [
            {
                "title": "Qubit state of Sender",
                "slug": "qubit_state_sender",
                "description": "description",
                "values": [
                    {
                        "name": "phi",
                        "default_value": 0.0,
                        "minimum_value": -1.0,
                        "maximum_value": 1.0,
                        "scale_value": "pi"
                    },
                    {
                        "name": "theta",
                        "default_value": 0.0,
                        "minimum_value": 0.0,
                        "maximum_value": 1.0,
                        "scale_value": 2.0
                    }
                ],
                "input_type": "qubit",
                "roles": [
                    "Role1"
                ]
            },
            {
                "title": "Qubit state of Sender",
                "slug": "qubit_state_sender",
                "description": "description",
                "values": [
                    {
                        "name": "x",
                        "default_value": 0.0,
                        "minimum_value": -1.0,
                        "maximum_value": 1.0,
                        "scale_value": "pi"
                    },
                ],
                "input_type": "number",
                "roles": [
                    "Role1",
                    "Role2"
                ]
            }
        ]

        self.mock_result_config = '[[{"output_type":"text","title":"results","parameters":{"content":' \
                                  '"Here we see an overview of all measurements,outcomes,and comparisons"}}],' \
                                  '[{"output_type":"table","title":"Alice\'s results","parameters":' \
                                  '{"data":"$.app_alice.table","headers":["Pairindex","Measurementbasis",' \
                                  '"SamebasisasBob","Measurementoutcome","SameoutcomeasBob"]}},' \
                                  '{"output_type":"table","title":"Bob\'s results","parameters":' \
                                  '{"data":"$.app_bob.table","headers":["Pairindex","Measurementbasis",' \
                                  '"SamebasisasAlice","Measurementoutcome","SameoutcomeasAlice"]}}],' \
                                  '[{"output_type":"text","title":"Alice\'sstatistics","parameters":' \
                                  '{"content":"Alice measured {{$.app_alice.x_basis_count}} times in the Xbasis and' \
                                  '{{$.app_alice.z_basis_count}}in the Zbasis."}}, {"output_type":"text",' \
                                  '"title":"Bob\'s statistics","parameters":{"content":"Bob measured ' \
                                  '{{$.app_bob.x_basis_count}} times in the Xbasis and {{$.app_bob.z_basis_count}} in' \
                                  'theZbasis."}}],[{"output_type":"text","title":"Generalstatistics","parameters":' \
                                  '{"content":"-Numberofpairsmeasuredinthesamebasis:{{$.app_alice.same_basis_count}}' \
                                  '\n-Numberof pairs chosen to compare measurement outcomes for:' \
                                  '{{$.app_alice.outcome_comparison_count}}\n-Number of different measurement ' \
                                  'outcomes among the pairs chosen to compare:{{$.app_alice.diff_outcome_count}}\n-' \
                                  'QBER:{{$.app_alice.qber}}.*QBERistheQuantumBitErrorRate.It is thefraction of ' \
                                  'compared measurement outcomes that are not equal,eventhoughtheyresult ' \
                                  'frommeasurementsinthesamebasis.*\n-Keyratepotential:' \
                                  '{{$.app_alice.key_rate_potential}}.*Rateofsecurekeythat can in theorybeextracted ' \
                                  'fromtherawkey(aftermoreclassicalpost-processing).The rate is lengthofsecurekey ' \
                                  'dividedby lengthofrawkey .*"}}],[{"output_type":"text","title":"Alice\'s rawkey",' \
                                  '"parameters":{"content":"{{$.app_alice.raw_key}}"}},{"output_type":"text",' \
                                  '"title":"Bob\'srawkey","parameters":{"content":"{{$.app_bob.raw_key}}"}}]]'

        self.channel_info_list = [{"slug": "c1-slug", "parameters": ["param-1", "param-2"]},
                                  {"slug": "c2-slug", "parameters": ["param-1"]},
                                  {"slug": "c3-slug", "parameters": ["param-2"]}]

        self.node_info_list = [{"slug": "n1-slug", "node_parameters": ["param-1", "param-2"], "number_of_qubits": 2,
                                "qubit_parameters": ["param-1", "param-2"]},
                               {"slug": "n2-slug", "node_parameters": ["param-2"], "number_of_qubits": 1,
                                "qubit_parameters": ["param-1"]},
                               {"slug": "n3-slug", "node_parameters": ["param-1"], "number_of_qubits": 1,
                                "qubit_parameters": ["param-2"]}]

        self.mock_network_data = {
            "networks": {
                "network1": {
                    "name": "Network 1",
                    "slug": "network1",
                    "channels": [
                        "n1-n2",
                        "n2-n3"
                    ]
                }
            }
        }
        self.mock_channel_data = {
            "channels": [
                {
                    "slug": "n1-n2",
                    "node1": "n1",
                    "node2": "n2",
                    "parameters": [
                        "param-1"
                    ]
                },
                {
                    "slug": "n2-n3",
                    "node1": "n2",
                    "node2": "n3",
                    "parameters": [
                        "param-2"
                    ]
                }
            ]
        }
        self.mock_node_data = {
            "nodes": [
                {
                    "name": "N1",
                    "slug": "n1",
                    "coordinates": {
                        "latitude": 52.3667,
                        "longitude": 4.8945
                    },
                    "node_parameters": [
                        "gate-fidelity"
                    ],
                    "number_of_qubits": 3,
                    "qubit_parameters": [
                        "relaxation-time",
                        "dephasing-time"
                    ]
                }
            ]
        }
        self.mock_template_data = {
            "templates": [
                {
                    "title": "Parameter One",
                    "slug": "param-1",
                    "values": [
                        {
                            "name": "fidelity",
                            "default_value": 1.0,
                            "minimum_value": 0.5,
                            "maximum_value": 1.0,
                            "unit": "unit-name",
                            "scale_value": 1.0
                        }
                    ],
                    "input_type": "fidelity_slider"
                },
                {
                    "title": "Parameter 2",
                    "slug": "param-2",
                    "values": [
                        {
                            "name": "t1",
                            "default_value": 0,
                            "minimum_value": 0,
                            "maximum_value": 1000,
                            "unit": "milliseconds",
                            "scale_value": 12.0
                        }
                    ],
                    "input_type": "time"
                }
            ]
        }
        self.dummy_qubit = [{
                "qubit_id": 0,
                "qubit_parameters": [
                    {
                        "slug": "relaxation-time",
                        "values": [
                            {
                                "name": "t1",
                                "value": 0,
                                "scale_value": 1.0
                            }
                        ]
                    }
                ]
            }
        ]

        self.dummy_channel_params = [
                {
                  "slug": "elementary-link-fidelity",
                  "values": [
                    {
                      "name": "fidelity",
                      "value": 12344.0,
                      "scale_value": 1.0
                    }
                  ]
                }
        ]

        self.mock_experiment_data = {
            "meta": {
                "application": {
                    "slug": "app_name",
                    "app_version": "",
                    "multi_round": "False"
                },
                "backend": {
                    "location": "local",
                    "type": DEFAULT_BACKEND_TYPE
                },
                "description": "exptest3: experiment description",
                "number_of_rounds": 1,
                "name": "exptest3"
            },
            "asset": {
                 "network": {
                     "name": "Randstad",
                     "slug": "randstad",
                     "nodes": [{"slug": "n1", "node_parameters": None, "qubits": self.dummy_qubit},
                               {"slug": "n2", "node_parameters": None, "qubits": self.dummy_qubit},
                               {"slug": "n3", "node_parameters": None, "qubits": self.dummy_qubit},
                               {"slug": "n4", "node_parameters": None, "qubits": self.dummy_qubit},
                               {"slug": "n5", "node_parameters": None, "qubits": self.dummy_qubit}],
                     "channels": [{"slug": "n1-n2", "parameters": self.dummy_channel_params,
                                   "node1": "n1", "node2": "n2"},
                                  {"slug": "n2-n3", "parameters": self.dummy_channel_params,
                                   "node1": "n2", "node2": "n3"},
                                  {"slug": "n4-n3", "parameters": self.dummy_channel_params,
                                   "node1": "n4", "node2": "n3"},
                                  {"slug": "n4-n5", "parameters": self.dummy_channel_params,
                                   "node1": "n4", "node2": "n5"}],
                     "roles": {"role1": "n1", "role2": "n2"}
                 }
            }
        }
        self.all_network_nodes = {'randstad': ['n1', 'n2', 'n3', 'n4', 'n5']}
        self.all_network_channels = ['n1-n2', 'n2-n3', 'n4-n3', 'n4-n5']

# pylint: disable=R0904
# R0904: Too many public methods
class ApplicationValidate(AppValidate):
    def test_constructor(self):
        with patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock:
            read_json_file_mock.side_effect = JsonFileNotFound("networks/networks.json")
            self.assertRaises(PackageNotComplete, LocalApi, self.config_manager)

    def test_init_application_new_manifest(self):
        with patch('adk.api.local_api.Path.mkdir') as mock_mkdir, \
             patch("adk.api.local_api.Path.is_file") as mock_is_file, \
             patch("adk.api.local_api.Path.exists") as mock_path_exists, \
             patch("adk.api.local_api.utils.move_files") as move_files_mock, \
             patch("adk.api.local_api.utils.get_default_manifest") as get_default_manifest_mock, \
             patch.object(self.local_api, 'get_application_data') as get_application_data_mock, \
             patch.object(self.local_api, 'set_application_data') as set_application_data_mock, \
             patch.object(self.local_api, 'get_application_file_names') as get_application_file_names_mock, \
             patch.object(self.config_manager, 'add_application') as add_application_mock:

            mock_path_exists.side_effect = [False, False]
            mock_is_file.return_value = False
            get_default_manifest_mock.return_value = {"application": {"name": self.application},
                                                      "remote": {}}
            get_application_data_mock.return_value = self.mock_app_manifest
            get_application_file_names_mock.return_value = ["app_role1.py", "app_role2.py", "lib.py"]

            self.local_api.init_application(self.application, self.path)

            move_files_calls = [call(self.path, self.path / 'config',
                                     files_list=['application.json', 'network.json', 'result.json']),
                                call(self.path, self.path / 'src',
                                     files_list=["app_role1.py", "app_role2.py", "lib.py"])]
            move_files_mock.assert_has_calls(move_files_calls, any_order=True)
            get_default_manifest_mock.assert_called_once_with(self.application)
            self.assertEqual(mock_mkdir.call_count, 2)
            expected_manifest = {
                "application": {
                    "name": "test_application",
                },
                "remote": {}
            }
            set_application_data_mock.assert_called_once_with(self.path, expected_manifest)
            add_application_mock.assert_called_once_with(application_name="test_application",
                                                         application_path=self.path)

    def test_init_application_manifest_exists(self):
        with patch('adk.api.local_api.Path.mkdir') as mock_mkdir, \
             patch("adk.api.local_api.Path.is_file") as mock_is_file, \
             patch("adk.api.local_api.Path.exists") as mock_path_exists, \
             patch("adk.api.local_api.utils.move_files") as move_files_mock, \
             patch("adk.api.local_api.utils.get_default_manifest") as get_default_manifest_mock, \
             patch.object(self.local_api, 'get_application_data') as get_application_data_mock, \
             patch.object(self.local_api, 'set_application_data') as set_application_data_mock, \
             patch.object(self.local_api, 'get_application_file_names') as get_application_file_names_mock, \
             patch.object(self.config_manager, 'add_application') as add_application_mock:

            mock_path_exists.side_effect = [True, True]
            mock_is_file.return_value = True
            get_default_manifest_mock.return_value = {"application": {"name": self.application},
                                                      "remote": {}}
            get_application_data_mock.return_value = self.mock_app_manifest_remote
            get_application_file_names_mock.return_value = ["app_role1.py", "app_role2.py", "lib.py"]

            self.local_api.init_application(self.application, self.path)

            move_files_calls = [call(self.path, self.path / 'config',
                                     files_list=['application.json', 'network.json', 'result.json']),
                                call(self.path, self.path / 'src',
                                     files_list=["app_role1.py", "app_role2.py", "lib.py"])]
            move_files_mock.assert_has_calls(move_files_calls, any_order=True)
            get_default_manifest_mock.assert_not_called()
            mock_mkdir.assert_not_called()
            expected_manifest = {
                "application": {
                    "name": "test_application",
                    "description": "add description",
                    "multi_round": False
                },
                "remote": {}
            }
            set_application_data_mock.assert_called_once_with(self.path, expected_manifest)
            add_application_mock.assert_called_once_with(application_name="test_application",
                                                         application_path=self.path)

    def test_create_application(self):
        with patch('adk.api.local_api.Path.mkdir') as mock_mkdir, \
             patch("adk.api.local_api.Path.exists") as mock_path_exists, \
             patch.object(LocalApi, "_get_network_nodes") as _get_nodes_mock, \
             patch("adk.api.local_api.utils.get_dummy_application") as get_dummy_application_mock, \
             patch("adk.api.local_api.shutil.rmtree") as rmtree_mock, \
             patch("adk.api.local_api.utils.write_json_file") as write_json_file_mock, \
             patch("adk.api.local_api.utils.write_file") as write_file_mock, \
             patch.object(self.config_manager, 'add_application') as config_manager_mock:

            _get_nodes_mock.return_value = {"dummy_network": ["network1", "network2", "network3"]}
            get_dummy_application_mock.return_value = {'application': [{'roles': ['dummy_role']}]}
            mock_path_exists.return_value = False
            self.local_api.create_application(self.application, self.roles, self.path)

            config_manager_mock.assert_called_once_with(application_name=self.application, application_path=self.path)
            self.assertEqual(write_file_mock.call_count, len(self.roles))
            self.assertEqual(mock_mkdir.call_count, 2)
            self.assertEqual(write_json_file_mock.call_count, 4)
            self.assertEqual(write_file_mock.call_count, 2)
            _get_nodes_mock.assert_called_once()
            get_dummy_application_mock.assert_called_once()
            config_manager_mock.assert_called_once_with(application_name=self.application, application_path=self.path)

            # Raise exception when no network available
            _get_nodes_mock.return_value = {}
            self.assertRaises(NoNetworkAvailable, self.local_api.create_application, self.application, self.roles,
                              self.path)
            rmtree_mock.assert_called_once()

    def test_clone_application(self):
        with patch('adk.api.local_api.Path.mkdir') as mock_mkdir, \
             patch("adk.api.local_api.utils.copy_files") as copy_files_mock, \
             patch.object(self.local_api, 'get_application_data') as get_application_data_mock, \
             patch.object(self.local_api, 'set_application_data') as set_application_data_mock, \
             patch.object(self.local_api, 'get_application_file_names') as get_application_file_names_mock, \
             patch.object(self.config_manager, 'get_application_path') as get_application_path_mock, \
             patch.object(self.config_manager, 'add_application') as add_application_mock:

            get_application_path_mock.return_value = self.path / 'old'
            get_application_file_names_mock.return_value = ["app_role1.py", "app_role2.py", "app_role3.py", "lib.py"]
            get_application_data_mock.return_value = self.mock_app_manifest
            self.local_api.clone_application(self.application, "New_App", self.path)

            get_application_path_mock.assert_called_once_with("test_application")
            copy_files_calls = [call(self.path / 'old', self.path, files_list=['manifest.json']),
                                call(self.path / 'old' / 'config', self.path / 'config',
                                     files_list=['application.json', 'network.json', 'result.json']),
                                call(self.path / 'old' / 'src', self.path / 'src',
                                     files_list=["app_role1.py", "app_role2.py", "app_role3.py", "lib.py"])]
            copy_files_mock.assert_has_calls(copy_files_calls)

            self.assertEqual(mock_mkdir.call_count, 2)
            expected_manifest = {
                "application": {
                    "name": "new_app",
                    "description": "add description",
                    "multi_round": False
                },
                "remote": {}
            }
            set_application_data_mock.assert_called_once_with(self.path, expected_manifest)
            add_application_mock.assert_called_once_with(application_name="new_app", application_path=self.path)

    def test_validate_application(self):
        with patch.object(self.config_manager, "application_exists") as application_exists_mock, \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json") as is_manifest_valid_json_mock, \
             patch.object(LocalApi, "_LocalApi__is_structure_valid") as is_structure_valid_mock, \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json") as is_config_valid_json_mock, \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid") as is_result_valid_mock, \
             patch.object(LocalApi, "_LocalApi__is_python_valid") as is_python_valid_mock:

            # If application is not unique, is_config_valid_json() returns an error and warning
            application_exists_mock.return_value = True, None

            self.assertEqual(self.local_api.validate_application(application_name=self.application,
                                                                 application_path=self.path),
                             self.error_dict)

            application_exists_mock.assert_called_once_with(self.application)
            is_structure_valid_mock.assert_called_once_with(self.path, self.error_dict)
            is_config_valid_json_mock.assert_called_once_with(self.path, self.error_dict)
            is_python_valid_mock.assert_called_once_with(self.path, self.error_dict)
            is_result_valid_mock.assert_called_once_with(self.path, self.error_dict)
            is_manifest_valid_json_mock.assert_called_once_with(self.path, self.error_dict)

            # If application is unique
            application_exists_mock.reset_mock()
            application_exists_mock.return_value = False, None
            self.assertEqual(self.local_api.validate_application(application_name=self.application,
                                                                 application_path=self.path),
                             {"error": [f"Application '{self.application}' does not exist"], "warning": [], "info": []})
            application_exists_mock.assert_called_once_with(self.application)

    def test__is_python_valid(self):
        with patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_structure_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid"), \
             patch.object(LocalApi, "_LocalApi__get_role_file_names") as get_role_file_names_mock, \
             patch.object(self.local_api, 'get_application_file_names') as get_application_file_names_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock, \
             patch.object(LocalApi, "_LocalApi__is_valid_input_params_for_role") as is_valid_param_role, \
             patch("adk.api.local_api.utils.check_python_syntax") as check_python_syntax:

            get_role_file_names_mock.return_value = ["app_role1.py", "app_role2.py", "app_role3.py"]
            get_application_file_names_mock.return_value = ["app_role1.py", "app_role2.py", "app_role3.py", "lib.py"]
            check_python_syntax.side_effect = [(True, 'ok'), (False, 'error'), (True, 'ok'), (True, 'ok')]

            self.local_api.validate_application(application_name=self.application, application_path=self.path)
            get_role_file_names_mock.assert_called_once_with(self.path / 'config')
            get_application_file_names_mock.assert_called_once_with(self.path / 'src')

            check_python_syntax_call = [call(self.path / 'src' / 'app_role1.py'),
                                        call(self.path / 'src' / 'app_role2.py'),
                                        call(self.path / 'src' / 'app_role3.py'),
                                        call(self.path / 'src' / 'lib.py')]
            check_python_syntax.assert_has_calls(check_python_syntax_call)
            self.assertEqual(is_valid_param_role.call_count, 2)

    def test_is_python_valid_input_params_for_roles(self):
        with patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json"), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_structure_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid"), \
             patch("adk.api.local_api.Path.is_file", return_value=True), \
             patch.object(LocalApi, "_LocalApi__get_role_file_names") as get_role_file_names_mock, \
             patch.object(self.local_api, 'get_application_file_names') as get_application_file_names_mock, \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Role1', 'Role2']), \
             patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock, \
             patch("adk.api.local_api.utils.get_function_arguments") as get_function_arguments_mock, \
             patch("adk.api.local_api.utils.check_python_syntax") as check_python_syntax:

            read_json_file_mock.return_value = self.mock_application_json
            check_python_syntax.return_value = (True, 'ok')
            get_role_file_names_mock.return_value = ["app_role1.py", "app_role2.py", "appIncorrect.py", "app_role3.py"]
            get_application_file_names_mock.return_value = ["app_role1.py", "app_role2.py",
                                                            "appIncorrect.py", "app_role3.py"]
            get_function_arguments_mock.side_effect = [['phi', 'x'], ['app_config', 'y'], None]

            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)
            get_role_file_names_mock.assert_called_once_with(self.path / 'config')
            get_application_file_names_mock.assert_called_once_with(self.path / 'src')
            check_python_syntax_call = [call(self.path / 'src' / 'app_role1.py'),
                                        call(self.path / 'src' / 'app_role2.py'),
                                        call(self.path / 'src' / 'appIncorrect.py'),
                                        call(self.path / 'src' / 'app_role3.py')]
            check_python_syntax.assert_has_calls(check_python_syntax_call)
            self.assertEqual(check_python_syntax.call_count, 4)
            get_function_arguments_call = [call(self.path / 'src' / 'app_role1.py', function_name='main'),
                                           call(self.path / 'src' / 'app_role2.py', function_name='main'),
                                           call(self.path / 'src' / 'app_role3.py', function_name='main')]
            self.assertEqual(get_function_arguments_mock.call_count, 3)
            get_function_arguments_mock.assert_has_calls(get_function_arguments_call)

            self.assertEqual(len(error_dict['error']), 5)
            self.assertIn('main() in app_role1.py is missing the theta argument', error_dict['error'])
            self.assertIn('main() in app_role2.py is missing the x argument', error_dict['error'])
            self.assertIn('Name of appIncorrect.py is not properly formatted', error_dict['error'])
            self.assertIn('main() not found in file app_role3.py', error_dict['error'])
            self.assertIn('main() in app_role1.py is missing the app_config argument', error_dict['error'])

    def test_is_result_config_valid(self):
        with patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json"), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_structure_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_python_valid"), \
             patch.object(LocalApi, "_LocalApi__get_role_file_names") as get_role_file_names_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True), \
             patch('adk.api.local_api.open', mock_open(read_data=self.mock_result_config)), \
             patch("adk.api.local_api.utils.get_function_return_variables") as get_function_return_mock:

            get_role_file_names_mock.return_value = ["app_alice.py", "app_bob.py",]
            get_function_return_mock.side_effect = [
                [
                    ['r11', 'table', 'same_basis_count', 'outcome_comparison_count', 'diff_outcome_count', 'qber'],
                    ['r21', 'r22', 'same_basis_count', 'outcome_comparison_count', 'diff_outcome_count'],
                    ['same_basis_count', 'outcome_comparison_count', 'diff_outcome_count', 'qber', 'key_rate_potential',
                     'x_basis_count']
                 ],
                [
                    ['r11', 'table', 'x_basis_count', 'z_basis_count', 'raw_key'],
                    ['table', 'x_basis_count', 'z_basis_count', 'raw_key']
                 ]
            ]

            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)

            missing_return_vars_alice = ['qber', 'key_rate_potential', 'x_basis_count', 'table', 'raw_key',
                                         'z_basis_count']
            included_return_vars_alice = ['same_basis_count', 'outcome_comparison_count', 'diff_outcome_count']

            self.assertEqual(len(error_dict['error']), len(missing_return_vars_alice))

            for variable_name in included_return_vars_alice:
                self.assertNotIn(f'Variable {variable_name} is used in result.json, but not found in return '
                                 f'statement(s) of main() in file app_alice.py', error_dict['error'])

            get_function_return_mock.reset()
            get_function_return_mock.side_effect = [
                [
                    ['same_basis_count', 'outcome_comparison_count', 'diff_outcome_count', 'qber',
                     'key_rate_potential', 'x_basis_count'],
                    ['same_basis_count', 'r11', 'table'],
                    ['same_basis_count', 'r21', 'r22']
                 ],
                [
                    ['table', 'x_basis_count', 'z_basis_count', 'raw_key'],
                    ['r11', 'table', 'x_basis_count']]
            ]
            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)

            missing_return_vars_alice = ['outcome_comparison_count', 'diff_outcome_count', 'qber',
                                         'key_rate_potential', 'x_basis_count', 'table', 'raw_key', 'z_basis_count']
            included_return_vars_alice = ['same_basis_count']

            for variable_name in included_return_vars_alice:
                self.assertNotIn(f'Variable {variable_name} is used in result.json, but not found in return '
                                 f'statement(s) of main() in file app_alice.py', error_dict['error'])

            for variable_name in missing_return_vars_alice:
                self.assertIn(f'Variable {variable_name} is used in result.json, but not found in return '
                              f'statement(s) of main() in file app_alice.py', error_dict['error'])

            missing_return_vars_bob= ['z_basis_count', 'raw_key']
            included_return_vars_bob = ['table', 'x_basis_count']

            for variable_name in included_return_vars_bob:
                self.assertNotIn(f'Variable {variable_name} is used in result.json, but not found in return '
                                 f'statement(s) of main() in file app_bob.py', error_dict['error'])

            for variable_name in missing_return_vars_bob:
                self.assertIn(f'Variable {variable_name} is used in result.json, but not found in return '
                              f'statement(s) of main() in file app_bob.py', error_dict['error'])

            self.assertEqual(len(error_dict['error']), len(missing_return_vars_alice) + len(missing_return_vars_bob))


            get_function_return_mock.reset()
            get_function_return_mock.side_effect = [
                [['same_basis_count', 'outcome_comparison_count', 'diff_outcome_count', 'table',
                  'qber', 'key_rate_potential', 'x_basis_count', 'z_basis_count', 'raw_key']],
                [['table', 'x_basis_count', 'z_basis_count', 'raw_key']]
            ]
            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)

            self.assertEqual(len(error_dict['error']), 0)

            # when return variable is something other than dict / function call, then empty list is returned
            get_function_return_mock.reset()
            get_function_return_mock.side_effect = [
                [],
                []
            ]
            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)

            self.assertEqual(len(error_dict['error']), 0)

    def test__is_application_config_valid(self):
        with patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json"), \
             patch.object(LocalApi, "_LocalApi__is_structure_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_python_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid"), \
             patch("adk.api.local_api.validate_json_file") as validate_json_file_mock, \
             patch.object(LocalApi, "_LocalApi__get_application_role_names") as get_application_role_names_mock, \
             patch.object(LocalApi, "_LocalApi__get_role_names") as get_role_names_mock:

            validate_json_file_mock.return_value = [(True, None), (True, None)]

            get_application_role_names_mock.return_value = ["role0", "role2", "role3"]
            get_role_names_mock.return_value = ["role1", "role2", "role3"]
            error_dict = self.local_api.validate_application(application_name=self.application, application_path=self.path)
            self.assertIn(f"The application role 'role0' in "
                          f"'{self.path / 'config' / 'application.json'}' not found in "
                          f"'{self.path / 'config' / 'network.json'}'",
                          error_dict["error"][0])

    def test__is_structure_valid_all_oke(self):
        with patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json"), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_python_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid"), \
             patch("adk.api.local_api.validate_json_file") as validate_json_file_mock, \
             patch.object(LocalApi, "_LocalApi__get_role_file_names") as get_role_file_names_mock, \
             patch("adk.api.local_api.Path.is_dir", return_value=True) as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock, \
             patch.object(self.local_api, 'get_application_file_names') as get_application_file_names_mock:

            is_dir_mock.side_effect = [True, True, True, True]
            is_file_mock.side_effect = [True, True, True, True, True]
            get_application_file_names_mock.return_value = ["app_role1.py", "app_role2.py"]
            get_role_file_names_mock.return_value = ["app_role1.py", "app_role2.py"]
            validate_json_file_mock.return_value = (True, None)
            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)
            self.assertEqual(is_dir_mock.call_count, 2)
            self.assertEqual(is_file_mock.call_count, 4)
            validate_json_file_mock.assert_called_once()
            get_application_file_names_mock.assert_called_once()
            self.assertEqual(0, len(error_dict["error"]))
            self.assertEqual(0, len(error_dict["warning"]))

    def test__is_structure_valid_role_file_not_found(self):
        with patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json"), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_python_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid"), \
             patch("adk.api.local_api.validate_json_file") as validate_json_file_mock, \
             patch.object(LocalApi, "_LocalApi__get_role_file_names") as get_role_file_names_mock, \
             patch("adk.api.local_api.Path.is_dir", return_value=True) as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock, \
             patch.object(self.local_api, 'get_application_file_names') as get_application_file_names_mock:

            is_dir_mock.side_effect = [True, True, True, True]
            is_file_mock.side_effect = [True, True, True, True, True]
            get_application_file_names_mock.return_value = ["app_role1.py", "app_role3.py", "app_role4.py"]
            get_role_file_names_mock.return_value = ["app_role1.py", "app_role2.py"]
            validate_json_file_mock.return_value = (True, None)
            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)
            self.assertEqual(is_dir_mock.call_count, 2)
            self.assertEqual(is_file_mock.call_count, 4)
            validate_json_file_mock.assert_called_once()
            get_application_file_names_mock.assert_called_once()
            self.assertIn(f"The application file 'app_role2.py' for the corresponding role in "
                          f"'{self.path / 'config' / 'network.json'}' not found in '{self.path / 'src'}'",
                          error_dict["error"][0])

    def test__is_structure_valid_config_dir_not_found(self):
        with patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json"), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_python_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid"), \
             patch("adk.api.local_api.validate_json_file") as validate_json_file_mock, \
             patch("adk.api.local_api.Path.is_dir", return_value=True) as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock:

            # If the app_config_path, app_config_path / application.json does not exist and validate_json_file is False
            is_dir_mock.side_effect = [False, True, True, True]
            is_file_mock.side_effect = [True, False, True, True, True]
            validate_json_file_mock.return_value = (False, "Invalid json")
            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)
            self.assertEqual(is_dir_mock.call_count, 2)
            self.assertEqual(is_file_mock.call_count, 1)
            validate_json_file_mock.assert_called_once()
            self.assertIn(f"{self.path} should contain a 'config' directory", error_dict["error"][0])
            # the invalid json will be reported in __is_config_valid_json
            self.assertTrue(len(error_dict["error"]) == 1)

    def test__is_structure_valid_src_dir_not_found_and_files_missing(self):
        with patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json"), \
             patch.object(LocalApi, "_LocalApi__is_config_valid_json", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_python_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid"), \
             patch("adk.api.local_api.validate_json_file") as validate_json_file_mock, \
             patch.object(LocalApi, "_LocalApi__get_role_file_names") as get_role_file_names_mock, \
             patch("adk.api.local_api.Path.is_dir", return_value=True) as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock, \
             patch.object(self.local_api, 'get_application_file_names') as get_application_file_names_mock:

            # No files at all in the directories
            is_dir_mock.side_effect = [True, False]
            is_file_mock.side_effect = [False, False, False, False, False]
            validate_json_file_mock.return_value = (True, None)
            get_application_file_names_mock.return_value = ['__init__.py']
            get_role_file_names_mock.return_value = ["app_role1.py", "app_role2.py"]
            error_dict = self.local_api.validate_application(application_name=self.application,
                                                             application_path=self.path)
            self.assertEqual(is_dir_mock.call_count, 2)
            self.assertEqual(is_file_mock.call_count, 4)

            self.assertIn(f"{self.path / 'config'} should contain the file 'application.json'", error_dict["error"][0])
            self.assertIn(f"{self.path / 'config'} should contain the file 'network.json'", error_dict["error"][1])
            self.assertIn(f"{self.path / 'config'} should contain the file 'result.json'", error_dict["error"][2])
            self.assertIn(f"{self.path} should contain a 'src' directory", error_dict["error"][3])
            self.assertIn(f"{self.path} should contain the file 'manifest.json'", error_dict["warning"][0])

    def test__is_config_valid(self):
        with patch.object(LocalApi, "_LocalApi__is_structure_valid") as is_structure_valid_mock, \
             patch.object(LocalApi, "_LocalApi__is_python_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_application_config_valid", return_value=True), \
             patch.object(LocalApi, "_LocalApi__is_result_config_valid"), \
             patch.object(LocalApi, "_LocalApi__is_manifest_valid_json"), \
             patch.object(self.config_manager, "application_exists", return_value=(True, None)), \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock, \
             patch("adk.api.local_api.validate_json_file") as validate_json_file_mock, \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock:

            # If is_file() is true and validate_json_file is true
            is_structure_valid_mock.return_value = self.error_dict
            validate_json_file_mock.return_value = True, None
            validate_json_schema_mock.return_value = True, None
            self.local_api.validate_application(application_name=self.application, application_path=self.path)
            self.assertEqual(is_file_mock.call_count, 3)
            self.assertEqual(validate_json_schema_mock.call_count, 3)

            # If validate_json_file is false
            is_file_mock.reset_mock()
            validate_json_schema_mock.reset_mock()
            validate_json_schema_mock.return_value = (False, "Error")
            self.local_api.validate_application(application_name=self.application, application_path=self.path)
            self.assertEqual(is_file_mock.call_count, 3)
            self.assertEqual(validate_json_schema_mock.call_count, 3)

    def test_list_applications(self):
        with patch.object(self.config_manager, "get_applications") as get_applications_mock:
            self.local_api.list_applications()
            get_applications_mock.assert_called_once()

    def test_get_application_config(self):
        with patch.object(self.config_manager, "get_application") as get_application_mock, \
             patch("adk.api.local_api.utils.read_json_file") as read_mock:

            read_mock.side_effect = [[{'app': 'foo'}], {'network': 'bar'}]
            get_application_mock.return_value = {'path': 'some-path'}
            config = self.local_api.get_application_config('test')
            get_application_mock.assert_called_once_with('test')
            self.assertEqual(read_mock.call_count, 2)
            self.assertDictEqual(config, {'application': [{'app': 'foo'}], 'network': {'network': 'bar'}})

            get_application_mock.reset_mock()
            get_application_mock.return_value = {}
            config = self.local_api.get_application_config('test')
            self.assertIsNone(config)

    def test_set_application_data(self):
        with patch("adk.api.local_api.utils.write_json_file") as write_mock:

            self.local_api.set_application_data(self.path, self.mock_app_manifest)
            self.assertEqual(write_mock.call_count, 1)
            write_mock.assert_called_once_with(self.path / 'manifest.json', self.mock_app_manifest)

    def test_get_application_data(self):
        with patch("adk.api.local_api.utils.read_json_file") as read_mock:

            read_mock.return_value = self.mock_app_manifest
            application_data = self.local_api.get_application_data(self.path)
            self.assertEqual(read_mock.call_count, 1)
            read_mock.assert_called_once_with(self.path / 'manifest.json')
            self.assertDictEqual(application_data, self.mock_app_manifest)

    def test_delete_application_invalid_application_dir(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch.object(self.config_manager, "get_application_from_path", return_value=('app_dir', None)), \
             patch("adk.api.local_api.Path.is_file", return_value=False):

            is_dir_mock.side_effect = [False]
            self.assertRaises(ApplicationDoesNotExist, self.local_api.delete_application, 'app_dir', self.path)

    def test_delete_application_src_dir(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file") as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch.object(self.config_manager, "get_application_from_path", return_value=('app_dir', None)), \
             patch.object(self.config_manager, "delete_application"), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            is_dir_mock.side_effect = [True, True, True, False]
            is_file_mock.side_effect = [True, True, True, True, True, True, True, True, True]
            rmdir_mock.side_effect = [None, None]

            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 3)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertTrue(delete_application_output)

            # rmdir directory ./result fails
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, True, True, False]
            is_file_mock.side_effect = [True, True, True, True, True, True, True, True, True]
            rmdir_mock.side_effect = [OSError, None]

            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 3)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertFalse(delete_application_output)

            # network.json not found, app files not deleted
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, True, True, False]
            is_file_mock.side_effect = [False, True, True, True, True]
            rmdir_mock.side_effect = [OSError, None]

            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 1)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertFalse(delete_application_output)

    def test_delete_application_config_dir(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file") as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch.object(self.config_manager, "get_application_from_path", return_value=('app_dir', None)), \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            is_dir_mock.side_effect = [True, False, True, True]
            is_file_mock.side_effect = [True, True, True, True, True]

            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 4)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertTrue(delete_application_output)

            # rmdir directory ./config fails
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, False, True, True]
            is_file_mock.side_effect = [True, True, True, True, True]
            rmdir_mock.side_effect = [OSError, None]

            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 4)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertFalse(delete_application_output)

    def test_delete_application_with_application_dir(self):
        with patch("adk.api.local_api.Path.is_dir", return_value=True) as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch.object(self.config_manager, "get_application_from_path", return_value=('app_dir', None)), \
             patch.object(self.config_manager, "delete_application"), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 6)
            self.assertEqual(rmdir_mock.call_count, 3)
            self.assertTrue(delete_application_output)

            # rmdir directory application_path fails
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, True, False, False, True]
            is_file_mock.side_effect = [True, True, True, True, True]
            rmdir_mock.side_effect = [OSError]

            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 1)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertFalse(delete_application_output)

    def test_delete_application_path_from_configuration(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch.object(self.config_manager, "get_application_path", return_value='other_path'), \
             patch.object(self.config_manager, "get_application_from_path") as resulting_path_mock, \
             patch.object(self.config_manager, "delete_application"), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            resulting_path_mock.return_value = ('app_dir', None)
            is_dir_mock.side_effect = [True, True, True, True]
            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            resulting_path_mock.assert_called_once_with(Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 6)
            self.assertEqual(rmdir_mock.call_count, 3)
            self.assertTrue(delete_application_output)

            # rmdir directory application_path fails
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, False, False, True]
            is_file_mock.side_effect = [True, True, True, True, True]
            rmdir_mock.side_effect = [OSError]

            delete_application_output = self.local_api.delete_application('app_dir', application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 1)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertFalse(delete_application_output)

    def test_delete_application_path_from_configuration_not_valid(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True), \
             patch("adk.api.local_api.Path.unlink"), \
             patch.object(self.config_manager, "get_application_path", return_value=None), \
             patch.object(self.config_manager, "get_application_from_path") as resulting_path_mock, \
             patch.object(self.config_manager, "delete_application"), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.os.rmdir"):

            resulting_path_mock.return_value = ('app_dir', None)
            is_dir_mock.side_effect = [False, False]
            self.assertRaises(ApplicationDoesNotExist, self.local_api.delete_application, 'app_dir',
                              application_path=Path('dummy'))

    def test_delete_application_no_application_directory(self):
        with patch("adk.api.local_api.Path.is_dir", return_value=True), \
             patch("adk.api.local_api.Path.is_file", return_value=True), \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch.object(self.config_manager, "get_application_from_path", return_value=('app_dir', None)), \
             patch.object(self.config_manager, "delete_application"), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            delete_application_output = self.local_api.delete_application(None, application_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 6)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertFalse(delete_application_output)


# pylint: disable=R0904
# Too many public methods
class ExperimentValidate(AppValidate):
    def test_experiments_create(self):
        with patch.object(LocalApi, "get_network_data") as get_network_data_mock, \
             patch.object(LocalApi, "create_asset_network") as create_network_asset_mock, \
             patch.object(LocalApi, "_LocalApi__create_experiment") as create_exp_mock:

            get_network_data_mock.return_value = {'a': 'b'}
            create_network_asset_mock.return_value = {'c': 'd'}
            self.local_api.experiments_create(experiment_name='name', app_config={'foo': 'bar'},
                                              network_name='network_name', local=True, path=Path('dummy'),
                                              application_name='application')
            get_network_data_mock.assert_called_once_with(network_name='network_name')
            create_network_asset_mock.assert_called_once_with(network_data={'a': 'b'}, app_config={'foo': 'bar'})
            create_exp_mock.assert_called_once_with(experiment_name='name', app_config={'foo': 'bar'},
                                                    asset_network={'c': 'd'}, local=True, path=Path('dummy'),
                                                    application_name='application')

    def test_create_experiment(self):
        with patch("adk.api.local_api.utils.write_json_file") as write_mock, \
             patch('adk.api.local_api.Path.mkdir') as mkdir_mock, \
             patch.object(LocalApi, 'create_asset_network') as create_asset_network_mock, \
             patch.object(LocalApi, 'get_network_data'), \
             patch.object(LocalApi, "_LocalApi__copy_input_files_from_application") as copy_files_mock:

            experiment_name = 'test'
            create_asset_network_mock.return_value = {'a': 'b'}
            self.local_api.experiments_create(experiment_name=experiment_name, application_name='app_name',
                                              network_name='network_name', local=True, path=Path('dummy'),
                                              app_config=self.mock_app_config)

            self.assertEqual(mkdir_mock.call_count, 2)

            experiment_dir = Path('dummy') / experiment_name
            input_dir = experiment_dir / 'input'
            copy_files_call = [call('app_name', input_dir)]

            copy_files_mock.assert_has_calls(copy_files_call)

            expected_asset_application = [{
                    "roles": ["Sender"],
                    "values": [{"name": "phi", "value": 0.0, "scale_value": "pi"},
                               {"name": "theta", "value": 0.0, "scale_value": 2.0}
                               ]
                }
            ]

            self.experiment_data_local['meta']['description'] = f"description of {experiment_name} here"
            self.experiment_data_local['meta']['number_of_rounds'] = 1
            self.experiment_data_local['meta']['name'] = experiment_name
            self.experiment_data_local['asset'] = {'network': {'a': 'b'},
                                                   'application': expected_asset_application}

            write_mock.assert_called_once_with(Path('dummy') / 'test' / 'experiment.json', self.experiment_data_local)

    def test_delete_experiment_invalid_experiment_dir(self):
        with patch("adk.api.local_api.Path.is_dir", return_value=False), \
             patch("adk.api.local_api.Path.is_file", return_value=False):

            self.assertRaises(ExperimentDirectoryNotValid, self.local_api.delete_experiment, 'exp_dir', self.path)

    def test_delete_experiment_result_dir(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file") as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            # processed.json not a file
            is_dir_mock.side_effect = [True, False, False, True]
            is_file_mock.side_effect = [True, False]

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 1)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertTrue(delete_experiment_output)

            # processed.json is a file
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, False, False, True]
            is_file_mock.side_effect = [True, True]

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 2)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertTrue(delete_experiment_output)

            # rmdir directory ./result fails
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, False, False, True]
            is_file_mock.side_effect = [True, True]
            rmdir_mock.side_effect = [OSError, None]

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 2)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertFalse(delete_experiment_output)

    def test_delete_experiment_raw_output_dir(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file") as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch("adk.api.local_api.shutil.rmtree") as rmtree_mock, \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            # directory ./raw_output deleted
            is_dir_mock.side_effect = [True, False, True, False]
            is_file_mock.side_effect = [True]
            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 1)
            self.assertEqual(rmtree_mock.call_count, 1)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertTrue(delete_experiment_output)

    def test_delete_experiment_when_input_dir_not_completely_deleted(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file") as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch.object(LocalApi, "_LocalApi__get_config_file_names", return_value=['application.json',
                                                                                      'network.json']), \
             patch.object(LocalApi, "_LocalApi__get_simulator_file_names", return_value=['roles.yaml',
                                                                                         'network.yaml']), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.shutil.rmtree") as rmtree_mock, \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            # input dir not empty. Itis not deleted. Test that the other directories are deleted
            is_dir_mock.side_effect = [True, True, True, True]
            is_file_mock.side_effect = [True, True, True, True, True, True, True, True, True, True]
            rmdir_mock.side_effect = [OSError, None, None]

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 10)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertEqual(rmtree_mock.call_count, 1)
            self.assertFalse(delete_experiment_output)

    def test_delete_experiment_input_dir(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file") as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch.object(LocalApi, "_LocalApi__get_config_file_names", return_value=['application.json',
                                                                                      'network.json']), \
             patch.object(LocalApi, "_LocalApi__get_simulator_file_names", return_value=['roles.yaml',
                                                                                         'network.yaml']), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            # network.json found
            is_dir_mock.side_effect = [True, True, False, False]
            is_file_mock.side_effect = [True, True, True, True, True, True, True, True, True]
            rmdir_mock.side_effect = [None, None]

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 9)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertTrue(delete_experiment_output)

            # rmdir directory ./result fails
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, True, False, False]
            is_file_mock.side_effect = [True, True, True, True, True, True, True, True, True]
            rmdir_mock.side_effect = [OSError, None]

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 9)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertFalse(delete_experiment_output)

            # network.json not found
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, True, False, False]
            is_file_mock.side_effect = [True, True, False, True, True]
            rmdir_mock.side_effect = [None, None]

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 4)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertTrue(delete_experiment_output)

    def test_delete_experiment_with_experiment_dir(self):
        with patch("adk.api.local_api.Path.is_dir", return_value=True) as is_dir_mock, \
             patch("adk.api.local_api.Path.is_file", return_value=True) as is_file_mock, \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch("adk.api.local_api.shutil.rmtree") as rmtree_mock, \
             patch.object(LocalApi, "_LocalApi__get_config_file_names", return_value=['application.json',
                                                                                      'network.json']), \
             patch.object(LocalApi, "_LocalApi__get_simulator_file_names", return_value=['roles.yaml',
                                                                                         'network.yaml']), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 10)
            self.assertEqual(rmdir_mock.call_count, 3)
            self.assertEqual(rmtree_mock.call_count, 1)
            self.assertTrue(delete_experiment_output)

            # rmdir directory experiment_path fails
            unlink_mock.reset_mock()
            rmdir_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()

            is_dir_mock.side_effect = [True, False, False, False]
            is_file_mock.side_effect = [True]
            rmdir_mock.side_effect = [OSError]

            delete_experiment_output = self.local_api.delete_experiment('exp_dir', experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 1)
            self.assertEqual(rmdir_mock.call_count, 1)
            self.assertFalse(delete_experiment_output)

    def test_delete_experiment_no_experiment_directory(self):
        with patch("adk.api.local_api.Path.is_dir", return_value=True), \
             patch("adk.api.local_api.Path.is_file", return_value=True), \
             patch("adk.api.local_api.Path.unlink") as unlink_mock, \
             patch("adk.api.local_api.shutil.rmtree") as rmtree_mock, \
             patch.object(LocalApi, "_LocalApi__get_config_file_names", return_value=['application.json',
                                                                                      'network.json']), \
             patch.object(LocalApi, "_LocalApi__get_simulator_file_names", return_value=['roles.yaml',
                                                                                         'network.yaml']), \
             patch.object(LocalApi, "_LocalApi__get_role_names", return_value=['Sender', 'Receiver']), \
             patch("adk.api.local_api.os.rmdir") as rmdir_mock:

            delete_experiment_output = self.local_api.delete_experiment(None, experiment_path=Path('dummy'))
            self.assertEqual(unlink_mock.call_count, 10)
            self.assertEqual(rmdir_mock.call_count, 2)
            self.assertEqual(rmtree_mock.call_count, 1)
            self.assertFalse(delete_experiment_output)

    def test_validate_experiment(self):
        with patch.object(LocalApi, "_validate_experiment_json") as validate_experiment_json_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input:

            error_dict = {'error': [], 'warning': [], 'info': []}
            self.local_api.validate_experiment(self.path, error_dict)
            self.assertEqual(error_dict, self.error_dict)
            validate_experiment_json_mock.assert_called_once_with(experiment_path=self.path, error_dict=self.error_dict)
            validate_experiment_input.assert_called_once_with(experiment_path=self.path, error_dict=self.error_dict)

    def test_validate_experiment_json_all_ok(self):
        with patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch("adk.api.local_api.utils.read_json_file"), \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch.object(LocalApi, "get_experiment_data",
                          return_value=self.mock_experiment_data) as get_experiment_data_mock, \
             patch.object(LocalApi, "_get_network_info") as get_network_info_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_validate_experiment_nodes") as validate_experiment_nodes_mock, \
             patch.object(LocalApi, "_validate_experiment_channels") as validate_experiment_channels_mock, \
             patch.object(LocalApi, "_validate_experiment_roles") as validate_experiment_roles_mock, \
             patch.object(LocalApi, "_validate_experiment_application") as validate_experiment_application_mock:

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            get_network_info_mock.return_value = "slug"
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=self.error_dict)
            path_join_mock.assert_called_once()
            validate_json_schema_mock.assert_called_once_with(self.experiment_file_path, self.path)
            get_experiment_data_mock.assert_called_once_with(self.path)
            get_network_info_mock.assert_called_once_with = "slug"
            validate_experiment_nodes_mock.assert_called_once_with(self.experiment_file_path, self.mock_experiment_data,
                                                                   self.error_dict)
            validate_experiment_channels_mock.assert_called_once_with(self.experiment_file_path,
                                                                      self.mock_experiment_data, self.error_dict)
            validate_experiment_roles_mock.assert_called_once_with(self.path, self.mock_experiment_data,
                                                                   self.error_dict)
            validate_experiment_application_mock.assert_called_once_with(self.path, self.mock_experiment_data,
                                                                         self.error_dict)

    def test_validate_experiment_json_experiment_not_valid(self):
        with patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch.object(LocalApi, "get_experiment_data", return_value=self.mock_experiment_data), \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch("adk.api.local_api.os.path.join") as path_join_mock:

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = False, "message"
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict={'error': ['message'], 'warning': [],
                                                                               'info': []})
            path_join_mock.assert_called_once()
            validate_json_schema_mock.assert_called_once_with(self.experiment_file_path, self.path)

    def test_validate_experiment_json_location_not_valid(self):
        with patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch("adk.api.local_api.utils.read_json_file"), \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_get_network_info") as get_network_info_mock, \
             patch.object(LocalApi, "_validate_experiment_nodes"), \
             patch.object(LocalApi, "_validate_experiment_channels"), \
             patch.object(LocalApi, "_validate_experiment_roles"), \
             patch.object(LocalApi, "_validate_experiment_application"):

            experiment_data = {
                "meta": {
                    "backend": {
                        "location": "something_else",
                        "type": DEFAULT_BACKEND_TYPE
                    },
                    "number_of_rounds": 1,
                    "description": "exptest3: experiment description"
                },
                "asset": {
                    "network": {
                        "name": "Randstad",
                        "slug": "randstad",
                    }
                }
            }
            warning_message = f"In file '{self.experiment_file_path}': only 'local' or 'remote' is supported for " \
                              f"backend property 'location'"
            error_dict = {'error': [], 'warning': [warning_message], 'info': []}

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            get_experiment_data_mock.return_value = experiment_data
            get_network_info_mock.return_value = "slug"
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=error_dict)
            path_join_mock.assert_called_once()
            validate_json_schema_mock.assert_called_once_with(self.experiment_file_path, self.path)
            get_experiment_data_mock.assert_called_once_with(self.path)

    def test_validate_experiment_json_local_backend_type_not_valid(self):
        with patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch("adk.api.local_api.utils.read_json_file"), \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_get_network_info") as get_network_info_mock, \
             patch.object(LocalApi, "_validate_experiment_nodes"), \
             patch.object(LocalApi, "_validate_experiment_channels"), \
             patch.object(LocalApi, "_validate_experiment_roles"), \
             patch.object(LocalApi, "_validate_experiment_application"):

            experiment_data = {
                "meta": {
                    "backend": {
                        "location": "local",
                        "type": "not the default backend type"
                    },
                    "number_of_rounds": 1,
                    "description": "exptest3: experiment description"
                },
                "asset": {
                    "network": {
                        "name": "Randstad",
                        "slug": "randstad",
                    }
                }
            }
            warning_message = f"In file '{self.experiment_file_path}': local backend must be {DEFAULT_BACKEND_TYPE}"
            error_dict = {'error': [], 'warning': [warning_message], 'info': []}

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            get_experiment_data_mock.return_value = experiment_data
            get_network_info_mock.return_value = "slug"
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=error_dict)
            path_join_mock.assert_called_once()
            validate_json_schema_mock.assert_called_once_with(self.experiment_file_path, self.path)
            get_experiment_data_mock.assert_called_once_with(self.path)

    def test_validate_experiment_json_network_slug_does_not_exist(self):
        with patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch("adk.api.local_api.utils.read_json_file"), \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch.object(LocalApi, "_get_network_info") as get_network_info_mock, \
             patch.object(LocalApi, "_validate_experiment_application") as validate_experiment_application_mock:

            warning_message = f"In file '{self.experiment_file_path}': network '" \
                              f"{self.mock_experiment_data['asset']['network']['slug']}' does not exist"
            error_dict = {'error': [], 'warning': [warning_message], 'info': []}

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            get_experiment_data_mock.return_value = self.mock_experiment_data
            get_network_info_mock.return_value = None
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=error_dict)
            path_join_mock.assert_called_once()
            validate_json_schema_mock.assert_called_once_with(self.experiment_file_path, self.path)
            get_experiment_data_mock.assert_called_once_with(self.path)
            validate_experiment_application_mock.assert_called_once_with(self.path, self.mock_experiment_data,
                                                                         error_dict)

    def test_validate_experiment_json_non_required_values(self):
        # test get_experiment_round_set and get_experiment_id
        with patch.object(LocalApi, "is_experiment_local", return_value=False) as is_experiment_local_mock, \
             patch.object(LocalApi, "get_experiment_data",
                          return_value=self.mock_experiment_data) as get_experiment_data_mock:

            return_value = self.local_api.get_experiment_id(self.path)
            is_experiment_local_mock.assert_called_once()
            self.assertIsNone(return_value)

            is_experiment_local_mock.reset_mock()
            return_value = self.local_api.get_experiment_round_set(self.path)
            is_experiment_local_mock.assert_called_once()
            self.assertIsNone(return_value)

            # add data coming from experiment run
            self.mock_experiment_data["meta"]["experiment_id"] = 3
            self.mock_experiment_data["meta"]["round_set"] = 'fake_url'

            is_experiment_local_mock.reset_mock()
            return_value = self.local_api.get_experiment_id(self.path)
            is_experiment_local_mock.assert_called_once()
            self.assertEqual(return_value, '3')

            is_experiment_local_mock.reset_mock()
            return_value = self.local_api.get_experiment_round_set(self.path)
            is_experiment_local_mock.assert_called_once()
            self.assertEqual(return_value, 'fake_url')

    def test_validate_experiment_input_all_ok(self):
        with patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch.object(LocalApi, "_validate_experiment_json") as validate_experiment_json_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_validate_application_roles", return_value=True), \
             patch.object(LocalApi, "_LocalApi__check_all_experiment_input_files_exist") as exp_input_files_mock:

            is_dir_mock.return_value = True
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_json_mock.assert_called_once_with(experiment_path=self.path, error_dict=self.error_dict)
            exp_input_files_mock.assert_called_once_with(self.path / 'input', self.error_dict)
            is_dir_mock.assert_called_once()

    def test_validate_experiment_input_no_dir_exist(self):
        with patch.object(LocalApi, "_validate_experiment_json") as validate_experiment_json_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch("adk.api.local_api.Path.is_dir") as is_dir_mock:

            error_message = f"Required directory not found: '{self.path / 'input'}'"
            error_dict = {'error': [error_message], 'warning': [], 'info': []}

            is_dir_mock.return_value = False
            self.local_api.validate_experiment(self.path, self.error_dict)
            is_dir_mock.assert_called_once()
            validate_experiment_json_mock.assert_called_once_with(experiment_path=self.path, error_dict=error_dict)

    def test_validate_experiment_input_file_missing(self):
        with patch.object(LocalApi, "_validate_experiment_json") as validate_experiment_json_mock, \
             patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_LocalApi__get_config_file_names") as get_config_file_names_mock, \
             patch.object(LocalApi, "_validate_application_roles") as validate_application_roles_mock, \
             patch("adk.api.local_api.Path.is_file") as is_file_mock:

            error_message1 = f"'{self.path / 'input'}' should contain the file 'application.json'"
            error_message2 = f"'{self.path / 'input'}' should contain the file 'network.json'"
            error_message3 = f"'{self.path / 'input'}' should contain the file 'result.json'"

            error_dict = {'error': [error_message1, error_message2, error_message3], 'warning': [], 'info': []}
            is_dir_mock.return_value = True
            get_config_file_names_mock.return_value = self.config_files
            is_file_mock.return_value = False

            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_application_roles_mock.assert_called_once()
            is_dir_mock.assert_called_once()
            get_config_file_names_mock.assert_called_once()
            self.assertEqual(is_file_mock.call_count, 3)
            validate_experiment_json_mock.assert_called_once_with(experiment_path=self.path, error_dict=error_dict)

    def test_validate_experiment_input_experiment_data_invalid(self):
        with patch.object(LocalApi, "_validate_experiment_json") as validate_experiment_json_mock, \
             patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch.object(LocalApi, "_LocalApi__get_config_file_names") as get_config_file_names_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_validate_application_roles") as validate_application_roles_mock, \
             patch("adk.api.local_api.Path.is_file") as is_file_mock, \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock:

            error_dict = {'error': ["message", "message", "message"], 'warning': [], 'info': []}

            is_dir_mock.return_value = True
            get_config_file_names_mock.return_value = self.config_files
            is_file_mock.return_value = True
            validate_json_schema_mock.return_value = False, "message"

            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_application_roles_mock.assert_called_once()
            is_dir_mock.assert_called_once()
            get_config_file_names_mock.assert_called_once()
            self.assertEqual(is_file_mock.call_count, 3)
            self.assertEqual(validate_json_schema_mock.call_count, 3)
            validate_experiment_json_mock.assert_called_once_with(experiment_path=self.path, error_dict=error_dict)

    def test_validate_experiment_input_missing_role_file_names(self):
        with patch.object(LocalApi, "_validate_experiment_json") as validate_experiment_json_mock, \
             patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch.object(LocalApi, "_LocalApi__get_config_file_names") as get_config_file_names_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch("adk.api.local_api.Path.is_file") as is_file_mock, \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch.object(LocalApi, "_validate_application_roles") as validate_application_roles_mock, \
             patch.object(LocalApi, "_LocalApi__get_role_file_names") as get_role_file_names_mock:

            error_message1 = f"'{self.path / 'input'}' is missing the file: '{self.roles[0]}'"
            error_message2 = f"'{self.path / 'input'}' is missing the file: '{self.roles[1]}'"
            error_dict = {'error': [error_message1, error_message2], 'warning': [], 'info': []}

            is_dir_mock.return_value = True
            get_config_file_names_mock.return_value = self.config_files
            is_file_mock.side_effect = [True, True, False, False, True]
            validate_json_schema_mock.return_value = True, None
            get_role_file_names_mock.return_value = self.roles

            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_application_roles_mock.assert_called_once()
            is_dir_mock.assert_called_once()
            get_config_file_names_mock.assert_called_once()
            self.assertEqual(is_file_mock.call_count, 5)
            self.assertEqual(validate_json_schema_mock.call_count, 3)
            get_role_file_names_mock.assert_called_once_with(self.path / "input")
            validate_experiment_json_mock.assert_called_once_with(experiment_path=self.path, error_dict=error_dict)

    def test_validate_experiment_input_missing_application_roles(self):
        with patch.object(LocalApi, "_validate_experiment_json") as validate_experiment_json_mock, \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch("adk.api.local_api.Path.is_dir") as is_dir_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "_LocalApi__check_all_experiment_input_files_exist") as check_all_input_files_mock,\
             patch.object(LocalApi, "_LocalApi__get_role_names") as get_roles_mock:

            error_1 = f"In file '{self.path / 'experiment.json'}': role 'role2' is not valid for the application"
            error_dict_expected = {'error': [error_1], 'warning': [], 'info': []}

            is_dir_mock.return_value = True
            get_roles_mock.reset_mock()
            get_roles_mock.return_value = ['role1', 'role6']

            mock_exp_data_for_roles = self.mock_experiment_data
            mock_exp_data_for_roles["asset"]["network"]["roles"] = {"role1": "n1", "role2": "n2"}
            get_experiment_data_mock.return_value = mock_exp_data_for_roles

            self.local_api.validate_experiment(self.path, self.error_dict)

            self.assertDictEqual(self.error_dict, error_dict_expected)
            validate_experiment_json_mock.assert_called_once()
            check_all_input_files_mock.assert_called_once()
            is_dir_mock.assert_called_once()

    def test_validate_experiment_nodes(self):
        with patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch("adk.api.local_api.utils.read_json_file"), \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch.object(LocalApi, "_get_network_info"), \
             patch.object(LocalApi, "_validate_experiment_channels"), \
             patch.object(LocalApi, "_validate_experiment_roles"), \
             patch.object(LocalApi, "_validate_template_parameters"), \
             patch.object(LocalApi, "_validate_experiment_application"), \
             patch.object(LocalApi, "_get_network_nodes") as get_network_nodes_mock:

            experiment_data_too_many_nodes = {
                "meta": {
                    "backend": {
                        "location": "local",
                        "type": DEFAULT_BACKEND_TYPE
                    },
                    "number_of_rounds": 1,
                    "description": "exptest3: experiment description"
                },
                "asset": {
                    "network": {
                        "name": "Randstad",
                        "slug": "randstad",
                        "nodes": [{"slug": "n1", "node_parameters": None, "qubits": self.dummy_qubit},
                                  {"slug": "n2", "node_parameters": None, "qubits": self.dummy_qubit},
                                  {"slug": "n3", "node_parameters": None, "qubits": self.dummy_qubit},
                                  {"slug": "n4", "node_parameters": None, "qubits": self.dummy_qubit},
                                  {"slug": "n5", "node_parameters": None, "qubits": self.dummy_qubit},
                                  {"slug": "n6", "node_parameters": None, "qubits": self.dummy_qubit}],
                    }
                }
            }

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            get_experiment_data_mock.return_value = self.mock_experiment_data
            get_network_nodes_mock.return_value = self.all_network_nodes
            self.local_api.validate_experiment(self.path, self.error_dict)
            get_network_nodes_mock.assert_called_once()
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=self.error_dict)

            # length of experiment_nodes is greater than network_nodes and n6 does not exist in network
            error_message1 = f"In file '{self.path / 'experiment.json'}': too many nodes used in network " \
                             f"'{experiment_data_too_many_nodes['asset']['network']['slug']}'. Maximum amount of " \
                             f"nodes that can be used: {len(self.all_network_nodes['randstad'])}"

            error_message2 = f"In file '{self.path / 'experiment.json'}': node 'n6' does not exist "  \
                             f"or does not belong to the network '" \
                             f"{experiment_data_too_many_nodes['asset']['network']['slug']}'"

            error_dict = {'error': [error_message1, error_message2], 'warning': [], 'info': []}
            get_network_nodes_mock.reset_mock()
            get_experiment_data_mock.reset_mock()
            validate_experiment_input_mock.reset_mock()
            get_experiment_data_mock.return_value = experiment_data_too_many_nodes
            self.local_api.validate_experiment(self.path, self.error_dict)
            get_network_nodes_mock.assert_called_once()
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=error_dict)

    def test_validate_experiment_channels(self):
        with patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch("adk.api.local_api.utils.read_json_file"), \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch.object(LocalApi, "_get_network_info"), \
             patch.object(LocalApi, "_validate_experiment_nodes"), \
             patch.object(LocalApi, "_validate_experiment_roles"), \
             patch.object(LocalApi, "_validate_experiment_application"), \
             patch.object(LocalApi, "_validate_template_parameters"), \
             patch.object(LocalApi, "_get_channel_info") as get_channel_info_mock, \
             patch.object(LocalApi, "_get_channels_for_network") as get_channels_for_network_mock:

            experiment_data_too_many_channels = {
                "meta": {
                    "backend": {
                        "location": "local",
                        "type": DEFAULT_BACKEND_TYPE
                    },
                    "number_of_rounds": 1,
                    "description": "exptest3: experiment description"
                },
                "asset": {
                    "network": {
                        "name": "Randstad",
                        "slug": "randstad",
                        "channels": [{"slug": "n1-n2", "parameters": None, "node1": "n1", "node2": "n2"},
                                     {"slug": "n2-n3", "parameters": None, "node1": "n2", "node2": "n3"},
                                     {"slug": "n4-n3", "parameters": None, "node1": "n4", "node2": "n3"},
                                     {"slug": "n4-n5", "parameters": None, "node1": "n4", "node2": "n5"},
                                     {"slug": "n5-n6", "parameters": None, "node1": "n5", "node2": "n6"}]
                    }
                }
            }

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            get_experiment_data_mock.return_value = self.mock_experiment_data
            get_channels_for_network_mock.return_value = self.all_network_channels
            channel_info_list = [{"slug": "n1-n2", "node1": "n1", "node2": "n2"},
                                 {"slug": "n2-n3", "node1": "n2", "node2": "n3"},
                                 {"slug": "n4-n3", "node1": "n4", "node2": "n3"},
                                 {"slug": "n4-n5", "node1": "n4", "node2": "n5"}]
            get_channel_info_mock.side_effect = channel_info_list
            self.local_api.validate_experiment(self.path, self.error_dict)
            get_channels_for_network_mock.assert_called_once_with(network_slug='randstad')
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=self.error_dict)

            # length of experiment_channels is greater than network_nodes and n5-n6 does not exist in network
            error_message1 = f"In file {self.path / 'experiment.json'}: too many channels used in network " \
                             f"'{experiment_data_too_many_channels['asset']['network']['slug']}'. Maximum amount of " \
                             f"channels that can be used: " \
                             f"{len(self.mock_experiment_data['asset']['network']['channels'])}"

            error_message2 = f"In file '{self.path / 'experiment.json'}': channel 'n5-n6' does not exist or is " \
                             f"not a valid channel for network " \
                             f"'{experiment_data_too_many_channels['asset']['network']['slug']}'"

            error_dict = {'error': [error_message1, error_message2], 'warning': [], 'info': []}

            get_channels_for_network_mock.reset_mock()
            get_experiment_data_mock.reset_mock()
            validate_experiment_input_mock.reset_mock()
            get_channels_for_network_mock.return_value = self.all_network_channels
            get_experiment_data_mock.return_value = experiment_data_too_many_channels
            get_channel_info_mock.reset_mock()
            channel_info_list = [{"slug": "n1-n2", "node1": "n1", "node2": "n2"},
                                 {"slug": "n2-n3", "node1": "n2", "node2": "n3"},
                                 {"slug": "n4-n3", "node1": "n4", "node2": "n3"},
                                 {"slug": "n4-n5", "node1": "n4", "node2": "n5"},
                                 {"slug": "n5-n6", "node1": "n5", "node2": "n6"}]
            get_channel_info_mock.side_effect = channel_info_list
            self.error_dict = get_empty_errordict()
            self.local_api.validate_experiment(self.path, self.error_dict)
            get_channels_for_network_mock.assert_called_once_with(network_slug='randstad')
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=error_dict)

            # If network_channels is None
            error_dict = {"error": [f"No channels found for network '{'randstad'}'"], "warning": [], "info": []}
            get_channels_for_network_mock.reset_mock()
            validate_experiment_input_mock.reset_mock()
            get_channels_for_network_mock.return_value = None
            self.error_dict = get_empty_errordict()
            self.local_api.validate_experiment(self.path, self.error_dict)
            get_channels_for_network_mock.assert_called_once_with(network_slug='randstad')
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=error_dict)

            get_channel_info_mock.reset_mock()
            channel_info_list = [{"slug": "n1-n2", "node1": "n1", "node2": "n2"}]
            get_channel_info_mock.side_effect = channel_info_list
            get_channels_for_network_mock.reset_mock()
            validate_experiment_input_mock.reset_mock()
            get_channels_for_network_mock.return_value = self.all_network_channels
            experiment_data_incorrect_channel_nodes = {
                "meta": {
                    "backend": {
                        "location": "local",
                        "type": DEFAULT_BACKEND_TYPE
                    },
                    "number_of_rounds": 1,
                    "description": "exptest3: experiment description"
                },
                "asset": {
                    "network": {
                        "name": "Randstad",
                        "slug": "randstad",
                        "channels": [{"slug": "n1-n2", "node1": "n", "node2": "n", "parameters": None}]
                    }
                }
            }
            get_experiment_data_mock.reset_mock()
            get_experiment_data_mock.return_value = experiment_data_incorrect_channel_nodes
            error_1 = f"In file '{self.path / 'experiment.json'}': value 'n' of node 'node1' in channel 'n1-n2' " \
                      "does not exist or is not a valid node for the channel"
            error_2 = f"In file '{self.path / 'experiment.json'}': value 'n' of node 'node2' in channel 'n1-n2' " \
                      "does not exist or is not a valid node for the channel"
            error_dict = {'error': [error_1, error_2], 'warning': [], 'info': []}
            self.error_dict = get_empty_errordict()
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path, error_dict=error_dict)

    def test_validate_experiment_roles(self):
        with patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch.object(LocalApi, "_get_network_info"), \
             patch.object(LocalApi, "_validate_experiment_nodes"), \
             patch.object(LocalApi, "_validate_experiment_channels"), \
             patch.object(LocalApi, "_validate_experiment_application"), \
             patch.object(LocalApi, "_validate_template_parameters"), \
             patch.object(LocalApi, "_get_channel_info"), \
             patch.object(LocalApi, "_LocalApi__get_role_names") as get_roles_mock, \
             patch.object(LocalApi, "_get_network_nodes") as get_nodes_mock, \
             patch.object(LocalApi, "_get_channels_for_network"):

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            get_experiment_data_mock.return_value = self.mock_experiment_data
            get_roles_mock.return_value = ['role1', 'role2']
            get_nodes_mock.return_value = {"randstad": ["n1", "n2", "n3"]}
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path,
                                                                   error_dict=self.error_dict)

            validate_experiment_input_mock.reset_mock()
            get_roles_mock.reset_mock()
            get_roles_mock.return_value = ['role1', 'role6']
            get_nodes_mock.reset_mock()
            get_nodes_mock.return_value = {"randstad": ["n0"]}
            get_experiment_data_mock.reset_mock()
            mock_exp_data_for_roles = self.mock_experiment_data
            mock_exp_data_for_roles["asset"]["network"]["roles"] = {"role1": "n1", "role2": "n1"}
            get_experiment_data_mock.return_value = mock_exp_data_for_roles
            error_1 = f"In file '{self.path / 'experiment.json'}': node 'n1' used for role 'role1' is not valid " \
                      "for the application"
            error_2 = f"In file '{self.path / 'experiment.json'}': node 'n1' used for role 'role2' is not valid " \
                      "for the application"
            error_3 = f"In file '{self.path / 'experiment.json'}': node 'n1' is used for multiple roles"
            error_dict = {'error': [error_1, error_2, error_3], 'warning': [], 'info': []}
            self.error_dict = get_empty_errordict()
            self.local_api.validate_experiment(self.path, self.error_dict)
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path, error_dict=error_dict)

    def test_validate_template_parameters(self): # pylint: disable=R0914 too-many-locals
        with patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch.object(LocalApi, "_get_network_info"), \
             patch.object(LocalApi, "_validate_experiment_nodes"), \
             patch.object(LocalApi, "_validate_experiment_roles"), \
             patch.object(LocalApi, "_validate_experiment_application"), \
             patch.object(LocalApi, "_get_channel_info") as get_channel_info_mock, \
             patch.object(LocalApi, "_get_template_params_max_min_range") as get_templates_range_mock, \
             patch.object(LocalApi, "_get_channels_for_network") as get_channels_for_network_mock:

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            dummy_channel_params_1 = [
                {
                    "slug": "elementary-link-fidelity",
                    "values": [
                        {
                            "name": "fidelity",
                            "value": 12344.0,
                            "scale_value": 1.0
                        }
                    ]
                },
                {
                    "slug": "relaxation-time",
                    "values": [
                        {
                            "name": "t1",
                            "value": "string_value",
                            "scale_value": 1.0
                        }
                    ]
                }
            ]
            dummy_channel_params_2 = [
                {
                    "slug": "unknown_param",
                    "values": [
                        {
                            "name": "x",
                            "value": 1.0,
                            "scale_value": 1.0
                        }
                    ]
                },
                {
                    "slug": "relaxation-time",
                    "values": [
                        {
                            "name": "incorrect_name",
                            "value": 1.0,
                            "scale_value": 1.0
                        }
                    ]
                }
            ]
            mock_exp_data = self.mock_experiment_data
            mock_exp_data["asset"]["network"]["channels"] = [
                {"slug": "n1-n2", "parameters": dummy_channel_params_1,
              "node1": "n1", "node2": "n2"},
                {"slug": "n2-n3", "parameters": dummy_channel_params_2,
              "node1": "n2", "node2": "n3"},
            ]
            get_experiment_data_mock.return_value = mock_exp_data
            get_channels_for_network_mock.return_value = self.all_network_channels

            channel_info_list = [{"slug": "n1-n2", "node1": "n1", "node2": "n2",
                                  "parameters": dummy_channel_params_1,
                                  },
                                 {"slug": "n2-n3", "node1": "n2", "node2": "n3",
                                  "parameters": dummy_channel_params_2,
                                  },
                                 ]
            get_channel_info_mock.side_effect = channel_info_list

            get_templates_range_mock.return_value = {
                'elementary-link-fidelity': {
                    'fidelity': {'maximum_value': 1.0, 'minimum_value': 0.5}
                },
                'gate-fidelity': {
                    'gate_fidelity': {'maximum_value': 1.0, 'minimum_value': 0.5}
                },
                'relaxation-time': {
                    't1': {'maximum_value': 1000, 'minimum_value': 0}
                },
                'dephasing-time': {
                    't2': {'maximum_value': 1000, 'minimum_value': 0}
                }
            }
            error_1 = f"In file '{self.path / 'experiment.json'}': value '12344.0' of param " \
                      "'elementary-link-fidelity' -> 'fidelity' in channel 'n1-n2' is not within the allowed range " \
                      "of minimum (0.5) and maximum (1.0)"
            error_2 = f"In file '{self.path / 'experiment.json'}': value 'string_value' of param " \
                      "'relaxation-time' -> 't1' in channel 'n1-n2' is not of the required type (integer or float)"
            error_3 = f"In file '{self.path / 'experiment.json'}': parameter 'unknown_param' in channel 'n2-n3' " \
                      "does not exist"
            error_4 = f"In file '{self.path / 'experiment.json'}': 'incorrect_name' is not valid for param " \
                      "'relaxation-time' in channel 'n2-n3'"
            error_dict = {'error': [error_1, error_2, error_3, error_4], 'warning': [], 'info': []}
            self.local_api.validate_experiment(self.path, self.error_dict)
            get_channels_for_network_mock.assert_called_once_with(network_slug='randstad')
            validate_experiment_input_mock.assert_called_once_with(experiment_path=self.path, error_dict=error_dict)

    def test_validate_experiment_application(self):
        with patch.object(LocalApi, "_validate_experiment_input") as validate_experiment_input_mock, \
             patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock, \
             patch("adk.api.local_api.os.path.join") as path_join_mock, \
             patch("adk.api.local_api.validate_json_schema") as validate_json_schema_mock, \
             patch.object(LocalApi, "is_experiment_local", return_value=True), \
             patch.object(LocalApi, "get_experiment_data") as get_experiment_data_mock, \
             patch.object(LocalApi, "_get_network_info"), \
             patch.object(LocalApi, "_validate_experiment_nodes"), \
             patch.object(LocalApi, "_validate_experiment_channels"), \
             patch.object(LocalApi, "_validate_experiment_roles"), \
             patch("adk.api.local_api.Path.is_file") as is_file_mock:

            experiment_data = {
                "meta": {
                    "backend": {
                        "location": "local",
                        "type": DEFAULT_BACKEND_TYPE
                    },
                    "number_of_rounds": 1,
                    "description": "exptest3: experiment description"
                },
                "asset": {
                    "network": {
                        "slug": "randstad"
                    },
                    "application": [
                        {
                            "roles": [
                                "sender"
                            ],
                            "values": [
                                {
                                    "name": "x",
                                    "value": 0,
                                    "scale_value": 1.0
                                }
                            ]
                        }
                    ]
                }
            }
            network_data = {
                'networks': [
                    'randstad',
                    'europe',
                    'the-netherlands'
                ],
                'roles': [
                    'sender',
                    'receiver'
                ]
            }
            get_experiment_data_mock.return_value = experiment_data
            read_json_file_mock.side_effect = [
                network_data
            ]

            path_join_mock.return_value = self.path
            validate_json_schema_mock.return_value = True, None
            is_file_mock.return_value = True
            read_json_file_mock.return_value = {'networks': ['randstad', 'europe', 'the-netherlands'],
                                                'roles': ['sender', 'receiver']}

            self.local_api.validate_experiment(self.path, self.error_dict)
            is_file_mock.assert_called_once()
            read_json_file_mock.assert_called_with(self.path / "input/network.json")
            self.assertEqual(read_json_file_mock.call_count, 1)

    def test_run_experiment_application_not_changed(self):
        with patch.object(self.config_manager, "application_exists") as application_exists_mock, \
             patch("adk.api.local_api.Path.exists") as mock_path_exists, \
             patch("adk.api.local_api.filecmp.cmp") as mock_filecmp_cmp, \
             patch.object(LocalApi, "get_application_config") as get_application_config_mock, \
             patch.object(LocalApi, "get_experiment_asset") as get_experiment_asset_mock, \
             patch.object(LocalApi, "get_experiment_application") as get_experiment_application_mock, \
             patch.object(LocalApi, "set_experiment_asset_application") as set_experiment_asset_application_mock, \
             patch.object(LocalApi, "_LocalApi__copy_input_files_from_application") as copy_files_mock, \
             patch.object(RoundSetManager, "process") as process_mock:

            app_path = self.path
            get_experiment_application_mock.return_value = "the_app"
            experiment_path = Path('dummy')
            experiment_input_path = experiment_path / 'input'
            application_exp = experiment_input_path / 'application.json'
            application_app = Path(app_path) / 'config' / 'application.json'

            application_exists_mock.return_value = True, str(app_path)
            mock_path_exists.side_effect = [True, True]
            mock_filecmp_cmp.return_value = True
            get_application_config_mock.return_value = self.mock_app_config
            self.local_api.run_experiment(experiment_path, True)
            process_mock.assert_called_once_with(None)
            mock_filecmp_cmp.assert_called_once_with(str(application_app), str(application_exp), shallow=False)
            get_application_config_mock.assert_not_called()
            get_experiment_asset_mock.assert_called_once()
            set_experiment_asset_application_mock.assert_not_called()
            copy_files_mock.assert_called_once_with("the_app", experiment_input_path)

    def test_run_experiment_application_not_updated(self):
        with patch.object(LocalApi, "get_experiment_asset") as get_experiment_asset_mock, \
             patch.object(LocalApi, "_LocalApi__prepare_input_files") as prepare_input_files_mock, \
             patch.object(RoundSetManager, "process") as process_mock:

            app_path = self.path
            experiment_path = Path('dummy')
            experiment_input_path = experiment_path / 'input'
            application_exp = experiment_input_path / 'application.json'
            application_app = Path(app_path) / 'config' / 'application.json'

            self.local_api.run_experiment(experiment_path, False)
            prepare_input_files_mock.assert_not_called()
            process_mock.assert_called_once_with(None)
            get_experiment_asset_mock.assert_called_once()

    def test_run_experiment_application_config_file_not_found(self):
        with patch.object(self.config_manager, "application_exists") as application_exists_mock, \
             patch("adk.api.local_api.Path.exists") as mock_path_exists, \
             patch("adk.api.local_api.filecmp.cmp") as mock_filecmp_cmp, \
             patch.object(LocalApi, "get_application_config") as get_application_config_mock, \
             patch.object(LocalApi, "get_experiment_asset") as get_experiment_asset_mock, \
             patch.object(LocalApi, "get_experiment_application") as get_experiment_application_mock, \
             patch.object(LocalApi, "set_experiment_asset_application") as set_experiment_asset_application_mock, \
             patch.object(LocalApi, "_LocalApi__copy_input_files_from_application") as copy_files_mock, \
             patch.object(RoundSetManager, "process") as process_mock:

            get_experiment_application_mock.return_value = "the_app"
            experiment_path = Path('dummy')
            experiment_input_path = experiment_path / 'input'
            application_exists_mock.return_value = True, str(self.path)
            mock_path_exists.side_effect = [False, True]
            mock_filecmp_cmp.return_value = True
            get_application_config_mock.return_value = self.mock_app_config
            self.local_api.run_experiment(experiment_path, True, 30)
            process_mock.assert_called_once_with(30)
            mock_filecmp_cmp.assert_not_called()
            get_application_config_mock.assert_not_called()
            get_experiment_asset_mock.assert_called_once()
            set_experiment_asset_application_mock.assert_not_called()
            copy_files_mock.assert_called_once_with("the_app", experiment_input_path)

    def test_run_experiment_application_changed(self):
        with patch.object(self.config_manager, "application_exists") as application_exists_mock, \
             patch("adk.api.local_api.Path.exists") as mock_path_exists, \
             patch("adk.api.local_api.filecmp.cmp") as mock_filecmp_cmp, \
             patch.object(LocalApi, "get_application_config") as get_application_config_mock, \
             patch.object(LocalApi, "get_experiment_asset") as get_experiment_asset_mock, \
             patch.object(LocalApi, "get_experiment_application") as get_experiment_application_mock, \
             patch.object(LocalApi, "set_experiment_asset_application") as set_experiment_asset_application_mock, \
             patch.object(LocalApi, "_LocalApi__copy_input_files_from_application") as copy_files_mock, \
             patch.object(RoundSetManager, "process") as process_mock:

            get_experiment_application_mock.return_value = "the_app"
            experiment_path = Path('dummy')
            experiment_input_path = experiment_path / 'input'
            application_exists_mock.return_value = True, str(self.path)
            mock_path_exists.side_effect = [True, True]
            mock_filecmp_cmp.return_value = False
            get_application_config_mock.return_value = self.mock_app_config
            self.local_api.run_experiment(experiment_path, True)
            get_experiment_asset_mock.assert_called_once()
            process_mock.assert_called_once_with(None)
            expected_asset_application = [{'roles': ['Sender'],
                                          'values': [{'name': 'phi', 'value': 0.0, 'scale_value': 'pi'},
                                                     {'name': 'theta', 'value': 0.0, 'scale_value': 2.0}
                                                     ]
                                          }]
            set_experiment_asset_application_mock.assert_called_once_with(expected_asset_application, experiment_path)
            copy_files_mock.assert_called_once_with("the_app", experiment_input_path)

    def test_get_results(self):
        with patch.object(OutputConverter, "convert") as convert_mock:
            self.local_api.get_results(experiment_path=Path('dummy'))
            convert_mock.assert_called_once_with(round_number=1)

    def test_is_network_available(self):
        with patch.object(LocalApi, "_get_network_slug") as get_network_slug_mock:
            get_network_slug_mock.return_value = 'network-slug-1'
            mock_app_config = {'application': [{'app': 'foo'}],
                               'network': {'networks': ['network-slug-2', 'network-slug-1']}}
            network_available = self.local_api.is_network_available('network name', mock_app_config)

            get_network_slug_mock.assert_called_once_with('network name')
            self.assertTrue(network_available)

            get_network_slug_mock.reset_mock()
            get_network_slug_mock.return_value = 'network-slug-unknown'
            network_available = self.local_api.is_network_available('network name 1', mock_app_config)

            get_network_slug_mock.assert_called_once_with('network name 1')
            self.assertFalse(network_available)

    def test_get_network_data(self):
        with patch.object(LocalApi, "_get_network_nodes") as get_nodes_mock, \
             patch.object(LocalApi, "_get_network_slug") as get_network_slug_mock, \
             patch.object(LocalApi, "_get_channels_for_network") as get_channels_for_network_mock, \
             patch.object(LocalApi, "_get_channel_info") as get_channel_info_mock, \
             patch.object(LocalApi, "_get_node_info") as get_node_info_mock, \
             patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock:

            channel_info_list = [{"slug": "c1-slug"}, {"slug": "c2-slug"}, {"slug": "c3-slug"}]
            node_info_list = [{"slug": "n1-slug"}, {"slug": "n2-slug"}, {"slug": "n3-slug"}]

            get_nodes_mock.return_value = {"network-slug-1": ["n1", "n2", "n3"]}
            get_network_slug_mock.return_value = 'network-slug-1'
            get_channels_for_network_mock.return_value = ['c1', 'c2', 'c3']
            get_channel_info_mock.side_effect = channel_info_list
            get_node_info_mock.side_effect = node_info_list

            # Initialize the data for networks, channels, nodes and templates
            read_json_file_mock.side_effect = [self.mock_network_data, self.mock_channel_data,
                                               self.mock_node_data, self.mock_template_data]

            test_local_api = LocalApi(config_manager=self.config_manager)

            data = test_local_api.get_network_data('Network 1')
            get_network_slug_mock.assert_called_once_with('Network 1')
            get_channels_for_network_mock.assert_called_once_with(network_slug='network-slug-1')
            get_channel_info_mock.assert_has_calls([call(channel_slug='c1'), call(channel_slug='c2'),
                                                    call(channel_slug='c3')])
            get_node_info_mock.assert_has_calls([call(node_slug='n1'), call(node_slug='n2'), call(node_slug='n3')])

            self.assertEqual(data['name'], 'Network 1')
            self.assertEqual(data['slug'], 'network-slug-1')
            self.assertEqual(data['channels'], channel_info_list)
            self.assertEqual(data['nodes'], node_info_list)

    def test__fill_asset_role_information(self):
        with patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_node_information") as fill_asset_node_information_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_channel_information") as fill_asset_channel_information_mock:

            mock_network_data = {
                "name": 'Network 1',
                "slug": 'network-slug-1',
                "channels": self.channel_info_list,
                "nodes": self.node_info_list,
            }

            mock_app_config = {'application': [{'app': 'foo'}],
                               'network': {'networks': ['network-slug-2', 'network-slug-1'],
                                           'roles': ['role1', 'role2']}
                               }

            read_json_file_mock.return_value = self.mock_template_data
            test_local_api = LocalApi(config_manager=self.config_manager)
            asset_network = test_local_api.create_asset_network(network_data=mock_network_data,
                                                                app_config=mock_app_config)
            # Check Roles data
            self.assertIn('roles', asset_network)
            self.assertIn('role1', asset_network['roles'])
            self.assertIn('role2', asset_network['roles'])
            fill_asset_channel_information_mock.assert_called_once()
            fill_asset_node_information_mock.assert_called_once()

    def test__fill_asset_channel_information(self):
        with patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_role_information") as fill_asset_role_information_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_node_information") as fill_asset_node_information_mock:

            mock_network_data = {
                "name": 'Network 1',
                "slug": 'network-slug-1',
                "channels": self.channel_info_list,
                "nodes": self.node_info_list,
            }

            mock_app_config = {'application': [{'app': 'foo'}],
                               'network': {'networks': ['network-slug-2', 'network-slug-1'],
                                           'roles': ['role1', 'role2']}
                               }

            read_json_file_mock.return_value = self.mock_template_data
            test_local_api = LocalApi(config_manager=self.config_manager)
            asset_network = test_local_api.create_asset_network(network_data=mock_network_data,
                                                                app_config=mock_app_config)
            # Check Channels data
            self.assertIn('channels', asset_network)
            self.assertEqual(len(asset_network["channels"]), 3)
            for channel in asset_network['channels']:
                self.assertIn('parameters', channel)
                self.assertNotIn('filled_parameters', channel)

            expected_param_1_dict = {'slug': 'param-1',
                                     'values': [{'name': 'fidelity', 'value': 1.0, 'scale_value': 1.0}]}
            expected_param_2_dict = {'slug': 'param-2',
                                     'values': [{'name': 't1', 'value': 0, 'scale_value': 12.0}]}

            c1_channel = asset_network['channels'][0]
            self.assertEqual((c1_channel["slug"]), "c1-slug")
            self.assertEqual(len(c1_channel["parameters"]), 2)
            self.assertDictEqual(c1_channel["parameters"][0], expected_param_1_dict)
            self.assertDictEqual(c1_channel["parameters"][1], expected_param_2_dict)

            c2_channel = asset_network['channels'][1]
            self.assertEqual((c2_channel["slug"]), "c2-slug")
            self.assertEqual(len(c2_channel["parameters"]), 1)
            self.assertDictEqual(c2_channel["parameters"][0], expected_param_1_dict)

            c3_channel = asset_network['channels'][2]
            self.assertEqual((c3_channel["slug"]), "c3-slug")
            self.assertEqual(len(c3_channel["parameters"]), 1)
            self.assertDictEqual(c3_channel["parameters"][0], expected_param_2_dict)

            fill_asset_role_information_mock.assert_called_once()
            fill_asset_node_information_mock.assert_called_once()

    def test__fill_asset_node_information(self):
        with patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_role_information") as fill_asset_role_information_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_channel_information") as fill_asset_channel_information_mock:

            mock_network_data = {
                "name": 'Network 1',
                "slug": 'network-slug-1',
                "channels": self.channel_info_list,
                "nodes": self.node_info_list,
            }

            mock_app_config = {'application': [{'app': 'foo'}],
                               'network': {'networks': ['network-slug-2', 'network-slug-1'],
                                           'roles': ['role1', 'role2']}
                               }

            read_json_file_mock.return_value = self.mock_template_data
            test_local_api = LocalApi(config_manager=self.config_manager)
            asset_network = test_local_api.create_asset_network(network_data=mock_network_data,
                                                                app_config=mock_app_config)

            expected_param_1_dict = {'slug': 'param-1',
                                     'values': [{'name': 'fidelity', 'value': 1.0, 'scale_value': 1.0}]}
            expected_param_2_dict = {'slug': 'param-2',
                                     'values': [{'name': 't1', 'value': 0, 'scale_value': 12.0}]}

            # Check Nodes data
            self.assertIn('nodes', asset_network)
            self.assertEqual(len(asset_network["nodes"]), 3)
            for node in asset_network['nodes']:
                self.assertIn('node_parameters', node)
                self.assertIn('qubits', node)
                self.assertNotIn('number_of_qubits', node)
                self.assertNotIn('qubit_parameters', node)
                self.assertNotIn('filled_node_parameters', node)

            # Node 1 (n1-slug)
            n1_node = asset_network['nodes'][0]
            self.assertEqual((n1_node["slug"]), "n1-slug")
            self.assertEqual(len(n1_node["node_parameters"]), 2)
            self.assertDictEqual(n1_node["node_parameters"][0], expected_param_1_dict)
            self.assertDictEqual(n1_node["node_parameters"][1], expected_param_2_dict)

            self.assertEqual(len(n1_node["qubits"]), 2)

            self.assertEqual(n1_node["qubits"][0]['qubit_id'], 0)
            self.assertEqual(len(n1_node["qubits"][0]['qubit_parameters']), 2)
            self.assertDictEqual(n1_node["qubits"][0]['qubit_parameters'][0], expected_param_1_dict)
            self.assertDictEqual(n1_node["qubits"][0]['qubit_parameters'][1], expected_param_2_dict)

            self.assertEqual(n1_node["qubits"][1]['qubit_id'], 1)
            self.assertEqual(len(n1_node["qubits"][1]['qubit_parameters']), 2)
            self.assertDictEqual(n1_node["qubits"][1]['qubit_parameters'][0], expected_param_1_dict)
            self.assertDictEqual(n1_node["qubits"][1]['qubit_parameters'][1], expected_param_2_dict)

            # Node 2 (n2-slug)
            n2_node = asset_network['nodes'][1]
            self.assertEqual((n2_node["slug"]), "n2-slug")
            self.assertEqual(len(n2_node["node_parameters"]), 1)
            self.assertDictEqual(n2_node["node_parameters"][0], expected_param_2_dict)

            self.assertEqual(len(n2_node["qubits"]), 1)

            self.assertEqual(n2_node["qubits"][0]['qubit_id'], 0)
            self.assertEqual(len(n2_node["qubits"][0]['qubit_parameters']), 1)
            self.assertDictEqual(n2_node["qubits"][0]['qubit_parameters'][0], expected_param_1_dict)

            # Node 3 (n3-slug)
            n3_node = asset_network['nodes'][2]
            self.assertEqual((n3_node["slug"]), "n3-slug")
            self.assertEqual(len(n3_node["node_parameters"]), 1)
            self.assertDictEqual(n3_node["node_parameters"][0], expected_param_1_dict)

            self.assertEqual(len(n3_node["qubits"]), 1)

            self.assertEqual(n3_node["qubits"][0]['qubit_id'], 0)
            self.assertEqual(len(n3_node["qubits"][0]['qubit_parameters']), 1)
            self.assertDictEqual(n3_node["qubits"][0]['qubit_parameters'][0], expected_param_2_dict)

            fill_asset_role_information_mock.assert_called_once()
            fill_asset_channel_information_mock.assert_called_once()

    def test_create_asset_network_temp(self):
        with patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_role_information") as fill_asset_role_information_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_node_information") as fill_asset_node_information_mock, \
             patch.object(LocalApi, "_LocalApi__fill_asset_channel_information") as fill_asset_channel_information_mock:

            mock_network_data = {
                "name": 'Network 1',
                "slug": 'network-slug-1',
                "channels": self.channel_info_list,
                "nodes": self.node_info_list,
            }

            mock_app_config = {'application': [{'app': 'foo'}],
                               'network': {'networks': ['network-slug-2', 'network-slug-1'],
                                           'roles': ['role1', 'role2']}
                               }

            read_json_file_mock.return_value = self.mock_template_data
            test_local_api = LocalApi(config_manager=self.config_manager)
            test_local_api.create_asset_network(network_data=mock_network_data, app_config=mock_app_config)

            fill_asset_role_information_mock.assert_called_once()
            fill_asset_channel_information_mock.assert_called_once()
            fill_asset_node_information_mock.assert_called_once()

    def test_get_network_nodes(self):
        with patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock:
            read_json_file_mock.side_effect = \
                [
                    {
                        "networks": {
                            "randstad": {
                                "name": "Randstad",
                                "slug": "randstad",
                                "channels": [
                                    "amsterdam-leiden",
                                    "leiden-the-hague",
                                    "delft-the-hague",
                                    "delft-rotterdam"
                                ]
                            }
                        }
                    },
                    {
                        "channels": [
                            {
                                "slug": "amsterdam-leiden",
                                "node1": "amsterdam",
                                "node2": "leiden",
                                "parameters": [
                                    "elementary-link-fidelity"
                                ]
                            },
                            {
                                "slug": "leiden-the-hague",
                                "node1": "leiden",
                                "node2": "the-hague",
                                "parameters": [
                                    "elementary-link-fidelity"
                                ]
                            }
                        ]
                    },
                    {},
                    {}
                ]

            test_local_api = LocalApi(config_manager=self.config_manager)

            data = test_local_api._get_network_nodes()  # pylint: disable=W0212
            self.assertEqual(data, {'randstad': ['amsterdam', 'leiden', 'the-hague']})

            # Check when only two nodes are available
            read_json_file_mock.reset_mock()
            read_json_file_mock.side_effect = \
                [
                    {
                        "networks": {
                            "randstad": {
                                "name": "Randstad",
                                "slug": "randstad",
                                "channels": [
                                    "amsterdam-leiden",
                                    "leiden-the-hague",
                                    "delft-the-hague",
                                    "delft-rotterdam"
                                ]
                            }
                        }
                    },
                    {
                        "channels": [
                            {
                                "slug": "amsterdam-leiden",
                                "node1": "amsterdam",
                                "node2": "leiden",
                                "parameters": [
                                    "elementary-link-fidelity"
                                ]
                            },
                        ]
                    },
                    {},
                    {}
                ]

            test_local_api = LocalApi(config_manager=self.config_manager)
            data = test_local_api._get_network_nodes()  # pylint: disable=W0212
            self.assertEqual(data, {'randstad': ['amsterdam', 'leiden']})

    def test_network_helpers(self):
        # pylint: disable=W0212
        with patch("adk.api.local_api.utils.read_json_file") as read_json_file_mock:
            # Initialize the data for networks, channels, nodes and templates
            read_json_file_mock.side_effect = [self.mock_network_data, self.mock_channel_data,
                                             self.mock_node_data, self.mock_template_data]

            test_local_api = LocalApi(config_manager=self.config_manager)

            network_info = test_local_api._get_network_info(identifier_value="network1")
            self.assertEqual(network_info['slug'], 'network1')

            network_info = test_local_api._get_network_info(identifier_value="NETWORK1")
            self.assertIsNotNone(network_info)

            network_info = test_local_api._get_network_info(identifier_value="NETWORK 1", identifier_type="name")
            self.assertIsNotNone(network_info)

            self.assertEqual(test_local_api._get_network_slug(network_name='NETWORK 1'), 'network1')
            self.assertIsNone(test_local_api._get_network_slug(network_name='NETWORK 42'))

            self.assertEqual(test_local_api._get_network_name(network_slug='network1'), 'Network 1')
            self.assertIsNone(test_local_api._get_network_name(network_slug='network42'))

            self.assertEqual(test_local_api._get_qne_network_name(network_name='NETWORK 1'), 'Network 1')
            self.assertEqual(test_local_api._get_qne_network_name(network_name='Network 1'), 'Network 1')
            self.assertIsNone(test_local_api._get_qne_network_name(network_name='NETWORK 42'))

            expected_channel_list = ["n1-n2", "n2-n3"]
            self.assertEqual(test_local_api._get_channels_for_network(network_slug='network1'), expected_channel_list)
            self.assertIsNone(test_local_api._get_channels_for_network(network_slug='network-unknown'))

            expected_channel_info = {
              "slug": "n1-n2",
              "node1": "n1",
              "node2": "n2",
              "parameters": [
                    "param-1"
                ]
            }
            self.assertEqual(test_local_api._get_channel_info(channel_slug='n1-n2'), expected_channel_info)
            self.assertIsNone(test_local_api._get_channel_info(channel_slug='channel-unknown'))

            expected_node_info = {
              "name": "N1",
              "slug": "n1",
              "coordinates": {
                "latitude": 52.3667,
                "longitude": 4.8945
              },
              "node_parameters": [
                "gate-fidelity"
              ],
              "number_of_qubits": 3,
              "qubit_parameters": [
                "relaxation-time",
                "dephasing-time"
              ]
            }
            self.assertEqual(test_local_api._get_node_info(node_slug='n1'), expected_node_info)
            self.assertIsNone(test_local_api._get_node_info(node_slug='node-unknown'))

            expected_template_info = {
                "param-1": {
                      "title": "Parameter One",
                      "slug": "param-1",
                      "values": [
                        {
                          "name": "fidelity",
                          "default_value": 1.0,
                          "minimum_value": 0.5,
                          "maximum_value": 1.0,
                          "unit": "unit-name",
                          "scale_value": 1.0
                        }
                      ],
                      "input_type": "fidelity_slider"
                    },
                "param-2": {
                      "title": "Parameter 2",
                      "slug": "param-2",
                      "values": [
                          {
                              "name": "t1",
                              "default_value": 0,
                              "minimum_value": 0,
                              "maximum_value": 1000,
                              "unit": "milliseconds",
                              "scale_value": 12.0
                          }
                      ],
                      "input_type": "time"
                    }
            }
            self.assertEqual(test_local_api._get_templates(), expected_template_info)
