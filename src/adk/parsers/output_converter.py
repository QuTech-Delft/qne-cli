import os
import shutil
from typing import Any, cast, Dict, List, Optional
import yaml

from adk.generators.network_generator import FullyConnectedNetworkGenerator
from adk.generators.instruction_generator import InstructionGenerator
from adk.generators.result_generator import ResultGenerator
from adk.type_aliases import ResultType, CumulativeResultType, LogEntryType, RoundSetType


class OutputConverter:
    """
    Class to process the output of the application run.
    Contains methods to convert the output from netqasm into QNE format
    """
    ROLE_INSTRS_LOG = "instrs"
    ROLE_CLASS_COMM_LOG = "class_comm"
    ROLE_APP_LOG = "app_log"
    ROLE_LOG_TYPES = [ROLE_INSTRS_LOG, ROLE_CLASS_COMM_LOG, ROLE_APP_LOG]
    GENERIC_LOG_FILES = ["network_log.yaml"]

    def __init__(self, round_set: RoundSetType, log_dir: str, output_dir: str,
                 instruction_converter: Optional[FullyConnectedNetworkGenerator] = None):
        self._log_dir = log_dir
        self._round_set = round_set
        self._instruction_converter = instruction_converter
        self._log_files_dir = os.path.join(log_dir, output_dir)

    def prepare_output(self) -> None:
        if not os.path.isdir(self._log_dir):
            os.makedirs(self._log_dir)

    def __get_node_names(self) -> List[str]:
        """Get the names of the nodes in the application.

        The results.yaml file contains the result for the various nodes used in the application. This data will be used
        to determine which nodes exist in the application.

        Returns:
            List of node names.
        """
        result_file = os.path.join(self._log_files_dir, 'results.yaml')
        result = self.__read_yaml_file(result_file)
        return [key.split('app_', 1)[1] for key in result[0] if key.startswith('app_')]

    @staticmethod
    def __read_yaml_file(file_path: str) -> Any:
        """Read the content from a YAML file.

        Args:
            file_path: location and name of the file to read.

        Returns:
            Content of the YAML file.
        """
        with open(file_path, encoding="utf-8") as fp:
            return yaml.load(fp, Loader=yaml.FullLoader)

    def __list_log_files(self) -> List[Dict[str, Optional[str]]]:
        """Build a list of existing log files in the OutputConverter's output directory.

        Based on existing roles and possible log file names, build a list of files that actually exist. This list can
        subsequently be used by methods that combine/sort log files, clean up log files, etc.

        Returns:
            List of dictionaries with existing log files and their properties.
        """
        log_files = []

        def add_to_log_files(log_file_basename: str, log_type: str, node: Optional[str]) -> None:
            log_file = os.path.join(self._log_files_dir, log_file_basename)
            if os.path.exists(log_file):
                log_files.append({
                    "name": log_file,
                    "type": log_type,
                    "node": node,
                })

        for node in self.__get_node_names():
            for log_type in OutputConverter.ROLE_LOG_TYPES:
                add_to_log_files(f'{node}_{log_type}.yaml', log_type, node)

        for general_log in OutputConverter.GENERIC_LOG_FILES:
            add_to_log_files(general_log, "generic", None)

        return log_files

    def __combine_log_files(self, log_files: List[Dict[str, Optional[str]]]) -> List[LogEntryType]:
        """Combine the various log files produced by the NetSquid simulator.

        The simulator generates log files that are stored in the output directory. These files are combined into one
        log file and sorted by wall-clock time (WCT). Additional fields (e.g. log type or missing INS) are added here
        to ease processing.

        Returns:
             Sorted list of all combined logs.
        """
        logs = []
        for log_file in log_files:
            log_records = self.__read_yaml_file(cast(str, log_file['name']))
            for log_record in log_records:
                if log_file['type'] == OutputConverter.ROLE_APP_LOG:
                    log_record['INS'] = 'user_msg'
                if 'INS' not in log_record or 'WCT' not in log_record:
                    raise KeyError("Log record should contain an INS and WCT field.")
                log_record.update({
                    'TYP': log_file['type'],
                    'FRM': log_file['node']
                })
                if log_file['type'] == OutputConverter.ROLE_INSTRS_LOG \
                        and not log_record['INS'] == 'create_epr' \
                        and not log_record['INS'] == 'recv_epr':
                    log_record['GAT'] = log_record['INS']
                    if log_record['INS'] != "BSM":
                        log_record['INS'] = 'apply_gate'    #TODO: Should every 'INS' be of type 'apply_gate'?
                logs.append(log_record)

        return sorted(logs, key=lambda l: cast(str, l['WCT']))

    def convert(self, round_number: int) -> ResultType:
        """Convert result and log files for one round number into a Result format compatible with the QNE

        NetSquid logs all actions that are performed in the applications. These log_entries are converted into
        instructions that can be interpreted by either humans or end-user interfaces.

        The results.yaml file is read into a dictionary and placed in the Result without conversion.

        Returns:
            Result object from ResultGenerator
        """
        instructions = []

        log_entries = self.__combine_log_files(self.__list_log_files())
        log_entries.append({"INS": "application_finished"})
        for log_entry in log_entries:
            try:
                instruction_list = InstructionGenerator.generate(log_entry)
            except KeyError as key_error:
                raise KeyError(f"Could not find field {key_error} while processing instruction {log_entry}") \
                    from key_error
            instructions += instruction_list

        if self._instruction_converter is not None:
            self._instruction_converter.convert(instructions)
        result_file = os.path.join(self._log_files_dir, 'results.yaml')
        round_result = self.__read_yaml_file(result_file)

        cumulative_result: CumulativeResultType = {}
        result = ResultGenerator.generate(self._round_set, round_number, round_result, instructions, cumulative_result)
        return result

    def __clean(self) -> None:
        """Cleans all files from the log directory.

        All yaml files and instructions json file have to be deleted. Given that the directory is automatically created,
        all files can be safely deleted.

        Note: Keep in mind never to point the output or cache directory to an actual source folder.
        """
        if os.path.isdir(self._log_dir):
            shutil.rmtree(self._log_dir)
        os.makedirs(self._log_dir)

    def terminate(self) -> None:
        """Terminate this OutputConverter."""
        self.__clean()
