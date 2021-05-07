from io import BytesIO
from random import randint
from unittest.mock import patch, MagicMock
from uuid import uuid4

import grpc
import pytest

from pyzeebe.errors import InvalidJSONError, ProcessDefinitionNotFoundError, ProcessInstanceNotFoundError, \
    ProcessDefinitionHasNoStartEventError, \
    ProcessInvalidError, ZeebeInternalError
from tests.unit.utils.grpc_utils import GRPCStatusCode
from tests.unit.utils.random_utils import RANDOM_RANGE


def test_create_process_instance(grpc_servicer, zeebe_adapter):
    bpmn_process_id = str(uuid4())
    version = randint(0, 10)
    grpc_servicer.mock_deploy_process(bpmn_process_id, version, [])
    response = zeebe_adapter.create_process_instance(
        bpmn_process_id=bpmn_process_id, variables={}, version=version)
    assert isinstance(response, int)


def test_create_process_instance_raises_grpc_error_correctly(zeebe_adapter):
    error = grpc.RpcError()
    error._state = GRPCStatusCode(grpc.StatusCode.INTERNAL)

    zeebe_adapter._gateway_stub.CreateProcessInstance = MagicMock(
        side_effect=error)

    with pytest.raises(ZeebeInternalError):
        zeebe_adapter.create_process_instance(bpmn_process_id=str(uuid4()), variables={},
                                              version=randint(0, 10))


def test_create_process_instance_with_result_return_types(grpc_servicer, zeebe_adapter):
    bpmn_process_id = str(uuid4())
    version = randint(0, 10)
    grpc_servicer.mock_deploy_process(bpmn_process_id, version, [])
    process_instance_key, response = zeebe_adapter.create_process_instance_with_result(
        bpmn_process_id=bpmn_process_id,
        variables={},
        version=version,
        timeout=0,
        variables_to_fetch=[]
    )
    assert isinstance(process_instance_key, int)
    assert isinstance(response, dict)


def test_create_process_instance_with_result_raises_grpc_error_correctly(zeebe_adapter):
    error = grpc.RpcError()
    error._state = GRPCStatusCode(grpc.StatusCode.INTERNAL)

    zeebe_adapter._gateway_stub.CreateProcessInstanceWithResult = MagicMock(
        side_effect=error)

    with pytest.raises(ZeebeInternalError):
        zeebe_adapter.create_process_instance_with_result(bpmn_process_id=str(uuid4()), variables={},
                                                          version=randint(0, 10), timeout=0,
                                                          variables_to_fetch=[])


def test_cancel_process(grpc_servicer, zeebe_adapter):
    bpmn_process_id = str(uuid4())
    version = randint(0, 10)
    grpc_servicer.mock_deploy_process(bpmn_process_id, version, [])
    process_instance_key = zeebe_adapter.create_process_instance(bpmn_process_id=bpmn_process_id,
                                                                 variables={}, version=version)
    zeebe_adapter.cancel_process_instance(
        process_instance_key=process_instance_key)
    assert process_instance_key not in grpc_servicer.active_processes.keys()


def test_cancel_process_instance_already_cancelled(zeebe_adapter):
    error = grpc.RpcError()
    error._state = GRPCStatusCode(grpc.StatusCode.NOT_FOUND)

    zeebe_adapter._gateway_stub.CancelProcessInstance = MagicMock(
        side_effect=error)

    with pytest.raises(ProcessInstanceNotFoundError):
        zeebe_adapter.cancel_process_instance(
            process_instance_key=randint(0, RANDOM_RANGE))


def test_cancel_process_instance_common_errors_called(zeebe_adapter):
    zeebe_adapter._common_zeebe_grpc_errors = MagicMock()
    error = grpc.RpcError()
    error._state = GRPCStatusCode(grpc.StatusCode.INTERNAL)

    zeebe_adapter._gateway_stub.CancelProcessInstance = MagicMock(
        side_effect=error)

    zeebe_adapter.cancel_process_instance(
        process_instance_key=randint(0, RANDOM_RANGE))

    zeebe_adapter._common_zeebe_grpc_errors.assert_called()


def test_deploy_process_process_invalid(zeebe_adapter):
    with patch("builtins.open") as mock_open:
        mock_open.return_value = BytesIO()

        error = grpc.RpcError()
        error._state = GRPCStatusCode(grpc.StatusCode.INVALID_ARGUMENT)

        zeebe_adapter._gateway_stub.DeployProcess = MagicMock(
            side_effect=error)

        with pytest.raises(ProcessInvalidError):
            zeebe_adapter.deploy_process()


def test_deploy_process_common_errors_called(zeebe_adapter):
    with patch("builtins.open") as mock_open:
        mock_open.return_value = BytesIO()

        zeebe_adapter._common_zeebe_grpc_errors = MagicMock()
        error = grpc.RpcError()
        error._state = GRPCStatusCode(grpc.StatusCode.INTERNAL)

        zeebe_adapter._gateway_stub.DeployProcess = MagicMock(
            side_effect=error)

        zeebe_adapter.deploy_process()

        zeebe_adapter._common_zeebe_grpc_errors.assert_called()


def test_get_process_request_object(zeebe_adapter):
    with patch("builtins.open") as mock_open:
        mock_open.return_value = BytesIO()
        file_path = str(uuid4())
        zeebe_adapter._get_process_request_object(file_path)
        mock_open.assert_called_with(file_path, "rb")


def test_create_process_errors_not_found(zeebe_adapter):
    error = grpc.RpcError()
    error._state = GRPCStatusCode(grpc.StatusCode.NOT_FOUND)
    with pytest.raises(ProcessDefinitionNotFoundError):
        zeebe_adapter._create_process_errors(
            error, str(uuid4()), randint(0, 10, ), {})


def test_create_process_errors_invalid_json(zeebe_adapter):
    error = grpc.RpcError()
    error._state = GRPCStatusCode(grpc.StatusCode.INVALID_ARGUMENT)
    with pytest.raises(InvalidJSONError):
        zeebe_adapter._create_process_errors(
            error, str(uuid4()), randint(0, 10, ), {})


def test_create_process_errors_process_has_no_start_event(zeebe_adapter):
    error = grpc.RpcError()
    error._state = GRPCStatusCode(grpc.StatusCode.FAILED_PRECONDITION)
    with pytest.raises(ProcessDefinitionHasNoStartEventError):
        zeebe_adapter._create_process_errors(
            error, str(uuid4()), randint(0, 10, ), {})


def test_create_process_errors_common_errors_called(zeebe_adapter):
    zeebe_adapter._common_zeebe_grpc_errors = MagicMock()
    error = grpc.RpcError()
    error._state = GRPCStatusCode("test")
    zeebe_adapter._create_process_errors(
        error, str(uuid4()), randint(0, 10, ), {})

    zeebe_adapter._common_zeebe_grpc_errors.assert_called()
