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

def test_sites_service_credential_is_sent_only_when_explicit(monkeypatch):
    observed=[]
    class Response:
        status=200
        def __enter__(self): return self
        def __exit__(self,*_): pass
        def read(self,_): return b'{}'
    class Opener:
        def open(self,request,timeout):
            observed.append((request.full_url,dict(request.header_items())))
            return Response()
    monkeypatch.setattr(bridge.urllib.request,"build_opener",lambda *_: Opener())
    bridge.request("http://127.0.0.1:8765/api/v1/snapshot","local")
    bridge.request("https://scheduler.test/agent/poll","agent",{},site_access="site-secret")
    assert "Oai-sites-authorization" not in observed[0][1]
    assert observed[1][1]["Oai-sites-authorization"] == "Bearer site-secret"
