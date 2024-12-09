import math
import random
from itertools import combinations
from netsquid.nodes import Node
import netsquid.components.instructions as instr
from netsquid.components.qprocessor import QuantumProcessor
from netsquid.components.qprocessor import PhysicalInstruction
from netsquid.components.models.qerrormodels import FibreLossModel, DepolarNoiseModel
from netsquid.nodes import DirectConnection
from netsquid.components import QuantumChannel, ClassicalChannel
from netsquid.components.models.cerrormodels import ClassicalErrorModel


class BSMNoiseModel(ClassicalErrorModel):
    """Model for applying BSM detector efficieny.

    Args
    ----------
    det_eff : float
        Probability that detector will provide the right BSM result.
        The incorrect result is a random number from the list(range(4))
    """

    def __init__(self, det_eff: float, **kwargs):
        super().__init__(**kwargs)
        self.det_eff = det_eff

    def error_operation(self, items, delta_time=0, **kwargs):
        if random.random() > self.det_eff:
            items[0] = random.randint(0,3)


def create_qlink(
        node_one: Node,
        node_two: Node,
        distance: float,
        link_properties: dict
    ) -> None:

    """
        Create a Quantum link between two NetSquid Node objects.


        Args
        -------
        node_one: Node
            NetSquid Node object representing the first node.
        node_two: Node
            NetSquid Node object representing the second node.
        distance: float
            Link distance between node_one and node_two
        link_properties: dict
            Channel properties from the experiment asset.

    """

    node_one_name = node_one.name
    node_two_name = node_two.name

    # TODO: Is it always params["values"][0]?
    parameters = {
        params["values"][0]["name"]: params["values"][0]["value"]
        for params in link_properties["parameters"]
    }
    loss_model = FibreLossModel(**parameters)

    qchannel_1 = QuantumChannel(
                    name="qchannel["+ node_one_name +" to "+node_two_name + "]",
                    length=distance,
                    models={'quantum_loss_model': loss_model}
                )
    qchannel_2 = QuantumChannel(
                    name="qchannel["+ node_two_name +" to "+node_one_name + "]",
                    length=distance,
                    models={'quantum_loss_model': loss_model}
                )
    qconnection = DirectConnection(
                    name="qconn_direct[" + node_one_name + "|" + node_two_name + "]",
                    channel_AtoB=qchannel_1,
                    channel_BtoA=qchannel_2
                )

    node_one.connect_to(
        remote_node=node_two,
        connection=qconnection,
        local_port_name="qlink_"+node_two_name,
        remote_port_name="qlink_"+node_one_name
    )


def create_clink(node_one: Node, node_two: Node, distance: float = 1.0) -> None:

    """
        Create a Classical link between two NetSquid Node objects.

        Args
        -------
        node_one: Node
            NetSquid Node object representing the first node.
        node_two: Node
            NetSquid Node object representing the second node.
        distance: float
            Link distance between node_one and node_two (in km).
    """

    node_one_name = node_one.name
    node_two_name = node_two.name

    cchannel_1 = ClassicalChannel(name="cchannel_1", length=distance)
    cchannel_2 = ClassicalChannel(name="cchannel_2", length=distance)
    connection = DirectConnection(
                    name="cconn",
                    channel_AtoB=cchannel_1,
                    channel_BtoA=cchannel_2
                )

    node_one.connect_to(
        remote_node=node_two,
        connection=connection,
        local_port_name="clink_"+node_two_name,
        remote_port_name="clink_"+node_one_name
    )


def create_processor(node_properties: dict) -> QuantumProcessor:

    """
        Define the Quantum Processor object on NetSquid Node.

        Args
        -------
        node_properties: dict
            Node properties from the experiment asset.
    """


    # TODO: Is it always params["values"][0]?
    parameters = {
        params["values"][0]["name"]: params["values"][0]["value"]
        for params in node_properties["node_parameters"]
    }
    num_qubits = len(node_properties["qubits"])

    try:
        bsm_noise_model = BSMNoiseModel(**parameters)
    except Exception:
        bsm_noise_model = BSMNoiseModel(det_eff=1)

    try:
        memory_noise_model = DepolarNoiseModel(**parameters)
    except Exception:
        memory_noise_model = DepolarNoiseModel(depolar_rate=0)

    physical_instructions = [
        PhysicalInstruction(instr.INSTR_INIT, duration=3, parallel=True),
        PhysicalInstruction(instr.INSTR_H, duration=1, parallel=True),
        PhysicalInstruction(instr.INSTR_X, duration=1, parallel=True),
        PhysicalInstruction(instr.INSTR_Z, duration=1, parallel=True),
        PhysicalInstruction(instr.INSTR_S, duration=1, parallel=True),
        PhysicalInstruction(instr.INSTR_CNOT, duration=4, parallel=True),
        PhysicalInstruction(instr.INSTR_MEASURE, duration=7, parallel=False),
        PhysicalInstruction(instr.INSTR_MEASURE_X, duration=7, parallel=False),
        PhysicalInstruction(instr.INSTR_MEASURE_BELL, duration=7, parallel=False,
                            classical_noise_model=bsm_noise_model)
    ]

    processor = QuantumProcessor("quantum_processor", num_positions=num_qubits,
                                 memory_noise_models=[memory_noise_model] * num_qubits,
                                 phys_instructions=physical_instructions)
    return processor


def link_distance(node_one_coords: dict[str, float], node_two_coords: dict[str, float]) -> float:

    """
        Calculate distance between two nodes given their
        {"latitude": latitude, "longitude": longitude}
        coordinates in Python dictionary form.

        Args
        -------
        node_one_coords: dict[str, float]
            Latitude and Longitude coordinates of the first ndoe.
        node_two_coords: dict[str, float]
            Latitude and Longitude coordinates of the second ndoe.
    """

    # Convert latitude and longitude from degrees to radians
    lat1, lon1, lat2, lon2 = map(
        math.radians, [
            node_one_coords["latitude"],
            node_one_coords["longitude"],
            node_two_coords["latitude"],
            node_two_coords["longitude"]
        ]
    )

    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = math.sin(dlat / 2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    r = 6371.0 # Radius of earth
    return c * r


def create_netsquid_fully_connected_network(
        role_dict: dict,
        node_properties: dict,
        channel_properties: dict
    ) -> dict[Node]:

    """
        Create and connect NetSquid Nodes based on Network Configuration.

        Args
        -------
        role_dict: dict
            Role dictionary from the experiment asset.
        node_properties: dict
            Node properties of the whole network from the experiment asset.
        channel_properties: dict
            Channel properties of the whole network from the experiment asset.
    """

    netsquid_nodes = {}
    role_node_property_mapping = {}

    for role in role_dict:
        for node_property in node_properties:
            if node_property['slug'] == role_dict[role]:
                netsquid_nodes[role] = Node(name=role, qmemory=create_processor(node_property))
                role_node_property_mapping[role] = node_property
                break

    for node1, node2 in combinations(netsquid_nodes, 2):
        node1_coordinates = role_node_property_mapping[node1]["coordinates"]
        node2_coordinates = role_node_property_mapping[node2]["coordinates"]
        node1_slug = role_node_property_mapping[node1]["slug"]
        node2_slug = role_node_property_mapping[node2]["slug"]
        distance = link_distance(node1_coordinates, node2_coordinates)

        for channel in channel_properties:
            if(
                channel['slug'] == f"{node1_slug}-{node2_slug}" or
                channel['slug'] == f"{node2_slug}-{node1_slug}"
            ):
                create_qlink(
                    node_one=netsquid_nodes[node1],
                    node_two=netsquid_nodes[node2],
                    distance=distance,
                    link_properties=channel
                )
                break
        create_clink(netsquid_nodes[node1], netsquid_nodes[node2], distance=distance)

    return netsquid_nodes
