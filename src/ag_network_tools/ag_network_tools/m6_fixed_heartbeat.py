"""One fixed heartbeat API for a supervised, lifetime-owning creator.

An unresolved registry must remain owned by that creator. This deliberately is
not an autonomous one-shot CLI that could exit and orphan its responsibility.
"""
from .m6_owned_session import OwnedSessionRegistry

class FixedHeartbeatAdapter:
    def __init__(self,output,release_manifest_sha256,*,borrowed_context=None):
        self.registry=OwnedSessionRegistry(output,release_manifest_sha256,borrowed_context=borrowed_context)
    def acquire_fixed_heartbeat(self):return self.registry.acquire_fixed_heartbeat()
    def start(self):return self.registry.start()
    def request_stop(self):return self.registry.request_stop()
    def observe(self):return self.registry.observe()
    def wait(self,timeout=10):return self.registry.wait(timeout)
    def close(self,*,primary_error=None):return self.registry.close(primary_error=primary_error)
    def get_cleanup_report(self):return self.registry.get_cleanup_report()
