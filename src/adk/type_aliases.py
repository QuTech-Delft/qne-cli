from typing import Any, Callable, Dict, List, Union, Tuple, Optional
from typing_extensions import TypedDict

DefaultPayloadType = Union[int, str]

valuesType = Dict[str, Any]
listValuesType = List[valuesType]
app_configNetworkType = Dict[str, List[str]]
app_configApplicationType = List[Dict[str, Any]]
app_ownerType = Optional[Dict[str, DefaultPayloadType]]
assetNetworkType = Dict[str, Any]
assetApplicationType = List[Dict[str, Any]]
assetParameterType = Dict[str, Union[str, listValuesType]]
listAssetParameterType = List[assetParameterType]
instructionsType = List[Dict[str, Any]]
round_resultType = Dict[str, Any]
cumulative_resultType = Dict[str, Any]
final_resultType = Dict[str, Any]
coordinatesType = Dict[str, float]
result_componentType = Optional[List[Dict[str, Any]]]
round_result_viewType = List[result_componentType]
cumulative_result_viewType = List[result_componentType]
final_result_viewType = List[result_componentType]
parametersType = List[str]

TemplateType = Dict[str, Union[DefaultPayloadType, listValuesType]]
NodeType = Dict[str, Union[DefaultPayloadType, coordinatesType, parametersType]]
ChannelType = Dict[str, Union[DefaultPayloadType, parametersType]]
NetworkType = Dict[str, Union[DefaultPayloadType, List[ChannelType], List[NodeType]]]
NetworkListType = Dict[str, Union[DefaultPayloadType]]
TemplatesType = Dict[str, List[Dict[str, Any]]]
AssetChannelListType = List[Dict[str, Any]]
AssetNodeListType = List[Dict[str, Any]]

ApplicationType = Dict[str, Union[DefaultPayloadType, bool, app_ownerType]]
AppVersionType = Dict[str, Union[DefaultPayloadType, bool]]
AppSourceType = Dict[str, Union[DefaultPayloadType, bool]]
AppConfigType = Dict[str, Union[DefaultPayloadType, bool, app_configNetworkType, app_configApplicationType]]
AppResultType = Dict[str, Union[DefaultPayloadType, bool, round_result_viewType, cumulative_result_viewType,
                                final_result_viewType]]
AppSourceFilesType = Dict[str, Tuple[Any, Any]]

TokenType = Dict[str, str]
MetaType = Dict[str, Any]
UserType = Dict[str, Union[DefaultPayloadType]]
RoundSetType = Dict[str, Union[DefaultPayloadType, float]]
AssetType = Dict[str, Union[DefaultPayloadType, assetNetworkType, assetApplicationType]]
ExperimentType = Dict[str, Union[DefaultPayloadType, bool]]
ExperimentDataType = Dict[str, Dict[str, Any]]
ApplicationDataType = Dict[str, Dict[str, Any]]

ResultType = Dict[str, Union[DefaultPayloadType, round_resultType, cumulative_resultType, instructionsType]]
FinalResultType = Dict[str, Union[DefaultPayloadType, Dict[str, Any]]]
RoundResultType = Dict[str, Any]
CumulativeResultType = Dict[str, Any]
InstructionType = Dict[str, Any]
LogEntryType = Dict[str, Any]
BackendType = Dict[str, DefaultPayloadType]
BackendTypeType = Dict[str, Union[DefaultPayloadType, bool]]

ActionsType = Union[str, List[str]]
ParametersType = Union[str, Dict[str, str], Any]

NetworkData = Dict[str, Dict[str, Dict[str, Any]]]
ChannelData = Dict[str, List[Dict[str, Any]]]
NodeData = Dict[str, List[Dict[str, Any]]]
TemplateData = Dict[str, List[Dict[str, Any]]]
GenericNetworkData = Dict[str, Any]

AuthType = Dict[str, Dict[str, str]]

LoginFunctionType = Callable[[str, str, str, bool], str]
LogoutFunctionType = Callable[[str], None]
FallbackFunctionType = Callable[[str], str]
TokenFetchFunctionType = Union[LoginFunctionType, FallbackFunctionType]

ErrorDictType = Dict[str, List[str]]
LinkType = Dict[str, Union[str, float]]
QuantumStateType = List[List[Dict[str, float]]]
NetworkConfigType = Dict[str, Union[List[LinkType], List[NodeType]]]


class DijkstraNode(TypedDict):
    effective_fidelity: float
    channels: List[str]
    final: bool
