import os
from typing import Optional, Any
import yaml

class VanillaNetSquidLogger:

    """
        Logging class for Vanilla Netsquid Programs
    """

    def __init__(self, app_role:str, directory: str, role_mappings: dict[str, str]):

        self.role_mappings = role_mappings
        self.instrs_logs = []
        self.qlink_logs = []
        self.clink_logs = []

        self.instr_log_file = os.path.join(directory, f'{app_role}_instrs.yaml')
        self.qlink_log_file = os.path.join(directory, 'network_log.yaml')
        self.clink_log_file = os.path.join(directory, f'{app_role}_class_comm.yaml')

    def add_log_command(
            self,
            message:str,
            log_type:str,
            ins:str,
            sim_time:float,
            sender:Optional[str] = None,
            receiver:Optional[str] = None,
            value:Optional[Any] = None
        ):

        """
            Add log to the respective log list.

            Args
            -------
            message: str
                Loggin message.

            log_type: str
                Defines the type of log entry. Can be one of
                    - "node-log" (for logging operations within a node)
                    - "clink-log" (for logging classical communication)
                    - "qlink-log" (for logging quantum communication)
                Else, message will not be logged.

            ins: str
                Type of instruction that is the case of the log. Can be one of:
                    ["FlyingQubitSent", "WAIT_RECV", "RECV", "SEND", "BSM]

            sim_time: float
                Simulation time at which this message was logged.

            sender: Optional[str]
                Name of the sender in case of a (classical/quantum) communication log

            receiver: Optional[str]
                Name of the receiver in case of a (classical/quantum) communication log

            value: Optional[Any]
                Output value that will be displayed in processed.json
        """

        if log_type == "node-log":
            self.instrs_logs.append({
                "INS": ins,
                "LOG": message,
                "WCT": sim_time,
                "OUT": value
            })
        elif log_type == "clink-log":
            self.clink_logs.append({
                "INS": ins,
                "LOG": message,
                "WCT": sim_time,
                "SEN": sender,
                "REC": receiver,
                "MSG": value
            })
        elif log_type == "qlink-log":
            sender_node = self.role_mappings[sender]
            receiver_node = self.role_mappings[receiver]
            self.qlink_logs.append({
                "INS": ins,
                "LOG": message,
                "WCT": sim_time,
                "NOD": [sender_node, receiver_node],
                "PTH": f"{sender_node}-{receiver_node}"
            })

    def finish_logging(self):
        """
            Write to log file at the end.
        """

        if self.instrs_logs:
            with open(self.instr_log_file, 'w', encoding='utf8') as file:
                for item in self.instrs_logs:
                    yaml.dump([item], file)

        if self.qlink_logs:
            with open(self.qlink_log_file, 'a', encoding='utf8') as file:
                for item in self.qlink_logs:
                    yaml.dump([item], file)

        if self.clink_logs:
            with open(self.clink_log_file, 'w', encoding='utf8') as file:
                for item in self.clink_logs:
                    yaml.dump([item], file)
