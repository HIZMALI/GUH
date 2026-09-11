"""These adapters only compose local records; none can contact an external provider."""
from dataclasses import dataclass

@dataclass(frozen=True)
class MockNotification:
    channel: str
    recipient: str
    status: str
    message: str

def compose_notifications(message: str) -> list[MockNotification]:
    return [MockNotification('sms_mock', 'SIMULATED_OPERATIONS_TEAM', 'simulated', message),
            MockNotification('whatsapp_mock', 'SIMULATED_MAINTENANCE_TEAM', 'simulated', message)]
