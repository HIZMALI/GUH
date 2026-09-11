"""Per-panel monotonic deadlines with one focused panel and a shared publication budget."""
from dataclasses import dataclass

def telemetry_message_id(demo_run_id, step):
    """A restart retry for the same run/step keeps its durable idempotency key."""
    return f'{demo_run_id}-s{step}'

def publication_interval(panel_count, requested_interval, max_fps):
    if requested_interval <= 0 or max_fps <= 0 or panel_count < 0:
        raise ValueError('Interval and max_fps must be positive; panel_count cannot be negative')
    return max(requested_interval, panel_count / max_fps)

@dataclass
class ScheduledPanel:
    panel: dict
    step: int
    next_due: float
    interval: float
    focused: bool
    emitted: int = 0
    disabled: bool = False
    arc_event_timestamp: str | None = None

class PanelScheduler:
    def __init__(self, interval=3, max_fps=50, focus_interval=1.5):
        publication_interval(0, interval, max_fps)
        if focus_interval <= 0 or max_fps <= 1 / focus_interval:
            raise ValueError('Focus cadence must leave positive capacity for the background fleet')
        self.interval, self.max_fps, self.focus_interval = interval, max_fps, focus_interval
        self.entries = {}
        self.next_publish = 0.
        self.background_budget = max_fps
        self.background_interval = interval
        self.focus_panel_id = None

    def sync(self, panels, now):
        ordered = sorted(panels, key=lambda panel: int(panel['id'].split('-')[1]))
        self.focus_panel_id = next((panel['id'] for panel in ordered if panel.get('focused_demo')), None)
        background = [panel for panel in ordered if panel['id'] != self.focus_panel_id]
        self.background_budget = self.max_fps - (1 / self.focus_interval if self.focus_panel_id else 0)
        self.background_interval = publication_interval(len(background), self.interval, self.background_budget)
        ranks = {panel['id']: index for index, panel in enumerate(background)}
        active = set()
        for panel in ordered:
            panel_id, revision = panel['id'], panel['revision']
            active.add(panel_id)
            focused = panel_id == self.focus_panel_id
            cadence = self.focus_interval if focused else self.background_interval
            entry = self.entries.get(panel_id)
            if entry is None or entry.panel['revision'] != revision:
                last_step = panel.get('last_step')
                step = last_step + 1 if last_step is not None else 0
                due = now if focused else now + ranks[panel_id] / self.background_budget
                entry = ScheduledPanel(panel, step, due, cadence, focused,
                                       arc_event_timestamp=panel.get('arc_event_timestamp'))
                self.entries[panel_id] = entry
            else:
                if focused != entry.focused:
                    entry.next_due = now if focused else now + ranks[panel_id] / self.background_budget
                entry.panel, entry.interval, entry.focused = panel, cadence, focused
        for panel_id in list(self.entries):
            if panel_id not in active:
                del self.entries[panel_id]

    def due(self, now):
        if now + 1e-9 < self.next_publish:
            return None
        focus = self.entries.get(self.focus_panel_id)
        if focus and not focus.disabled and focus.next_due <= now + 1e-9:
            return focus
        candidates = [entry for entry in self.entries.values() if not entry.disabled and not entry.focused
                      and entry.next_due <= now + 1e-9]
        return min(candidates, key=lambda entry: entry.next_due) if candidates else None

    def sent(self, entry, now):
        entry.step += 1
        entry.emitted += 1
        entry.next_due = now + entry.interval
        self.next_publish = now + 1 / self.max_fps

    def retry(self, entry, now):
        entry.next_due = now + min(1, entry.interval)
        self.next_publish = now + 1 / self.max_fps

    def deadline(self, now):
        pending = [entry.next_due for entry in self.entries.values() if not entry.disabled]
        return max(self.next_publish, min(pending)) if pending else now + 1

    def stats(self):
        return {'panels': len(self.entries), 'focus_panel_id': self.focus_panel_id,
                'focus_interval_seconds': self.focus_interval, 'max_fps': self.max_fps,
                'background_fps_budget': round(self.background_budget, 4),
                'background_interval_seconds': round(self.background_interval, 4)}
