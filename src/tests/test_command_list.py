import unittest
from pathlib import Path
from unittest.mock import patch
from typer.testing import CliRunner

from adk.exceptions import ApplicationNotFound, ExperimentDirectoryNotValid
from adk.command_list import app, applications_app, experiments_app, networks_app, retrieve_application_name_and_path, \
                             retrieve_experiment_name_and_path
from adk.api.local_api import LocalApi
from adk.api.remote_api import RemoteApi
from adk.command_processor import CommandProcessor
from adk.managers.config_manager import ConfigManager


class TestCommandList(unittest.TestCase):
    def setUp(self):
        self.application = 'test_application'
        self.experiment_name = 'test_experiment'
        self.roles = ["role1, role2"]
        self.path = Path("dummy")
        self.runner = CliRunner()
        self.app_dict_1 = {'remote': [], 'local': []}
        self.app_dict_2 = {'remote': [{'name': 'foo'}, {'name': 'bar'}], 'local': []}
        self.app_dict_3 = {'remote': [], 'local': [{'name': 'foo'}]}
        self.app_dict_4 = {'remote': [{'name': 'bar'}], 'local': [{'name': 'foo'}]}
        self.app_dict_5 = {'local': []}
        self.app_dict_6 = {'local': [{'name': 'foo'}, {'name': 'bar'}]}
        self.app_dict_7 = {'remote': []}
        self.app_dict_8 = {'remote': [{'name': 'foo'}, {'name': 'bar'}]}
        self.exp_dict_1 = []
        self.exp_dict_2 = [{"id": 3}, {"id": 1}, {"id": 2}]
        self.net_dict_1 = {'remote': [], 'local': []}
        self.net_dict_2 = {'remote': [], 'local': [{"name": "1"}, {"name": "2"}, {"name": "3"}]}
        self.net_dict_3 = {'remote': [], 'local': []}
        self.net_dict_4 = {'remote': [{"name": "6"}, {"name": "5"}], 'local': []}
        self.net_dict_5 = {'remote': [{"name": "6"}, {"name": "5"}],
                           'local': [{"name": "1"}, {"name": "2"}, {"name": "3"}]}

    def test_login(self):
        with patch.object(CommandProcessor, "login") as login_mock, \
             patch.object(RemoteApi, 'get_active_host') as get_active_host_mock:

            get_active_host_mock.return_value = 'test_host'
            login_output = self.runner.invoke(app, ['login', '--email=test@email.com',
                                                    '--password=test_password', 'test_host'])
            login_mock.assert_called_once_with(host='test_host', email='test@email.com',
                                               password='test_password', use_username=False)
            self.assertIn("Log in to 'test_host' as user 'test@email.com' succeeded", login_output.stdout)

    def test_login_email_as_username(self):
        with patch.object(CommandProcessor, "login") as login_mock, \
             patch.object(RemoteApi, 'get_active_host') as get_active_host_mock:

            get_active_host_mock.return_value = 'test_host'
            login_output = self.runner.invoke(app, ['login', '--email=test@email.com',
                                                    '--password=test_password', '--username', 'test_host'])
            login_mock.assert_called_once_with(host='test_host', email='test@email.com',
                                               password='test_password', use_username=True)

    def test_logout(self):
        with patch.object(CommandProcessor, "logout") as logout_mock:
            host = 'test_host'
            logout_mock.return_value = True
            logout_output = self.runner.invoke(app, ['logout', host])
            self.assertIn(f"Logging out from '{host}' succeeded", logout_output.stdout)

            logout_mock.return_value = True
            logout_output = self.runner.invoke(app, ['logout'])
            self.assertIn("Logging out from active host succeeded", logout_output.stdout)

            logout_mock.reset_mock()
            logout_mock.return_value = False
            logout_output = self.runner.invoke(app, ['logout', host])
            self.assertIn('Not logged in to a host', logout_output.stdout)

    def test_applications_init_success(self):
        with patch("adk.command_list.Path.cwd", return_value=self.path) as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock, \
             patch.object(CommandProcessor, 'applications_init') as application_init_mock:

            application_exists_mock.return_value = False, ""
            application_init_output = self.runner.invoke(applications_app,
                                                         ['init', self.application])
            mock_cwd.assert_called_once()
            application_init_mock.assert_called_once_with(application_name=self.application,
                                                          application_path=self.path / self.application)
            self.assertEqual(application_init_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' initialized successfully in directory "
                          f"'{self.path / self.application}'",
                          application_init_output.stdout)

    def test_applications_init_exceptions(self):
        with patch("adk.command_list.Path.cwd", return_value=self.path) as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock, \
             patch.object(CommandProcessor, 'applications_init') as application_init_mock:

            # Raise ApplicationAlreadyExists
            application_exists_mock.return_value = True, "the_path"
            application_init_output = self.runner.invoke(applications_app,
                                                         ['init', self.application])
            self.assertIn(f"Application '{self.application}' already exists. Application location: 'the_path'",
                          application_init_output.stdout)

            application_init_output = self.runner.invoke(applications_app, ['init', 'test*application'])
            self.assertIn('Error: Application name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_init_output.stdout)

    def test_applications_create_success(self):
        with patch("adk.command_list.Path.cwd", return_value=self.path) as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock, \
             patch("adk.command_list.validate_path_name") as mock_validate_path_name, \
             patch.object(CommandProcessor, 'applications_create') as application_create_mock:

            application_exists_mock.return_value = False, ""
            application_create_output = self.runner.invoke(applications_app,
                                                           ['create', self.application, 'role1', 'role2'])
            mock_cwd.assert_called_once()
            self.assertEqual(mock_validate_path_name.call_count, 3)
            application_create_mock.assert_called_once_with(application_name=self.application, roles=['role1', 'role2'],
                                                            application_path=self.path / self.application)
            self.assertEqual(application_create_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' created successfully in directory "
                          f"'{self.path / self.application}'",
                          application_create_output.stdout)

    def test_applications_create_exceptions(self):
        with patch("adk.command_list.Path.cwd", return_value='test') as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock:

            application_exists_mock.return_value = False, ""
            # Raise error when no roles are given
            application_create_output = self.runner.invoke(applications_app, ['create', 'test_application'])
            self.assertIn("Missing argument 'ROLES...'", application_create_output.stdout)

            # Raise RolesNotUnique when roles are duplicated
            application_create_output = self.runner.invoke(applications_app, ['create', 'test_application', 'role1',
                                                                              'role2', 'role3', 'role2'])
            self.assertIn('The role names must be unique', application_create_output.stdout)

            # Raise InvalidApplicationName when the application name is invalid contains ['/', '\\', '*', ':', '?',
            # '"', '<', '>', '|']
            application_create_output = self.runner.invoke(applications_app, ['create', 'test_application/2',
                                                                              'role1', 'role2'])
            self.assertIn('Error: Application name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_create_output.stdout)

            application_create_output = self.runner.invoke(applications_app, ['create', 'test*application',
                                                                              'role1', 'role2'])
            self.assertIn('Error: Application name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_create_output.stdout)

            application_create_output = self.runner.invoke(applications_app, ['create', 'test\\application',
                                                                              'role1', 'role2'])
            self.assertIn('Error: Application name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_create_output.stdout)

            # Raise InvalidRoleName when one of the roles contains ['/', '\\', '*', ':', '?', '"', '<', '>', '|']
            application_create_output = self.runner.invoke(applications_app, ['create', 'test_application',
                                                                              'role/1', 'role2'])
            self.assertIn('Error: Role name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_create_output.stdout)

            application_create_output = self.runner.invoke(applications_app, ['create', 'test_application',
                                                                              'role1', 'role/2'])
            self.assertIn('Error: Role name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_create_output.stdout)

            application_create_output = self.runner.invoke(applications_app, ['create', 'test_application',
                                                                              'rol/e1', 'role2'])
            self.assertIn('Error: Role name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_create_output.stdout)

            # Raise ApplicationAlreadyExists
            application_exists_mock.return_value = True, "the_path"
            application_create_output = self.runner.invoke(applications_app,
                                                           ['create', self.application, 'role1', 'role2'])
            self.assertIn(f"Application '{self.application}' already exists. Application location: 'the_path'",
                          application_create_output.stdout)

            application_exists_mock.return_value = False, "the_path"
            # Raise Other Exception
            mock_cwd.side_effect = Exception("Test")
            application_create_output = self.runner.invoke(applications_app,
                                                           ['create', 'test_application', 'role1', 'role2'])
            self.assertIn("Unhandled exception: Exception('Test')", application_create_output.stdout)

    def test_applications_remote_fetch_success(self):
        with patch("adk.command_list.Path.cwd", return_value=self.path) as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock, \
             patch("adk.command_list.validate_path_name") as mock_validate_path_name, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as applications_validate_mock, \
             patch.object(CommandProcessor, 'applications_fetch') as application_fetch_mock:

            application_exists_mock.return_value = False, ""
            retrieve_appname_and_path_mock.return_value = self.path, self.application
            application_fetch_output = self.runner.invoke(applications_app,
                                                          ['fetch', self.application])
            mock_cwd.assert_called_once()
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 0)
            self.assertEqual(applications_validate_mock.call_count, 0)
            self.assertEqual(mock_validate_path_name.call_count, 1)
            application_fetch_mock.assert_called_once_with(application_name=self.application,
                                                           new_application_path=self.path / self.application)
            self.assertEqual(application_fetch_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' fetched successfully in directory "
                          f"'{self.path / self.application}'",
                          application_fetch_output.stdout)

    def test_applications_fetch_exceptions(self):
        with patch("adk.command_list.Path.cwd", return_value=self.path) as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_fetch') as application_fetch_mock:

            application_exists_mock.return_value = False, ""
            retrieve_appname_and_path_mock.return_value = self.path, self.application
            # When application is valid (no items in error, warning and info)
            application_fetch_output = self.runner.invoke(applications_app,
                                                          ['fetch', 'fetch*app'])

            self.assertIn('Error: Application name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_fetch_output.stdout)

            # Raise ApplicationAlreadyExists
            application_exists_mock.return_value = True, "the_path"
            application_fetch_output = self.runner.invoke(applications_app,
                                                           ['fetch', self.application])
            self.assertIn(f"Application '{self.application}' already exists. Application location: 'the_path'",
                          application_fetch_output.stdout)

    def test_applications_local_clone_success(self):
        with patch("adk.command_list.Path.cwd", return_value=self.path) as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock, \
             patch("adk.command_list.validate_path_name") as mock_validate_path_name, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as applications_validate_mock, \
             patch.object(CommandProcessor, 'applications_clone') as application_clone_mock:

            application_exists_mock.return_value = False, ""
            retrieve_appname_and_path_mock.return_value = self.path, self.application
            # When application is valid (no items in error, warning and info)
            applications_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            application_clone_output = self.runner.invoke(applications_app,
                                                          ['clone', self.application, 'new_app'])
            mock_cwd.assert_called_once()
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 1)
            self.assertEqual(applications_validate_mock.call_count, 1)
            self.assertEqual(mock_validate_path_name.call_count, 1)
            application_clone_mock.assert_called_once_with(application_name=self.application, local=True,
                                                           new_application_name='new_app',
                                                           new_application_path=self.path / 'new_app')
            self.assertEqual(application_clone_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' cloned successfully in directory "
                          f"'{self.path / 'new_app'}'",
                          application_clone_output.stdout)

    def test_applications_remote_clone_success(self):
        with patch("adk.command_list.Path.cwd", return_value=self.path) as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock, \
             patch("adk.command_list.validate_path_name") as mock_validate_path_name, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as applications_validate_mock, \
             patch.object(CommandProcessor, 'applications_clone') as application_clone_mock:

            application_exists_mock.return_value = False, ""
            retrieve_appname_and_path_mock.return_value = self.path, self.application
            # When application is valid (no items in error, warning and info)
            applications_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            application_clone_output = self.runner.invoke(applications_app,
                                                          ['clone', self.application, '--remote'])
            mock_cwd.assert_called_once()
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 0)
            self.assertEqual(applications_validate_mock.call_count, 0)
            self.assertEqual(mock_validate_path_name.call_count, 1)
            application_clone_mock.assert_called_once_with(application_name=self.application, local=False,
                                                           new_application_name=self.application,
                                                           new_application_path=self.path / self.application)
            self.assertEqual(application_clone_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' cloned successfully in directory "
                          f"'{self.path / self.application}'",
                          application_clone_output.stdout)

    def test_applications_clone_exceptions(self):
        with patch("adk.command_list.Path.cwd", return_value=self.path) as mock_cwd, \
             patch.object(ConfigManager, "application_exists") as application_exists_mock, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as applications_validate_mock, \
             patch.object(CommandProcessor, 'applications_clone') as application_clone_mock:

            application_exists_mock.return_value = False, ""
            retrieve_appname_and_path_mock.return_value = self.path, self.application
            # When application is valid (no items in error, warning and info)
            applications_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            application_clone_output = self.runner.invoke(applications_app,
                                                          ['clone', self.application, 'new*app'])

            self.assertIn('Error: Application name can\'t contain any of the following characters: [\'/\', \'\\\', '
                          '\'*\', \':\', \'?\', \'"\', \'<\', \'>\', \'|\']', application_clone_output.stdout)

            # Raise ApplicationAlreadyExists
            application_exists_mock.return_value = True, "the_path"
            application_clone_output = self.runner.invoke(applications_app,
                                                          ['clone', self.application, 'new_app'])
            self.assertIn(f"Application 'new_app' already exists. Application location: 'the_path'",
                          application_clone_output.stdout)

            application_exists_mock.return_value = False, ""
            retrieve_appname_and_path_mock.return_value = self.path, self.application
            # When application is valid (no items in error, warning and info)
            applications_validate_mock.return_value = {"error": ["an_error"], "warning": [], "info": []}
            application_clone_output = self.runner.invoke(applications_app,
                                                          ['clone', self.application, 'new_app'])
            self.assertIn(f"Local application was not cloned",
                          application_clone_output.stdout)
            self.assertIn(f"Application '{self.application}' failed validation.",
                          application_clone_output.stdout)

            application_clone_output = self.runner.invoke(applications_app,
                                                          ['clone', self.application])
            self.assertIn("Cloning a local application requires a new application name",
                          application_clone_output.stdout)

    def test_application_delete_no_application_name(self):
        with patch.object(CommandProcessor, 'applications_delete', return_value=True) as applications_delete_mock, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            application_delete_output = self.runner.invoke(applications_app, ['delete'])
            self.assertEqual(application_delete_output.exit_code, 0)
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertIn("Application deleted successfully",
                          application_delete_output.stdout)

            retrieve_appname_and_path_mock.reset_mock()
            applications_delete_mock.return_value = False
            application_delete_output = self.runner.invoke(applications_app, ['delete'])
            self.assertEqual(application_delete_output.exit_code, 0)
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertIn("Application files deleted, directory not empty",
                          application_delete_output.stdout)

            retrieve_appname_and_path_mock.reset_mock()
            retrieve_appname_and_path_mock.return_value = self.path, None
            applications_delete_mock.return_value = False
            application_delete_output = self.runner.invoke(applications_app, ['delete'])
            self.assertEqual(application_delete_output.exit_code, 0)
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertIn("Application files deleted",
                          application_delete_output.stdout)

    def test_application_delete_with_application_name(self):
        with patch.object(CommandProcessor, 'applications_delete', return_value=False) as applications_delete_mock, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            application_delete_output = self.runner.invoke(applications_app, ['delete', 'app_dir'])
            applications_delete_mock.assert_called_once()
            self.assertEqual(application_delete_output.exit_code, 0)
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertIn("Application files deleted, directory not empty",
                          application_delete_output.stdout)

    def test_retrieve_application_name_and_path(self):
        with patch("adk.command_list.validate_path_name") as validate_path_name_mock, \
             patch("adk.command_list.Path.cwd") as cwd_mock, \
             patch.object(ConfigManager, "get_application_path") as get_application_path_mock, \
             patch.object(ConfigManager, "get_application_from_path") as get_application_from_path_mock, \
             patch("adk.command_list.Path.is_dir") as is_dir_mock:

            get_application_path_mock.return_value = self.path
            # application name not None
            retrieve_application_name_and_path(application_name=self.application)
            is_dir_mock.assert_called_once()
            validate_path_name_mock.assert_called_once_with("Application", self.application)
            get_application_path_mock.assert_called_once_with(self.application)

            # application name is None
            is_dir_mock.reset_mock()
            cwd_mock.return_value = self.path
            get_application_from_path_mock.return_value = self.application, None
            retrieve_application_name_and_path(application_name=None)
            is_dir_mock.assert_called_once()
            cwd_mock.assert_called_once()
            get_application_from_path_mock.assert_called_once_with(self.path)

            # Raise ApplicationNotFound when application_path is None
            validate_path_name_mock.reset_mock()
            get_application_path_mock.reset_mock()
            get_application_path_mock.return_value = None
            self.assertRaises(ApplicationNotFound, retrieve_application_name_and_path, self.application)
            validate_path_name_mock.assert_called_once_with("Application", self.application)
            get_application_path_mock.assert_called_once_with(self.application)

            # Raise ApplicationNotFound when application directory does not exist
            validate_path_name_mock.reset_mock()
            get_application_path_mock.reset_mock()
            is_dir_mock.reset_mock()
            is_dir_mock.return_value = False
            get_application_path_mock.return_value = self.path
            self.assertRaises(ApplicationNotFound, retrieve_application_name_and_path, self.application)
            is_dir_mock.assert_called_once()
            validate_path_name_mock.assert_called_once_with("Application", self.application)
            get_application_path_mock.assert_called_once_with(self.application)

    def test_applications_validate_all_ok(self):
        with patch.object(CommandProcessor, 'applications_validate') as applications_validate_mock, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application

            # When application is valid (no items in error, warning and info)
            applications_validate_mock.return_value = {"error": {}, "warning": {}, "info": {}}

            application_validate_output = self.runner.invoke(applications_app, ['validate'])
            retrieve_appname_and_path_mock.assert_called_once()
            applications_validate_mock.assert_called_once_with(application_name=self.application,
                                                               application_path=self.path)
            self.assertIn(f"Application '{self.application}' is valid", application_validate_output.stdout)

            # When application is valid with item in 'info'
            retrieve_appname_and_path_mock.reset_mock()
            applications_validate_mock.reset_mock()
            applications_validate_mock.return_value = {"error": [], "warning": [], "info": ["info"]}

            application_validate_output = self.runner.invoke(applications_app, ['validate'])
            applications_validate_mock.assert_called_once_with(application_name=self.application,
                                                               application_path=self.path)
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertIn(f"Application '{self.application}' is valid", application_validate_output.stdout)

            # When application name is given as input
            retrieve_appname_and_path_mock.reset_mock()
            applications_validate_mock.reset_mock()

            application_validate_output = self.runner.invoke(applications_app, ['validate', self.application])
            applications_validate_mock.assert_called_once_with(application_name=self.application,
                                                               application_path=self.path)
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertIn(f"Application '{self.application}' is valid", application_validate_output.stdout)

    def test_applications_validate_invalid(self):
        with patch.object(CommandProcessor, 'applications_validate') as applications_validate_mock, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            applications_validate_mock.return_value = {"error": ["error"], "warning": ["warning"], "info": ["info"]}

            application_validate_output = self.runner.invoke(applications_app, ['validate'])
            applications_validate_mock.assert_called_once_with(application_name=self.application,
                                                               application_path=self.path)
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertIn(f"Application '{self.application}' failed validation.", application_validate_output.stdout)

            # When only 'error' has items
            retrieve_appname_and_path_mock.reset_mock()
            applications_validate_mock.reset_mock()
            applications_validate_mock.return_value = {"error": ["error"], "warning": [], "info": []}

            application_validate_output = self.runner.invoke(applications_app, ['validate'])
            applications_validate_mock.assert_called_once_with(application_name=self.application,
                                                               application_path=self.path)
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertIn(f"Application '{self.application}' failed validation.", application_validate_output.stdout)

    def test_applications_upload_success(self):
        with patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch.object(CommandProcessor, 'applications_upload') as application_upload_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            app_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            application_upload_mock.return_value = True

            application_upload_output = self.runner.invoke(applications_app,
                                                           ['upload', 'test_application'])
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 1)
            application_upload_mock.assert_called_once_with(application_name=self.application,
                                                            application_path=self.path)
            self.assertEqual(application_upload_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' uploaded successfully",
                          application_upload_output.stdout)

    def test_applications_upload_fails(self):
        with patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch.object(CommandProcessor, 'applications_upload') as application_upload_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            app_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            application_upload_mock.return_value = False

            application_upload_output = self.runner.invoke(applications_app,
                                                           ['upload', 'test_application'])
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 1)
            application_upload_mock.assert_called_once_with(application_name=self.application,
                                                            application_path=self.path)
            self.assertEqual(application_upload_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' not uploaded",
                          application_upload_output.stdout)

    def test_applications_upload_validation_error(self):
        with patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch("adk.command_list.format_validation_messages") as format_validation_messages_mock, \
             patch.object(CommandProcessor, 'applications_upload') as application_upload_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            app_validate_mock.return_value = {"error": [ 'Error' ], "warning": [], "info": []}
            application_upload_mock.return_value = True

            application_upload_output = self.runner.invoke(applications_app,
                                                           ['upload', 'test_application'])
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 1)
            format_validation_messages_mock.assert_called_once()
            application_upload_mock.assert_not_called()
            self.assertIn(f"Application was not uploaded",
                          application_upload_output.stdout)
            self.assertIn(f"Application '{self.application}' failed validation.",
                          application_upload_output.stdout)

    def test_applications_publish_success(self):
        with patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch.object(CommandProcessor, 'applications_publish') as application_publish_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            app_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            application_publish_mock.return_value = True

            application_publish_output = self.runner.invoke(applications_app,
                                                            ['publish', 'test_application'])
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 1)
            application_publish_mock.assert_called_once_with(application_path=self.path)
            self.assertEqual(application_publish_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' published successfully",
                          application_publish_output.stdout)

    def test_applications_publish_fails(self):
        with patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch.object(CommandProcessor, 'applications_publish') as application_publish_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            app_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            application_publish_mock.return_value = False

            application_publish_output = self.runner.invoke(applications_app,
                                                            ['publish', 'test_application'])
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 1)
            application_publish_mock.assert_called_once_with(application_path=self.path)
            self.assertEqual(application_publish_output.exit_code, 0)
            self.assertIn(f"Application '{self.application}' not published",
                          application_publish_output.stdout)

    def test_applications_publish_validation_error(self):
        with patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch("adk.command_list.format_validation_messages") as format_validation_messages_mock, \
             patch.object(CommandProcessor, 'applications_publish') as application_publish_mock:

            retrieve_appname_and_path_mock.return_value = self.path, self.application
            app_validate_mock.return_value = {"error": ['Error'], "warning": [], "info": []}
            application_publish_mock.return_value = True

            application_publish_output = self.runner.invoke(applications_app,
                                                            ['publish', 'test_application'])
            self.assertEqual(retrieve_appname_and_path_mock.call_count, 1)
            format_validation_messages_mock.assert_called_once()
            application_publish_mock.assert_not_called()
            self.assertIn(f"Application was not published",
                          application_publish_output.stdout)
            self.assertIn(f"Application '{self.application}' failed validation.",
                          application_publish_output.stdout)

    def test_applications_list(self):
        with patch.object(CommandProcessor, "applications_list") as list_applications_mock:
            list_applications_mock.side_effect = [self.app_dict_1, self.app_dict_2,
                                                  self.app_dict_3, self.app_dict_4]

            result_both = self.runner.invoke(applications_app, ['list'])
            self.assertEqual(result_both.exit_code, 0)
            self.assertIn('There are no local applications available', result_both.stdout)
            self.assertIn('There are no remote applications available', result_both.stdout)

            result_both = self.runner.invoke(applications_app, ['list'])
            self.assertEqual(result_both.exit_code, 0)
            self.assertIn('There are no local applications available', result_both.stdout)
            self.assertIn('2 remote application(s)', result_both.stdout)
            self.assertIn('foo', result_both.stdout)
            self.assertIn('bar', result_both.stdout)

            result_both = self.runner.invoke(applications_app, ['list'])
            self.assertEqual(result_both.exit_code, 0)
            self.assertIn('1 local application(s)', result_both.stdout)
            self.assertIn('foo', result_both.stdout)
            self.assertIn('There are no remote applications available', result_both.stdout)

            result_both = self.runner.invoke(applications_app, ['list'])
            self.assertEqual(result_both.exit_code, 0)
            self.assertIn('1 local application(s)', result_both.stdout)
            self.assertIn('1 remote application(s)', result_both.stdout)
            self.assertIn('foo', result_both.stdout)
            self.assertIn('bar', result_both.stdout)

    def test_applications_list_local(self):
        with patch.object(CommandProcessor, "applications_list") as list_applications_mock:
            list_applications_mock.side_effect = [self.app_dict_5, self.app_dict_6]

            result_local = self.runner.invoke(applications_app, ['list', '--local'])
            self.assertEqual(result_local.exit_code, 0)
            self.assertIn('There are no local applications available', result_local.stdout)
            self.assertNotIn('remote', result_local.stdout)

            result_local = self.runner.invoke(applications_app, ['list', '--local'])
            self.assertEqual(result_local.exit_code, 0)
            self.assertIn('2 local application(s)', result_local.stdout)
            self.assertIn('foo', result_local.stdout)
            self.assertIn('bar', result_local.stdout)
            self.assertNotIn('remote', result_local.stdout)

    def test_applications_list_remote(self):
        with patch.object(CommandProcessor, "applications_list") as list_applications_mock:
            list_applications_mock.side_effect = [self.app_dict_7, self.app_dict_8]

            result_remote = self.runner.invoke(applications_app, ['list', '--remote'])
            self.assertEqual(result_remote.exit_code, 0)
            self.assertIn('There are no remote applications available', result_remote.stdout)
            self.assertNotIn('local', result_remote.stdout)

            result_remote = self.runner.invoke(applications_app, ['list', '--remote'])
            self.assertEqual(result_remote.exit_code, 0)
            self.assertIn('2 remote application(s)', result_remote.stdout)
            self.assertIn('foo', result_remote.stdout)
            self.assertIn('bar', result_remote.stdout)
            self.assertNotIn('local', result_remote.stdout)

    def test_experiments_list(self):
        with patch.object(CommandProcessor, "experiments_list") as list_experiments_mock:
            list_experiments_mock.side_effect = [self.exp_dict_1, self.exp_dict_2]

            result = self.runner.invoke(experiments_app, ['list'])
            self.assertEqual(result.exit_code, 0)
            self.assertIn('There are no remote experiments available', result.stdout)

            result = self.runner.invoke(experiments_app, ['list'])
            self.assertEqual(result.exit_code, 0)
            self.assertIn('3 remote experiment(s)', result.stdout)
            self.assertIn("experiment id", result.stdout)
            self.assertIn("-------------", result.stdout)
            self.assertIn('1', result.stdout)
            self.assertIn('2', result.stdout)
            self.assertIn('3', result.stdout)

    def test_experiment_create_succeeds(self):
        with patch("adk.command_list.Path.cwd") as mock_cwd, \
             patch.object(CommandProcessor, 'experiments_create') as experiment_create_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch("adk.command_list.validate_path_name") as mock_validate_path, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_application_name_and_path_mock:

            retrieve_application_name_and_path_mock.return_value = self.path, "app_name"
            mock_cwd.return_value = 'test'
            app_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            experiment_create_mock.return_value = True, ''

            experiment_create_output = self.runner.invoke(experiments_app, ['create', 'test_exp', 'app_name',
                                                                            'network_1'])
            mock_validate_path.assert_called_once_with('Experiment', 'test_exp')
            retrieve_application_name_and_path_mock.assert_called_once_with(application_name="app_name")
            self.assertEqual(experiment_create_output.exit_code, 0)
            self.assertIn("Experiment 'test_exp' created successfully in directory 'test'",
                          experiment_create_output.stdout)
            experiment_create_mock.assert_called_once_with(experiment_name='test_exp', application_name='app_name',
                                                           network_name='network_1', local=True, path='test')

    def test_experiment_create_fails(self):
        with patch("adk.command_list.Path.cwd") as mock_cwd, \
             patch.object(CommandProcessor, 'experiments_create') as experiment_create_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch("adk.command_list.format_validation_messages") as format_validation_messages_mock, \
             patch("adk.command_list.validate_path_name") as mock_validate_path, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_application_name_and_path_mock:

            retrieve_application_name_and_path_mock.return_value = self.path, "app_name"
            mock_cwd.return_value = 'test'
            app_validate_mock.return_value = {"error": ["An error has occurred"], "warning": [], "info": []}
            experiment_create_mock.return_value = True, ''

            experiment_create_output = self.runner.invoke(experiments_app, ['create', 'test_exp', 'app_name',
                                                                            'network_1'])
            mock_validate_path.assert_called_once_with('Experiment', 'test_exp')
            format_validation_messages_mock.assert_called_once()

            retrieve_application_name_and_path_mock.assert_called_once_with(application_name="app_name")
            self.assertEqual(experiment_create_output.exit_code, 1)
            self.assertIn("Experiment was not created",
                          experiment_create_output.stdout)
            self.assertIn("Experiment failed validation",
                          experiment_create_output.stdout)
            experiment_create_mock.assert_not_called()

    def test_retrieve_experiment_name_and_path(self):
        with patch("adk.command_list.Path.cwd") as cwd_mock, \
             patch("adk.command_list.validate_path_name") as validate_path_name_mock, \
             patch("adk.command_list.Path.is_file") as is_file_mock, \
             patch("adk.command_list.Path.is_dir") as is_dir_mock:

            # if experiment name is not None
            cwd_mock.return_value = self.path
            is_dir_mock.return_value = True
            is_file_mock.return_value = True
            path, name = retrieve_experiment_name_and_path(self.experiment_name)
            validate_path_name_mock.assert_called_once_with("Experiment", self.experiment_name)
            self.assertEqual(path, self.path / self.experiment_name)
            self.assertEqual(name, self.experiment_name)
            is_dir_mock.assert_called_once()
            is_file_mock.assert_called_once()

            # if experiment name is None
            is_dir_mock.reset_mock()
            is_file_mock.reset_mock()
            is_dir_mock.return_value = True
            is_file_mock.return_value = True
            path, name = retrieve_experiment_name_and_path(None)
            self.assertEqual(path, self.path)
            self.assertEqual(name, 'dummy')
            is_dir_mock.assert_called_once()
            is_file_mock.assert_called_once()

            # raise ExperimentDirectoryNotValid
            is_dir_mock.reset_mock()
            validate_path_name_mock.reset_mock()
            is_dir_mock.return_value = False
            self.assertRaises(ExperimentDirectoryNotValid, retrieve_experiment_name_and_path, self.experiment_name)
            validate_path_name_mock.assert_called_once_with("Experiment", self.experiment_name)
            is_dir_mock.assert_called_once()

    def test_experiment_validate(self):
        with patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_experiment_name_and_path_mock, \
             patch.object(CommandProcessor, 'experiments_validate') as experiments_validate_mock, \
             patch("adk.command_list.format_validation_messages") as format_validation_messages_mock:

            experiments_validate_mock.return_value = {"error": ["error"], "warning": ["warning"], "info": ["info"]}
            retrieve_experiment_name_and_path_mock.return_value = (self.path, self.experiment_name)

            experiment_validate_output = self.runner.invoke(experiments_app, ['validate'])
            retrieve_experiment_name_and_path_mock.assert_called_once_with(experiment_name=None)
            experiments_validate_mock.assert_called_once_with(experiment_path=self.path)
            format_validation_messages_mock.assert_called_once()
            self.assertIn("Experiment failed validation", experiment_validate_output.stdout)

            # When only 'error' has items
            experiments_validate_mock.reset_mock()
            retrieve_experiment_name_and_path_mock.reset_mock()
            format_validation_messages_mock.reset_mock()
            experiments_validate_mock.return_value = {"error": ["error"], "warning": [], "info": []}

            experiment_validate_output = self.runner.invoke(experiments_app, ['validate'])
            retrieve_experiment_name_and_path_mock.assert_called_once_with(experiment_name=None)
            experiments_validate_mock.assert_called_once_with(experiment_path=self.path)
            format_validation_messages_mock.assert_called_once()
            self.assertIn("Experiment failed validation", experiment_validate_output.stdout)

            # When application is valid (no items in error, warning and info)
            experiments_validate_mock.reset_mock()
            retrieve_experiment_name_and_path_mock.reset_mock()
            format_validation_messages_mock.reset_mock()
            experiments_validate_mock.return_value = {"error": [], "warning": [], "info": []}

            experiment_validate_output = self.runner.invoke(experiments_app, ['validate'])
            retrieve_experiment_name_and_path_mock.assert_called_once_with(experiment_name=None)
            experiments_validate_mock.assert_called_once_with(experiment_path=self.path)
            self.assertIn("Experiment is valid", experiment_validate_output.stdout)

            # When application is valid with item in in 'info'
            experiments_validate_mock.reset_mock()
            retrieve_experiment_name_and_path_mock.reset_mock()
            format_validation_messages_mock.reset_mock()
            experiments_validate_mock.return_value = {"error": [], "warning": [], "info": ["info"]}

            experiment_validate_output = self.runner.invoke(experiments_app, ['validate'])
            retrieve_experiment_name_and_path_mock.assert_called_once_with(experiment_name=None)
            experiments_validate_mock.assert_called_once_with(experiment_path=self.path)
            self.assertIn("Experiment is valid", experiment_validate_output.stdout)

    def test_experiment_delete_no_experiment_dir(self):
        with patch.object(CommandProcessor, 'experiments_delete', return_value=True) as experiments_delete_mock, \
             patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_expname_and_path_mock:

            retrieve_expname_and_path_mock.return_value = self.path, self.experiment_name
            experiment_delete_output = self.runner.invoke(experiments_app, ['delete'])
            self.assertEqual(experiment_delete_output.exit_code, 0)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertIn("Experiment deleted successfully",
                          experiment_delete_output.stdout)

            retrieve_expname_and_path_mock.reset_mock()
            experiments_delete_mock.return_value = False
            experiment_delete_output = self.runner.invoke(experiments_app, ['delete'])
            self.assertEqual(experiment_delete_output.exit_code, 0)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertIn("Experiment files deleted",
                          experiment_delete_output.stdout)

    def test_experiment_delete_with_experiment_dir(self):
        with patch.object(CommandProcessor, 'experiments_delete', return_value=False) as experiments_delete_mock, \
             patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_expname_and_path_mock:

            retrieve_expname_and_path_mock.return_value = self.path, self.experiment_name
            experiment_delete_output = self.runner.invoke(experiments_app, ['delete', 'exp_dir'])
            experiments_delete_mock.assert_called_once_with(experiment_name=self.experiment_name,
                                                            experiment_path=self.path)
            self.assertEqual(experiment_delete_output.exit_code, 0)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertIn("Experiment files deleted, directory not empty",
                          experiment_delete_output.stdout)

    def test_experiment_delete_remote_with_experiment_dir(self):
        with patch.object(CommandProcessor, 'experiments_delete_remote_only',
                          return_value=False) as experiments_delete_mock:

            experiment_delete_output = self.runner.invoke(experiments_app, ['delete', '--remote'])
            self.assertIn("Remote experiment not deleted. No remote experiment id given",
                          experiment_delete_output.stdout)

            experiment_delete_output = self.runner.invoke(experiments_app, ['delete', '--remote', 'exp_dir'])
            self.assertIn("Remote experiment not deleted. No valid experiment id given",
                          experiment_delete_output.stdout)

            experiments_delete_mock.return_value = True
            experiment_delete_output = self.runner.invoke(experiments_app, ['delete', '--remote', 'exp_dir'])
            self.assertIn(f"Remote experiment with experiment name or id 'exp_dir' deleted successfully",
                          experiment_delete_output.stdout)

    def test_experiment_run_succeeds(self):
        with patch.object(CommandProcessor, 'experiments_validate') as exp_validate_mock, \
             patch.object(CommandProcessor, 'experiments_run') as exp_run_mock, \
             patch.object(LocalApi, "is_experiment_local") as exp_local_mock, \
             patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_expname_and_path_mock:

            retrieve_expname_and_path_mock.return_value = self.path, None
            exp_local_mock.return_value = True
            exp_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            exp_run_output = self.runner.invoke(experiments_app, ['run'])
            exp_validate_mock.assert_called_once_with(experiment_path=self.path)
            retrieve_expname_and_path_mock.assert_called_once()
            exp_run_mock.assert_called_once_with(experiment_path=self.path, block=True, update=False, timeout=None)
            self.assertEqual(exp_run_output.exit_code, 0)
            self.assertIn("Experiment is sent to the local server. Please wait until the results are received...",
                          exp_run_output.stdout)
            self.assertIn("Experiment run successfully. Check the results using command 'experiment results'",
                          exp_run_output.stdout)

            exp_local_mock.return_value = False
            retrieve_expname_and_path_mock.reset_mock()
            exp_run_mock.reset_mock()
            exp_run_mock.return_value = [{"round_result": "ok"}]
            exp_run_output = self.runner.invoke(experiments_app, ['run', '--timeout=30'])
            exp_run_mock.assert_called_once_with(experiment_path=self.path, block=False, update=False, timeout=30)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertEqual(exp_run_output.exit_code, 0)
            self.assertNotIn("Experiment is sent to the remote server. Please wait until the results are received...",
                             exp_run_output.stdout)
            self.assertIn("Experiment run successfully. Check the results using command 'experiment results'",
                          exp_run_output.stdout)

            exp_local_mock.return_value = False
            retrieve_expname_and_path_mock.reset_mock()
            exp_run_mock.reset_mock()
            exp_run_mock.return_value = None
            exp_run_output = self.runner.invoke(experiments_app, ['run', '--timeout=30'])
            exp_run_mock.assert_called_once_with(experiment_path=self.path, block=False, update=False, timeout=30)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertEqual(exp_run_output.exit_code, 0)
            self.assertNotIn("Experiment is sent to the remote server. Please wait until the results are received...",
                             exp_run_output.stdout)
            self.assertIn("Experiment sent successfully to server. "
                          "Check the results using command 'experiment results'",
                          exp_run_output.stdout)

    def test_experiment_run_fails(self):
        with patch.object(CommandProcessor, 'experiments_validate') as exp_validate_mock, \
             patch.object(CommandProcessor, 'experiments_run') as exp_run_mock, \
             patch.object(LocalApi, "is_experiment_local") as exp_local_mock, \
             patch("adk.command_list.format_validation_messages") as format_validation_messages_mock, \
             patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_expname_and_path_mock:

            retrieve_expname_and_path_mock.return_value = self.path, None
            exp_local_mock.return_value = True
            exp_validate_mock.return_value = {"error": ["Error occurred"], "warning": [], "info": []}
            exp_run_output = self.runner.invoke(experiments_app, ['run'])

            format_validation_messages_mock.assert_called_once()
            exp_local_mock.assert_not_called()
            exp_validate_mock.assert_called_once_with(experiment_path=self.path)
            retrieve_expname_and_path_mock.assert_called_once_with(experiment_name=None)
            exp_run_mock.assert_not_called()
            self.assertEqual(exp_run_output.exit_code, 1)
            self.assertIn("Experiment failed validation.",
                          exp_run_output.stdout)

            exp_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            exp_local_mock.return_value = False
            retrieve_expname_and_path_mock.reset_mock()
            exp_run_mock.reset_mock()
            exp_run_mock.return_value = [{"round_result": {"error": "Just an error"}}]
            exp_run_output = self.runner.invoke(experiments_app, ['run', '--timeout=30'])
            exp_run_mock.assert_called_once_with(experiment_path=self.path, block=False, update=False, timeout=30)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertEqual(exp_run_output.exit_code, 1)
            self.assertIn("Experiment encountered an error while running:",
                             exp_run_output.stdout)
            self.assertIn("Just an error",
                          exp_run_output.stdout)

    def test_experiment_run_update_succeeds(self):
        with patch.object(CommandProcessor, 'experiments_validate') as exp_validate_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch.object(CommandProcessor, 'experiments_run') as exp_run_mock, \
             patch.object(LocalApi, "is_experiment_local") as exp_local_mock, \
             patch.object(LocalApi, "get_experiment_application") as exp_application_mock, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_expname_and_path_mock:

            retrieve_expname_and_path_mock.return_value = self.path, None
            exp_application_mock.return_value = self.application
            retrieve_appname_and_path_mock.return_value = self.path, self.application
            exp_local_mock.return_value = True
            exp_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            app_validate_mock.return_value = {"error": [], "warning": [], "info": []}

            exp_run_output = self.runner.invoke(experiments_app, ['run', '--update'])
            exp_validate_mock.assert_called_once_with(experiment_path=self.path)
            retrieve_expname_and_path_mock.assert_called_once()
            exp_run_mock.assert_called_once_with(experiment_path=self.path, block=True, update=True, timeout=None)
            self.assertEqual(exp_run_output.exit_code, 0)
            self.assertIn("Experiment is sent to the local server. Please wait until the results are received...",
                          exp_run_output.stdout)
            self.assertIn("Experiment run successfully. Check the results using command 'experiment results'",
                          exp_run_output.stdout)

    def test_experiment_run_update_fails(self):
        with patch.object(CommandProcessor, 'experiments_validate') as exp_validate_mock, \
             patch.object(CommandProcessor, 'applications_validate') as app_validate_mock, \
             patch.object(CommandProcessor, 'experiments_run') as exp_run_mock, \
             patch.object(LocalApi, "is_experiment_local") as exp_local_mock, \
             patch.object(LocalApi, "get_experiment_application") as exp_application_mock, \
             patch("adk.command_list.format_validation_messages") as format_validation_messages_mock, \
             patch("adk.command_list.retrieve_application_name_and_path") as retrieve_appname_and_path_mock, \
             patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_expname_and_path_mock:

            retrieve_expname_and_path_mock.return_value = self.path, None
            exp_validate_mock.return_value = {"error": [], "warning": [], "info": []}
            exp_local_mock.return_value = False
            exp_run_output = self.runner.invoke(experiments_app, ['run', '--timeout=30', '--update'])
            exp_run_mock.assert_not_called()
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertEqual(exp_run_output.exit_code, 0)
            self.assertIn("Update only valid for local experiment runs", exp_run_output.stdout)

            exp_run_mock.reset_mock()
            retrieve_expname_and_path_mock.reset_mock()
            retrieve_expname_and_path_mock.return_value = self.path, None
            exp_application_mock.return_value = self.application
            retrieve_appname_and_path_mock.return_value = self.path, self.application
            app_validate_mock.return_value = {"error": ["App-error occurred"], "warning": [], "info": []}
            exp_validate_mock.return_value = {"error": [], "warning": [], "info": []}

            exp_local_mock.return_value = True
            exp_run_output = self.runner.invoke(experiments_app, ['run', '--timeout=30', '--update'])
            exp_run_mock.assert_not_called()
            format_validation_messages_mock.assert_called_once()
            retrieve_expname_and_path_mock.assert_called_once()
            retrieve_appname_and_path_mock.assert_called_once()
            self.assertEqual(exp_run_output.exit_code, 1)
            self.assertIn(f"Experiment cannot be updated", exp_run_output.stdout)
            self.assertIn(f"Application '{self.application}' failed validation.", exp_run_output.stdout)

    def test_experiment_results(self):
        with patch.object(CommandProcessor, 'experiments_results') as exp_results_mock, \
             patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_expname_and_path_mock:

            retrieve_expname_and_path_mock.return_value = self.path, None
            exp_results_output = self.runner.invoke(experiments_app, ['results'])

            exp_results_mock.assert_called_once_with(all_results=False, experiment_path=self.path)
            self.assertEqual(exp_results_output.exit_code, 0)
            retrieve_expname_and_path_mock.assert_called_once()

            retrieve_expname_and_path_mock.reset_mock()
            exp_results_mock.reset_mock()
            exp_results_mock.return_value = ['r1', 'r2']
            exp_results_output = self.runner.invoke(experiments_app, ['results', '--all', '--show'])
            exp_results_mock.assert_called_once_with(all_results=True, experiment_path=self.path)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertEqual(exp_results_output.exit_code, 0)
            self.assertIn("['r1', 'r2']", exp_results_output.stdout)

            retrieve_expname_and_path_mock.reset_mock()
            exp_results_mock.reset_mock()
            exp_results_output = self.runner.invoke(experiments_app, ['results', '--all'])
            exp_results_mock.assert_called_once_with(all_results=True, experiment_path=self.path)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertEqual(exp_results_output.exit_code, 0)
            self.assertIn(f"Results are stored at location '{self.path / 'results' / 'processed.json'}'",
                          exp_results_output.stdout)

    def test_experiment_results_no_success(self):
        with patch.object(CommandProcessor, 'experiments_results') as exp_results_mock, \
             patch("adk.command_list.retrieve_experiment_name_and_path") as retrieve_expname_and_path_mock:

            retrieve_expname_and_path_mock.return_value = self.path, None
            exp_results_mock.return_value = None
            exp_results_output = self.runner.invoke(experiments_app, ['results'])

            exp_results_mock.assert_called_once_with(all_results=False, experiment_path=self.path)
            self.assertEqual(exp_results_output.exit_code, 0)
            retrieve_expname_and_path_mock.assert_called_once()
            self.assertIn("No results received from backend yet. Check again later using command 'experiment results'",
                          exp_results_output.stdout)

    def test_networks_list(self):
        with patch.object(CommandProcessor, "networks_list") as networks_list_mock:

            networks_list_mock.side_effect = [self.net_dict_1, self.net_dict_2,
                                              self.net_dict_3, self.net_dict_4,
                                              self.net_dict_5]

            result_list = self.runner.invoke(networks_app, ['list'])
            networks_list_mock.assert_called_once_with(remote=False, local=True)
            self.assertEqual(result_list.exit_code, 0)
            self.assertIn('There are no local networks available', result_list.stdout)

            networks_list_mock.reset_mock()
            result_list = self.runner.invoke(networks_app, ['list', '--local'])
            networks_list_mock.assert_called_once_with(remote=False, local=True)
            self.assertEqual(result_list.exit_code, 0)
            self.assertIn('3 local network(s)', result_list.stdout)
            self.assertIn('network name', result_list.stdout)
            self.assertIn('1', result_list.stdout)
            self.assertIn('2', result_list.stdout)
            self.assertIn('3', result_list.stdout)

            networks_list_mock.reset_mock()
            result_list = self.runner.invoke(networks_app, ['list', '--remote', '--local'])
            networks_list_mock.assert_called_once_with(remote=True, local=False)
            self.assertEqual(result_list.exit_code, 0)
            self.assertIn('There are no remote networks available', result_list.stdout)

            networks_list_mock.reset_mock()
            result_list = self.runner.invoke(networks_app, ['list', '--remote', '--local'])
            networks_list_mock.assert_called_once_with(remote=True, local=False)
            self.assertEqual(result_list.exit_code, 0)
            self.assertIn('2 remote network(s)', result_list.stdout)
            self.assertIn('network name', result_list.stdout)
            self.assertIn('5', result_list.stdout)
            self.assertIn('6', result_list.stdout)

            networks_list_mock.reset_mock()
            result_list = self.runner.invoke(networks_app, ['list', '--remote'])
            networks_list_mock.assert_called_once_with(remote=True, local=True)
            self.assertEqual(result_list.exit_code, 0)
            self.assertIn('3 local network(s)', result_list.stdout)
            self.assertIn('network name', result_list.stdout)
            self.assertIn('1', result_list.stdout)
            self.assertIn('2', result_list.stdout)
            self.assertIn('3', result_list.stdout)
            self.assertIn('2 remote network(s)', result_list.stdout)
            self.assertIn('network name', result_list.stdout)
            self.assertIn('5', result_list.stdout)
            self.assertIn('6', result_list.stdout)

    def test_networks_update(self):
        with patch.object(CommandProcessor, "networks_update") as networks_update_mock:

            networks_update_mock.return_value = True
            result_update = self.runner.invoke(networks_app, ['update'])
            networks_update_mock.assert_called_once_with(overwrite=False)
            self.assertEqual(result_update.exit_code, 0)
            self.assertIn('The local networks are updated', result_update.stdout)

            networks_update_mock.reset_mock()
            networks_update_mock.return_value = True
            result_update = self.runner.invoke(networks_app, ['update', '--overwrite'])
            networks_update_mock.assert_called_once_with(overwrite=True)
            self.assertEqual(result_update.exit_code, 0)
            self.assertIn('The local networks are updated', result_update.stdout)

            networks_update_mock.reset_mock()
            networks_update_mock.return_value = False
            result_update = self.runner.invoke(networks_app, ['update'])
            networks_update_mock.assert_called_once_with(overwrite=False)
            self.assertEqual(result_update.exit_code, 0)
            self.assertIn('The local networks are not updated completely', result_update.stdout)
