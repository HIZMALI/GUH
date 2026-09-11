"""Shared, deterministic bank addressing for the local read-only SCADA demo."""
from dataclasses import dataclass
from .registers import panel_sort_key


def validate_bank_configuration(bank_size=247, port_base=1502, bank_count=3):
    if any(isinstance(v, bool) or not isinstance(v, int) for v in (bank_size, port_base, bank_count)):
        raise ValueError('Bank configuration must contain integers')
    if not 1 <= bank_size <= 247 or not 1 <= bank_count <= 128:
        raise ValueError('Bank size must be 1..247 and bank count 1..128')
    if not 1 <= port_base <= 65535 or port_base + bank_count - 1 > 65535:
        raise ValueError('Bank port range must fit TCP ports 1..65535')


@dataclass(frozen=True)
class BankAddress:
    bank: int
    port: int
    unit_id: int


def panel_bank_mapping(panels, bank_size=247, port_base=1502):
    """Numeric fleet order, identical to v1 within bank 1; never unit 248+."""
    validate_bank_configuration(bank_size, port_base, 1)
    identifiers = [str(p['id']) for p in sorted(panels, key=panel_sort_key)]
    if len(set(identifiers)) != len(identifiers):
        raise ValueError('Duplicate panel IDs in fleet')
    count = max(1, (len(identifiers) + bank_size - 1) // bank_size)
    validate_bank_configuration(bank_size, port_base, count)
    return {identifier: BankAddress(index // bank_size + 1,
                                   port_base + index // bank_size,
                                   index % bank_size + 1)
            for index, identifier in enumerate(identifiers)}


class BankFleetCache:
    """One authenticated fleet poll fan-outs to independent bank snapshots."""
    def __init__(self, bank_size=247, port_base=1502, bank_count=3, stale_seconds=15):
        from .registers import RegisterCache
        validate_bank_configuration(bank_size, port_base, bank_count)
        self.bank_size, self.port_base = bank_size, port_base
        self.caches = [RegisterCache(stale_seconds) for _ in range(bank_count)]

    def update(self, panels):
        addresses = panel_bank_mapping(panels, self.bank_size, self.port_base)
        if any(a.bank > len(self.caches) for a in addresses.values()):
            raise ValueError('Configured SCADA banks cannot address the complete fleet')
        groups = [[] for _ in self.caches]
        for panel in panels:
            groups[addresses[panel['id']].bank - 1].append(panel)
        for cache, group in zip(self.caches, groups):
            cache.update(group)

    def mark_failed(self, error):
        for cache in self.caches:
            cache.mark_failed(error)
