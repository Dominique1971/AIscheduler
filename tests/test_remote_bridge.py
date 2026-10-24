"""Bridge contract diagnostics. These do not attest a hosted/cloud deployment."""
import importlib.util
from pathlib import Path
import pytest

spec=importlib.util.spec_from_file_location("remote_bridge",Path(__file__).resolve().parents[1]/"remote"/"bridge.py")
bridge=importlib.util.module_from_spec(spec)
spec.loader.exec_module(bridge)

@pytest.mark.parametrize("value", [{"action":"shell","project":"demo"},{"action":"pause","project":"../../x"},{"action":"allocate","project":"demo","value":True},{"action":"emergency-stop"},{"action":"pause","project":"demo","url":"https://evil.invalid"}])
def test_reject_untyped_control(value):
    with pytest.raises(ValueError):
        bridge.control_route(value)

def test_typed_controls_resolve_only_to_existing_loopback_api_routes():
    assert bridge.control_route({"action":"allocate","project":"demo","value":2}) == ("/api/v1/projects/demo/allocate",{"max_workers":2})
    assert bridge.control_route({"action":"hold","project":"demo","task":"A"}) == ("/api/v1/projects/demo/tasks/A/hold",{})
    assert bridge.control_route({"action":"emergency-stop","confirmed":True}) == ("/api/v1/system/emergency-stop",{"confirmed":True})
