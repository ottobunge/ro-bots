"""A reviewed field destination continues while cognition is busy."""

from dataclasses import dataclass

from robots.app.field_travel import FieldTravel
from robots.domain.actions import MoveTo
from robots.domain.farm import FarmPlan
from robots.domain.model import BotState

FIELD_TRAVEL_SECONDS = 300.0


@dataclass
class FieldTravelIntent:
    plan: FarmPlan
    planner: FieldTravel
    epoch: int | None
    started: float

    def valid(self, state: BotState, now: float) -> bool:
        return state.native_epoch == self.epoch and self.started <= now < self.started + min(
            self.plan.duration_s, FIELD_TRAVEL_SECONDS
        )

    def action(self, state: BotState, now: float) -> MoveTo | None:
        if not self.valid(state, now) or state.map_name == self.plan.map_name:
            return None
        route = self.planner.route(state.map_name, state.x, state.y, self.plan.map_name)
        if not route or route[0][0] != state.map_name:
            return None
        return MoveTo(route[0][1], route[0][2])
