from pathlib import Path
from unittest.mock import patch, MagicMock
import unittest

from adk.command_processor import CommandProcessor
from adk.exceptions import (ApiClientError, AppConfigNotFound, ApplicationDoesNotExist, ApplicationNotComplete,
                            ApplicationNotFound, DirectoryAlreadyExists, NetworkNotAvailableForApplication)
from adk import utils


class TestCommandProcessor(unittest.TestCase):

    def setUp(self):
        self.config_manager = MagicMock(config_dir=Path('dummy'))
        self.local_api = MagicMock(config_manager=self.config_manager)
        self.remote_api = MagicMock(config_manager=self.config_manager)
        self.processor = CommandProcessor(local_api=self.local_api, remote_api=self.remote_api)
        self.host = 'qutech.com'
        self.email = 'test@email.com'
        self.password = 'test_password'
        self.use_username = True
        self.application = 'test_application'
        self.experiment = 'test_experiment'
        self.roles = ['role1', 'role2']
        self.path = Path('path/to/application')
        self.remote_List = ['r1', 'r2']
        self.local_list = ['l1', 'l2', 'l3']
        self.error_dict = {"error": [], "warning": [], "info": []}

    def test_login(self):
        self.processor.login(host=self.host, email=self.email, password=self.password, use_username=self.use_username)
        self.remote_api.login.assert_called_once_with(email=self.email, password=self.password,
                                                      host=self.host, use_username=self.use_username)

    def test_logout(self):
        self.processor.logout(host=self.host)
        self.remote_api.logout.assert_called_once_with(host=self.host)

    def test_applications_init(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists, \
             patch("adk.command_processor.Path.is_dir") as mock_path_is_dir:

            mock_path_exists.return_value = True
            mock_path_is_dir.return_value = True
            self.processor.applications_init(application_name=self.application,
                                             application_path=self.path)
            self.local_api.init_application.assert_called_once_with(self.application, self.path)

    def test_applications_init_fails(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists, \
             patch("adk.command_processor.Path.is_dir") as mock_path_is_dir:

            mock_path_exists.return_value = False
            mock_path_is_dir.return_value = True
            self.assertRaises(ApplicationDoesNotExist, self.processor.applications_init, self.application, self.path)

    def test_applications_create(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists:
            mock_path_exists.return_value = False
            self.processor.applications_create(application_name=self.application, roles=self.roles,
                                               application_path=self.path)
            self.local_api.create_application.assert_called_once_with(self.application, self.roles, self.path)

    def test_applications_create_fails(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists:
            mock_path_exists.return_value = True
            self.assertRaises(DirectoryAlreadyExists, self.processor.applications_create, self.application,
                              self.roles, self.path)

    def test_applications_clone_local(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists:
            mock_path_exists.return_value = False
            self.processor.applications_clone(self.application, True, "new_app", Path("new_path"))
            self.local_api.clone_application.assert_called_once_with(application_name=self.application,
                                                                     new_application_name="new_app",
                                                                     new_application_path=Path("new_path"))
            self.remote_api.clone_application.assert_not_called()

    def test_applications_fetch_remote(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists, \
             patch("adk.command_processor.utils.get_default_manifest") as get_default_manifest_mock:
            mock_path_exists.return_value = False
            get_default_manifest_mock.return_value = "application_data"
            self.processor.applications_fetch(self.application, Path("new_path"))
            self.remote_api.fetch_application.assert_called_once_with(application_name=self.application,
                                                                      new_application_path=Path("new_path"),
                                                                      application_data="application_data")
            self.local_api.fetch_application.assert_not_called()
            self.local_api.set_application_data.assert_called_once_with(Path("new_path"),
                                                                        "application_data")

    def test_applications_fetch_fails(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists:
            mock_path_exists.return_value = True
            self.assertRaises(DirectoryAlreadyExists, self.processor.applications_fetch, self.application, self.path)

    def test_applications_clone_remote(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists, \
             patch("adk.command_processor.utils.get_default_manifest") as get_default_manifest_mock:
            mock_path_exists.return_value = False
            get_default_manifest_mock.return_value = "application_data"
            self.processor.applications_clone(self.application, False, "new_app", Path("new_path"))
            self.remote_api.clone_application.assert_called_once_with(application_name=self.application,
                                                                      new_application_name="new_app",
                                                                      new_application_path=Path("new_path"),
                                                                      application_data="application_data")
            self.local_api.clone_application.assert_not_called()
            self.local_api.set_application_data.assert_called_once_with(Path("new_path"),
                                                                        "application_data")

    def test_applications_clone_fails(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists:
            mock_path_exists.return_value = True
            self.assertRaises(DirectoryAlreadyExists, self.processor.applications_clone, self.application,
                              True, "new_app", self.path)

    def test_applications_upload_succeeds(self):
        self.local_api.get_application_config.return_value = "app_config"
        self.local_api.get_application_data.return_value = "application_data"
        self.local_api.get_application_result.return_value = "app_result"
        self.local_api.get_application_file_names.return_value = ["application_source"]
        self.remote_api.upload_application.return_value = "application_data_result"

        return_value = self.processor.applications_upload(application_name=self.application, application_path=self.path)
        self.local_api.get_application_config.assert_called_once_with(self.application)
        self.local_api.get_application_data.assert_called_once_with(self.path)
        self.local_api.get_application_result.assert_called_once_with(self.application)
        self.remote_api.upload_application.assert_called_once_with(application_path=self.path,
                                                                   application_data="application_data",
                                                                   application_config="app_config",
                                                                   application_result="app_result",
                                                                   application_source=["application_source"])
        self.local_api.set_application_data.assert_called_once_with(self.path,
                                                                    "application_data_result")
        self.assertTrue(return_value)

    def test_applications_upload_fails_to_complete_app_version(self):
        self.local_api.get_application_config.return_value = "app_config"
        self.local_api.get_application_data.return_value = "application_data"
        self.local_api.get_application_result.return_value = "app_result"
        self.local_api.get_application_file_names.return_value = ["application_source"]
        self.remote_api.upload_application.side_effect = ApiClientError("Error: app_config creation error")
        self.assertRaises(ApiClientError, self.processor.applications_upload, self.application, self.path)
        self.local_api.set_application_data.assert_called_once_with(self.path, "application_data")

    def test_applications_upload_fails_no_config(self):
        self.local_api.get_application_config.return_value = None
        self.assertRaises(ApplicationNotFound, self.processor.applications_upload, self.application, self.path)

    def test_applications_upload_fails_no_app_result(self):
        self.local_api.get_application_config.return_value = "app_config"
        self.local_api.get_application_data.return_value = "application_data"
        self.local_api.get_application_result.return_value = None
        self.assertRaises(ApplicationNotComplete, self.processor.applications_upload, self.application, self.path)

    def test_applications_publish(self):
        self.local_api.get_application_data.return_value = "application_data"
        self.local_api.get_application_result.return_value = "app_result"
        self.remote_api.publish_application.return_value = True

        return_value = self.processor.applications_publish(application_path=self.path)
        self.local_api.get_application_data.assert_called_once_with(self.path)
        self.remote_api.publish_application.assert_called_once_with(application_data="application_data")
        self.local_api.set_application_data.assert_called_once_with(self.path,
                                                                    "application_data")
        self.assertTrue(return_value)

    def test_applications_list(self):
        self.remote_api.list_applications.return_value = self.remote_List
        self.local_api.list_applications.return_value = self.local_list
        applications = self.processor.applications_list(remote=True, local=True)

        self.local_api.list_applications.assert_called_once()
        self.remote_api.list_applications.assert_called_once()

        self.assertIn('local', applications)
        self.assertIn('remote', applications)
        self.assertEqual(len(applications), 2)
        self.assertEqual(len(applications['local']), 3)
        self.assertEqual(len(applications['remote']), 2)

    def test_applications_list_local(self):
        self.local_api.list_applications.return_value = self.local_list
        applications = self.processor.applications_list(remote=False, local=True)

        self.local_api.list_applications.assert_called_once()
        self.remote_api.list_applications.assert_not_called()

        self.assertIn('local', applications)
        self.assertNotIn('remote', applications)
        self.assertEqual(len(applications), 1)
        self.assertEqual(len(applications['local']), 3)

    def test_applications_list_remote(self):
        self.remote_api.list_applications.return_value = self.remote_List
        applications = self.processor.applications_list(remote=True, local=False)

        self.local_api.list_applications.assert_not_called()
        self.remote_api.list_applications.assert_called_once()

        self.assertIn('remote', applications)
        self.assertNotIn('local', applications)
        self.assertEqual(len(applications), 1)
        self.assertEqual(len(applications['remote']), 2)

    def test_application_delete(self):
        self.remote_api.delete_application.return_value = True
        self.local_api.delete_application.return_value = True

        self.local_api.get_application_id.return_value = "18"
        return_value = self.processor.applications_delete(None, application_path=Path('dummy'))

        self.local_api.delete_application.assert_called_once()
        self.remote_api.delete_application.assert_called_once()
        self.assertTrue(return_value)

        self.local_api.delete_application.reset_mock()
        self.remote_api.delete_application.reset_mock()
        self.remote_api.delete_application.return_value = False
        self.local_api.delete_application.return_value = False
        return_value = self.processor.applications_delete(None, application_path=Path('dummy'))
        self.local_api.delete_application.assert_called_once()
        self.remote_api.delete_application.assert_called_once()
        self.assertFalse(return_value)

        self.local_api.delete_application.reset_mock()
        self.remote_api.delete_application.reset_mock()
        self.local_api.get_application_id.return_value = None
        self.remote_api.delete_application.return_value = False
        self.local_api.delete_application.return_value = False
        return_value = self.processor.applications_delete(None, application_path=Path('dummy'))
        self.local_api.delete_application.assert_called_once()
        self.remote_api.delete_application.assert_not_called()
        self.assertFalse(return_value)

    def test_applications_validate(self):
        self.remote_api.validate_application.return_value = False
        self.local_api.validate_application.return_value = True
        local = True
        result = self.processor.applications_validate(self.application, self.path, local)
        self.assertTrue(result)
        self.local_api.validate_application.assert_called_once_with(self.application, self.path)
        self.remote_api.validate_application.assert_not_called()

        self.local_api.validate_application.reset_mock()
        self.remote_api.validate_application.reset_mock()
        self.remote_api.validate_application.return_value = True
        self.local_api.validate_application.return_value = False
        local = False
        result = self.processor.applications_validate(self.application, self.path, local)
        self.assertTrue(result)
        self.local_api.validate_application.assert_not_called()
        self.remote_api.validate_application.assert_called_once_with(self.application)

    def test_experiments_create_local(self):
        with patch("adk.command_processor.Path.exists") as mock_path_exists:
            self.local_api.get_application_config.return_value = {'foo': 'bar'}
            self.local_api.is_network_available.return_value = True
            mock_path_exists.return_value = False
            self.processor.experiments_create(experiment_name='test_exp', application_name='app_name',
                                              network_name='network_1', local=True, path=Path('test'))

            self.local_api.get_application_config.assert_called_once_with('app_name')
            self.local_api.is_network_available.assert_called_once_with('network_1', {'foo': 'bar'})
            self.local_api.experiments_create.assert_called_once_with(experiment_name='test_exp',
                                                                      application_name='app_name',
                                                                      network_name='network_1',
                                                                      local=True,
                                                                      path=Path('test'),
                                                                      app_config={'foo': 'bar'})

            self.local_api.experiments_create.reset_mock()
            self.local_api.get_application_config.reset_mock()
            self.local_api.get_application_config.return_value = {'foo': 'bar'}
            self.local_api.is_network_available.reset_mock()
            self.local_api.is_network_available.return_value = False

            with self.assertRaises(NetworkNotAvailableForApplication):
                self.processor.experiments_create(experiment_name='test_exp', application_name='app_name',
                                                  network_name='network_1', local=True, path=Path('test'))
                self.local_api.get_application_config.assert_called_once_with('app_name')
                self.local_api.is_network_available.assert_called_once_with('network_1', {'foo': 'bar'})
                self.local_api.experiments_create.assert_not_called()

            self.local_api.get_application_config.reset_mock()
            self.local_api.get_application_config.return_value = None
            self.assertRaises(AppConfigNotFound, self.processor.experiments_create, 'test_exp',
                              'app_name', 'network_1', True, Path('test'))

            mock_path_exists.return_value = True
            self.assertRaises(DirectoryAlreadyExists, self.processor.experiments_create, 'test_exp',
                              'app_name', 'network_1', True, Path('test'))

    def test_experiments_delete_local(self):
        self.local_api.delete_experiment.return_value = True
        self.remote_api.delete_experiment.return_value = True
        self.local_api.is_experiment_local.return_value = True
        return_value = self.processor.experiments_delete(experiment_name=self.experiment, experiment_path=self.path)
        self.local_api.delete_experiment.assert_called_once()
        self.remote_api.delete_experiment.assert_not_called()
        self.assertTrue(return_value)

        self.local_api.delete_experiment.reset_mock()
        self.remote_api.delete_experiment.reset_mock()
        self.local_api.is_experiment_local.return_value = True
        self.local_api.delete_experiment.return_value = False
        self.remote_api.delete_experiment.return_value = False
        return_value = self.processor.experiments_delete(experiment_name=self.experiment, experiment_path=self.path)
        self.local_api.delete_experiment.assert_called_once()
        self.remote_api.delete_experiment.assert_not_called()
        self.assertFalse(return_value)

    def test_experiments_delete_remote(self):
        self.local_api.is_experiment_local.return_value = False
        self.local_api.get_experiment_id.return_value = "13"
        self.local_api.delete_experiment.return_value = True
        self.remote_api.delete_experiment.return_value = True
        return_value = self.processor.experiments_delete(experiment_name=self.experiment, experiment_path=self.path)
        self.local_api.delete_experiment.assert_called_once()
        self.remote_api.delete_experiment.assert_called_once()
        self.assertTrue(return_value)

        self.local_api.delete_experiment.reset_mock()
        self.remote_api.delete_experiment.reset_mock()
        self.local_api.is_experiment_local.return_value = False
        self.local_api.get_experiment_id.return_value = "13"
        self.local_api.delete_experiment.return_value = False
        self.remote_api.delete_experiment.return_value = False
        return_value = self.processor.experiments_delete(experiment_name=self.experiment, experiment_path=self.path)
        self.local_api.delete_experiment.assert_called_once()
        self.remote_api.delete_experiment.assert_called_once()
        self.assertFalse(return_value)

    def test_experiments_validate_local(self):
        self.local_api.validate_experiment.return_value = self.error_dict
        self.assertEqual(self.processor.experiments_validate(experiment_path=self.path, local=True), self.error_dict)
        self.local_api.validate_experiment.assert_called_once_with(self.path, self.error_dict)

    def test_experiments_validate_remote(self):
        self.local_api.validate_experiment.return_value = self.error_dict
        experiment_data = {"test": 1}
        self.local_api.get_experiment_data.return_value = experiment_data
        self.assertEqual(self.processor.experiments_validate(experiment_path=self.path, local=False), self.error_dict)
        self.remote_api.validate_experiment.assert_called_once_with(experiment_data, self.error_dict)
        self.local_api.validate_experiment.assert_called_once_with(self.path, self.error_dict)

    def test_experiments_run(self):
        with patch('adk.command_processor.Path.mkdir') as mkdir_mock, \
             patch("adk.command_processor.utils.write_json_file") as write_json_mock:

            # local
            results = ['foo']
            run_update = False
            self.local_api.is_experiment_local.return_value = True
            self.local_api.run_experiment.return_value = results
            self.processor.experiments_run(self.path, True, run_update, None)

            self.local_api.is_experiment_local.assert_called_once_with(experiment_path=self.path)
            self.local_api.run_experiment.assert_called_once_with(self.path, run_update, None)
            mkdir_mock.assert_called_once_with(parents=True)
            write_json_mock.assert_called_once_with(self.path / 'results' / 'processed.json', results,
                                                    encoder_cls=utils.ComplexEncoder)

            mkdir_mock.reset_mock()
            write_json_mock.reset_mock()
            run_update = True
            self.local_api.is_experiment_local.reset_mock()
            self.local_api.is_experiment_local.return_value = True
            self.local_api.run_experiment.reset_mock()
            self.local_api.run_experiment.return_value = None
            self.processor.experiments_run(self.path, True, run_update, 30)
            self.local_api.is_experiment_local.assert_called_once_with(experiment_path=self.path)
            self.local_api.run_experiment.assert_called_once_with(self.path, run_update, 30)
            mkdir_mock.assert_not_called()
            write_json_mock.assert_not_called()

            # remote
            run_update = False
            mkdir_mock.reset_mock()
            write_json_mock.reset_mock()
            self.local_api.is_experiment_local.reset_mock()
            self.local_api.is_experiment_local.return_value = False
            self.local_api.run_experiment.reset_mock()
            results = ['foo']
            experiment_data = {"test": 1}
            round_set = {"fake_roundset_id": 1}
            self.remote_api.get_results.return_value = results
            self.local_api.get_experiment_data.return_value = experiment_data
            self.remote_api.run_experiment.return_value = (round_set, 12)
            return_value = self.processor.experiments_run(self.path, True, run_update, 30)

            self.local_api.get_experiment_data.assert_called_once_with(self.path)
            self.remote_api.run_experiment.assert_called_once_with(experiment_data)
            self.local_api.set_experiment_id.assert_called_once_with(12, self.path)
            self.local_api.set_experiment_round_set.assert_called_once_with(round_set, self.path)
            self.remote_api.get_results.assert_called_once_with(round_set, True, 30)
            mkdir_mock.assert_called_once_with(parents=True)

            write_json_mock.assert_called_once_with(self.path / 'results' / 'processed.json', results,
                                                    encoder_cls=utils.ComplexEncoder)
            self.assertEqual(return_value, results)

    def test_experiments_result(self):
        with patch("adk.command_processor.Path.exists") as exists_mock, \
             patch("adk.command_processor.utils.read_json_file") as read_json_mock:

            exists_mock.return_value = True
            read_json_mock.return_value = {"foo": "bar"}
            result_data = self.processor.experiments_results(True, Path('dummy'))
            self.assertEqual(result_data, {"foo": "bar"})

            exists_mock.reset_mock()
            exists_mock.return_value = False
            self.assertRaises(Exception, self.processor.experiments_results, True, False, Path('dummy'))

    def test_networks_list_local(self):
        self.local_api.list_networks.return_value = self.local_list
        networks = self.processor.networks_list(remote=False, local=True)

        self.local_api.list_networks.assert_called_once()
        self.remote_api.list_networks.assert_not_called()

        self.assertIn('local', networks)
        self.assertNotIn('remote', networks)
        self.assertEqual(len(networks), 1)
        self.assertEqual(len(networks['local']), 3)

    def test_networks_list_remote(self):
        self.remote_api.list_networks.return_value = self.remote_List
        networks = self.processor.networks_list(remote=True, local=False)

        self.local_api.list_networks.assert_not_called()
        self.remote_api.list_networks.assert_called_once()

        self.assertIn('remote', networks)
        self.assertNotIn('local', networks)
        self.assertEqual(len(networks), 1)
        self.assertEqual(len(networks['remote']), 2)
