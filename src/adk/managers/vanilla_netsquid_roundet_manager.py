import os
from pathlib import Path
import shutil
from subprocess import CalledProcessError, TimeoutExpired
from typing import Any, Dict, List, Optional

import importlib.util
import sys
import concurrent.futures
from datetime import datetime
import yaml
import netsquid as ns

from adk.parsers.input_parser import InputParser
from adk.parsers.output_converter import OutputConverter
from adk.generators.netsquid_network_generator import create_netsquid_fully_connected_network
from adk.generators.vanilla_netsquid_log_generator import VanillaNetSquidLogger
from adk.generators.result_generator import ErrorResultGenerator
from adk.type_aliases import ResultType, RoundSetType


class VanillaNetSquidRoundSetManager:
    """
    This class runs a single round of the application on the Vanilla NetSquid simulator.
    Uses the InputParser class to process the input and prepare it for running application.
    Uses the OutputConverter class to process the output of NetSquid and convert it to a result in QNE format.
    If the application run fails, then an error result is generated containing the reason for failure.
    """
    def __init__(self, round_set: RoundSetType, asset: Dict[str, Any], experiment_path: Path) -> None:
        self.__asset = asset
        self.__round_set = round_set
        self.__path = experiment_path
        self.__input_dir = str(experiment_path / "input")
        self.__log_dir = str(experiment_path / "raw_output")
        self.__output_dir = "LAST"

        # Create and connect NetSquid Nodes based on network config.
        self.netsquid_nodes = create_netsquid_fully_connected_network(
                                role_dict=self.__asset['network']['roles'],
                                node_properties=self.__asset['network']['nodes'],
                                channel_properties=self.__asset['network']['channels']
                            )

        self.__input_parser = InputParser(input_dir=self.__input_dir)
        self.__output_converter = OutputConverter(
            round_set=self.__round_set,
            log_dir=self.__log_dir,
            output_dir=self.__output_dir
        )

    def process(self, timeout: Optional[int] = None) -> List[ResultType]:
        """
        Process a round by running the application on simulator.

        Args:
            timeout: Limit the wait for result

        Returns:
            The result of the application run
        """
        round_failed = False
        round_number = 1
        self.__input_parser.prepare_input(self.__asset)
        self.__output_converter.prepare_output()

        exception_type: str = ""
        message: str = ""
        trace: Optional[str] = None
        try:
            self._run_application(timeout)
        except CalledProcessError as exc:
            exception_type = type(exc).__name__
            message = f"NetSquid returned with exit status {exc.returncode}."
            trace = exc.stderr.decode() if exc.stderr is not None else None
            round_failed = True
        except TimeoutExpired as exc:
            exception_type = type(exc).__name__
            message = f"Call to simulator timed out after {exc.timeout} seconds."
            trace = exc.stderr.decode() if exc.stderr is not None else None
            round_failed = True
        except Exception as exc:
            exception_type = type(exc).__name__
            trace = None
            message = str(exc)
            round_failed = True

        if round_failed:
            result = ErrorResultGenerator.generate(self.__round_set, round_number, exception_type, message, trace)
        else:
            result = self.__output_converter.convert(round_number)

        return [result]

    def __clean(self) -> None:
        """Cleans up all files in the input directory.

        Given that the source files provided by the application developer can have any format (not just app_*.py, but
        also src/*.py) all pythons need to be deleted. Furthermore, all *.yaml files need to be removed. Given that the
        directory is automatically created, all files can be safely deleted.

        Note: Keep in mind never to point the input or cache directory to an actual source folder.
        """
        if os.path.isdir(self.__input_dir):
            shutil.rmtree(self.__input_dir)
        os.makedirs(self.__input_dir)

    def terminate(self) -> None:
        """Clean up everything that the InputParser/RoundSetManager has created."""
        self.__clean()

    def _run_application(self, timeout: Optional[int] = None) -> None:

        """Execute the program runner for vanilla NetSquid progrmas.

        Args:
            timeout: Limit the wait for result

        Raises:
            CalledProcessError: If the application has failed, an exception is raised.
            TimeoutExpired: If the application runs longer than expected.
        """

        #TODO: Better error handling.
        #TODO: Handle timeout.

        role_dict = self.__asset['network']['roles']
        sys.path.append(os.path.abspath(self.__path / "input"))

        # Remove raw_output/LAST directory if it exists
        last_directory = self.__path / "raw_output/LAST"
        if os.path.isdir(last_directory):
            shutil.rmtree(last_directory)

        # Create raw_output/WTC directory
        wtc = datetime.now().strftime("%Y%m%d-%H%M%S")
        wtc_directory = self.__path / "raw_output" / wtc
        wtc_directory.mkdir(parents=True)

        # Create fresh raw_output/LAST directrory
        if not last_directory.exists():
            last_directory.mkdir(parents=True)

        # Import main function from all app_*.py files and
        # gather all application-specific inputs.
        main_function = {}
        input_values = {}
        for role in role_dict:
            netsquid_filename = "app_"+str(role)+".py"
            script_path = self.__path / "input" / netsquid_filename

            module_name = os.path.splitext(os.path.basename(script_path))[0]
            spec = importlib.util.spec_from_file_location(module_name, script_path)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            main_function[role] = module

            input_filenane = str(role)+".yaml"
            input_yaml_path = self.__path / "input" / input_filenane
            with open(input_yaml_path, 'r', encoding='utf8') as file:
                input_dict = yaml.safe_load(file)
            logger = VanillaNetSquidLogger(app_role=role, directory=last_directory, role_mappings=role_dict)

            class AppConfig:
                node = self.netsquid_nodes[role]
                log_config = logger
            input_dict["app_config"] = AppConfig()
            input_values[role] = input_dict

        # Run program on every node
        with concurrent.futures.ThreadPoolExecutor() as executor:
            results = {executor.submit(main_function[role].main, **input_values[role]): role for role in role_dict}
            ns.sim_run()
            final_result = {}
            for future in concurrent.futures.as_completed(results):
                try:
                    result = future.result()
                    role_name = results[future]
                    final_result[f"app_{role_name}"] = result
                except Exception as e:
                    print(e)

        # Write results to results.yaml file of LAST directory
        output_result_yaml = self.__path / "raw_output/LAST/results.yaml"
        with open(output_result_yaml, 'w', encoding='utf8') as file:
            yaml.dump([final_result], file)

        # Copy contents from the LAST directory to the WTC directory
        shutil.copytree(last_directory, wtc_directory, dirs_exist_ok=True)
