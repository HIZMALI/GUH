"""Transport to a READ-ONLY approved TCP-to-RTU gateway, not native vendor TCP."""
from services.scada_bridge.master import read_registers


class ReadOnlyTCPGateway:
    def __init__(self, host: str, port: int = 502, function: int = 3):
        if function not in (3, 4):
            raise ValueError("Only FC03/FC04 permitted")
        self.host, self.port, self.function = host, port, function

    def read_registers(self, unit_id, address, count, *, timeout=2.0):
        return read_registers(self.host, self.port, unit_id, address, count, timeout=timeout, function=self.function)
