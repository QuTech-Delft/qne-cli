from abc import ABC, abstractmethod
from typing import Dict, Any, List, Type, Optional
import logging

from adk.type_aliases import DefaultPayloadType, InstructionType, LogEntryType, QuantumStateType
from adk.parsers.encoders import JSONEncoder


class BaseInstruction(ABC):
    template: InstructionType = {}

    def __init__(self, log_entry: LogEntryType) -> None:
        self._log_entry = log_entry

    @property
    @abstractmethod
    def payload(self) -> InstructionType:
        """Return an instruction dictionary to update an instruction's template with."""

    def transform(self) -> InstructionType:
        template = self.template.copy()
        template.update(self.payload)
        return template

    def _get_qubit(self, qubit: List[DefaultPayloadType]) -> Dict[str, DefaultPayloadType]:
        return {
            "node": qubit[0],
            "id": qubit[1]
        }

    def _get_node(self, key: str) -> Dict[str, str]:
        return {
            "node": self._get_field(key)
        }

    def _get_field(self, key: str) -> Any:
        return self._log_entry[key]

    def _get_groups(self) -> Dict[str, Dict[str, Any]]:
        groups_in = self._get_field("QGR")

        groups = {}
        if groups_in is not None:
            for group_id, properties in groups_in.items():
                state: Dict[str, QuantumStateType] = {}
                JSONEncoder.encode(state, properties["state"])
                groups[str(group_id)] = {
                    "qubits": [self._get_qubit(q) for q in properties['qubit_ids']],
                    "is_entangled": properties["is_entangled"],
                    "state": state["json"]
                }

        return groups

    @staticmethod
    @abstractmethod
    def get_instruction() -> str:
        """Return the instruction name from the simulator that should map to this instruction class."""


class ApplicationFinishedInstruction(BaseInstruction):
    template = {
        "command": "application-finished",
    }

    @property
    def payload(self) -> InstructionType:
        return {}

    @staticmethod
    def get_instruction() -> str:
        return "application_finished"


class UserMessageInstruction(BaseInstruction):
    template = {
        "command": "user-message",
        "message": None,
        "from": None
    }

    @property
    def payload(self) -> InstructionType:
        return {
            'message': self._get_field('LOG'),
            'from': self._get_node('FRM')
        }

    @staticmethod
    def get_instruction() -> str:
        return "user_msg"


class EntanglementInstruction(BaseInstruction):
    template: Dict[str, Any] = {
        "command": "entanglement",
        "action": None,
        "from": None,
        "to": None,
        "channels": None,
        "groups": None,
    }

    @property
    def payload(self) -> InstructionType:
        qubits: List[List[DefaultPayloadType]] = list(map(list, zip(self._get_field("NOD"), self._get_field("QID"))))
        return {
            'action': self._get_action(),
            'from': self._get_qubit(qubits[0]),
            'to': self._get_qubit(qubits[1]),
            'channels': self._get_field("PTH"),
            'groups': self._get_groups(),
        }

    @staticmethod
    @abstractmethod
    def _get_action() -> str:
        """EntanglementInstruction subclass has to indicate which entanglement action it represents."""

    @staticmethod
    @abstractmethod
    def get_instruction() -> str:
        """Instruction name from simulator only exists for subclasses of EntanglementInstruction."""


class EntanglementStartInstruction(EntanglementInstruction):
    @staticmethod
    def _get_action() -> str:
        return "start"

    @staticmethod
    def get_instruction() -> str:
        return "epr_EntanglementStage.START"


class EntanglementFinishInstruction(EntanglementInstruction):
    @staticmethod
    def _get_action() -> str:
        return "success"

    @staticmethod
    def get_instruction() -> str:
        return "epr_EntanglementStage.FINISH"


class ClassicalMessageInstruction(BaseInstruction):
    template = {
        "command": "classical-message",
        "message": None,
        "from": None,
        "to": None
    }

    @property
    def payload(self) -> InstructionType:
        return {
            'message': self._get_field('MSG'),
            'from': self._get_node('SEN'),
            'to': self._get_node('REC')
        }

    @staticmethod
    def get_instruction() -> str:
        return "SEND"


class ApplyGateInstruction(BaseInstruction):
    template = {
        "command": "apply-gate",
        "qubits": None,
        "gate": None,
        "parameters": None,
        "groups": None,
        "outcome": None
    }

    @property
    def payload(self) -> InstructionType:
        qubits = []
        qids = self._get_field('QID')
        if qids is not None:
            for qid in qids:
                qubits.append(
                    self._get_qubit([self._get_field("FRM"), qid])
                )
        return {
            'qubits': qubits,
            'gate': self._get_field('GAT'),
            'groups': self._get_groups(),
            'outcome': self._get_field('OUT')
        }

    @staticmethod
    def get_instruction() -> str:
        return "apply_gate"


class BSMInstruction(BaseInstruction):
    template = {
        "command": "bsm-measurement",
        "qubits": None,
        "gate": "BSM",
        "parameters": None,
        "groups": None,
        "outcome": None
    }

    @property
    def payload(self) -> InstructionType:
        return {
            'outcome': self._get_field('OUT')
        }

    @staticmethod
    def get_instruction() -> str:
        return "BSM"

class TransferQubitInstruction(BaseInstruction):
    template: Dict[str, Any] = {
        "command": "transfer-qubit",
        "action": None,
        "from": None,
        "to": None,
        "channels": None,
        "groups": None,
    }

    @property
    def payload(self) -> InstructionType:
        nodes = self._get_field("NOD")
        return {
            'action': self._get_action(),
            'from': nodes[0],
            'to': nodes[1],
            'channels': self._get_field("PTH"),
        }

    @staticmethod
    @abstractmethod
    def _get_action() -> str:
        """TransferQubitInstruction subclass has to indicate which entanglement action it represents."""

    @staticmethod
    @abstractmethod
    def get_instruction() -> str:
        """Instruction name from simulator only exists for subclasses of TransferQubitInstruction."""


class StartTransferQubitInstruction(TransferQubitInstruction):
    @staticmethod
    def _get_action() -> str:
        return "send"

    @staticmethod
    def get_instruction() -> str:
        return "FlyingQubitSent"


class FinishTransferQubitInstruction(TransferQubitInstruction):
    @staticmethod
    def _get_action() -> str:
        return "finished"

    @staticmethod
    def get_instruction() -> str:
        return "FlyingQubitReceive"

class InstructionGenerator:
    INSTRUCTION_CLASSES = [ApplicationFinishedInstruction, ApplyGateInstruction, EntanglementStartInstruction,
                           EntanglementFinishInstruction, ClassicalMessageInstruction, UserMessageInstruction,
                           BSMInstruction, StartTransferQubitInstruction, FinishTransferQubitInstruction]

    INSTRUCTION_MAPPING = {}
    for instruction_class in INSTRUCTION_CLASSES:
        INSTRUCTION_MAPPING[instruction_class.get_instruction()] = instruction_class

    @staticmethod
    def generate(log_entry: LogEntryType) -> List[InstructionType]:
        instruction = log_entry['INS']
        cls: Optional[Type[BaseInstruction]] = InstructionGenerator.INSTRUCTION_MAPPING.get(instruction, None)

        instructions = []
        if cls is not None:
            instruction = cls(log_entry).transform()
            instructions.append(instruction)
        else:
            logging.debug("InstructionGenerator: unknown instruction (%s)", instruction)
        return instructions
