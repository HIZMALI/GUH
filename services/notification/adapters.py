"""These adapters only compose local records; none can contact an external provider."""
from dataclasses import dataclass

@dataclass(frozen=True)
class MockNotification:
    channel: str
    recipient: str
    status: str
    message: str

def compose_notifications(message: str, channels=None) -> list[MockNotification]:
    from services.anomaly_engine.actions import MOCK_CHANNELS
    recipients = {'sms_mock': 'SIMULATED_OPERATIONS_TEAM', 'whatsapp_mock': 'SIMULATED_MAINTENANCE_TEAM'}
    selected = MOCK_CHANNELS if channels is None else channels
    if any(channel not in recipients for channel in selected):
        raise ValueError('Only local simulated notification channels are supported')
    return [MockNotification(channel, recipients[channel], 'simulated', message) for channel in selected]
