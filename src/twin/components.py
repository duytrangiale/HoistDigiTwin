"""Physical entities of the hoist circuit: sources, bins, flasks, skips, and
the winder. simulation.py wires these together from config.yaml and runs
the environment. See reports/simulation_validation.md for the modelling
decisions behind this file.
"""

from __future__ import annotations

import random
from dataclasses import dataclass, field

import simpy


@dataclass
class Source:
    """One of the two ore feeds into the bins conveyor. Only one source is
    active at a time, controlled by source_switch_process."""

    name: str
    feed_rate_tph: float
    active: bool = False


class Bin(simpy.Container):
    """One of the three ore bins, a capacity limited store of tonnes."""

    def __init__(self, env: simpy.Environment, name: str, capacity_tonnes: float):
        super().__init__(env, capacity=capacity_tonnes, init=0)
        self.name = name


class Flask(simpy.Container):
    """A small buffer that stages ore for one skip. Flask west always feeds
    skip west, flask east always feeds skip east."""

    def __init__(self, env: simpy.Environment, name: str, capacity_tonnes: float):
        super().__init__(env, capacity=capacity_tonnes, init=0)
        self.name = name


class Winder:
    """The single shared hoist resource. A skip's hoist, dump, and return
    legs, scheduled maintenance, and random breakdowns all compete for the
    same one slot, so unavailability needs no separate interruption logic,
    it is just another request for the same resource."""

    def __init__(self, env: simpy.Environment, capacity: int = 1):
        self.resource = simpy.Resource(env, capacity=capacity)
        self.busy_hoisting_seconds = 0.0
        self.down_seconds = 0.0


@dataclass
class CycleRecord:
    """One completed skip cycle: when it dumped, which skip, how much ore,
    and how long the full cycle took."""

    dump_time_s: float
    skip_name: str
    tonnes: float
    cycle_time_s: float


class Skip:
    """One skip. Loads from its own flask (no winder needed), then holds
    the winder for the hoist, dump, and return legs of its cycle, so the
    other skip is free to load in the meantime."""

    def __init__(
        self,
        env: simpy.Environment,
        name: str,
        flask: Flask,
        winder: Winder,
        payload_tonnes: float,
        load_time_mean_s: float,
        hoist_time_mean_s: float,
        dump_time_mean_s: float,
        return_time_mean_s: float,
        cycle_time_cv: float,
        rng: random.Random,
        cycle_log: list[CycleRecord],
    ):
        self.env = env
        self.name = name
        self.flask = flask
        self.winder = winder
        self.payload_tonnes = payload_tonnes
        self.load_time_mean_s = load_time_mean_s
        self.hoist_time_mean_s = hoist_time_mean_s
        self.dump_time_mean_s = dump_time_mean_s
        self.return_time_mean_s = return_time_mean_s
        self.cycle_time_cv = cycle_time_cv
        self.rng = rng
        self.cycle_log = cycle_log

    def _duration(self, mean_s: float) -> float:
        std = mean_s * self.cycle_time_cv
        return max(0.0, self.rng.gauss(mean_s, std))

    def run(self):
        while True:
            cycle_start = self.env.now

            yield self.flask.get(self.payload_tonnes)
            yield self.env.timeout(self._duration(self.load_time_mean_s))

            with self.winder.resource.request() as req:
                yield req
                hoist_start = self.env.now
                yield self.env.timeout(self._duration(self.hoist_time_mean_s))
                yield self.env.timeout(self._duration(self.dump_time_mean_s))
                yield self.env.timeout(self._duration(self.return_time_mean_s))
                self.winder.busy_hoisting_seconds += self.env.now - hoist_start

            self.cycle_log.append(
                CycleRecord(
                    dump_time_s=self.env.now,
                    skip_name=self.name,
                    tonnes=self.payload_tonnes,
                    cycle_time_s=self.env.now - cycle_start,
                )
            )


def source_switch_process(env: simpy.Environment, sources: list[Source], switch_interval_hours: float):
    """Alternates which source is active on a fixed schedule. The caller
    must set exactly one source active before starting this process."""
    while True:
        yield env.timeout(switch_interval_hours * 3600)
        active_idx = next(i for i, s in enumerate(sources) if s.active)
        sources[active_idx].active = False
        sources[(active_idx + 1) % len(sources)].active = True


def feed_bins_process(
    env: simpy.Environment,
    sources: list[Source],
    bins: list[Bin],
    feed_step_minutes: float = 1.0,
):
    """Moves ore from whichever source is active into the bins, in small
    timed steps rather than continuous flow. Each step's tonnes are spread
    across bins in order of most free capacity first, so ore is only ever
    lost when every bin is simultaneously full, not as an artifact of the
    step size."""
    step_s = feed_step_minutes * 60
    while True:
        active = next((s for s in sources if s.active), None)
        if active is not None:
            remaining = active.feed_rate_tph * (feed_step_minutes / 60)
            for target in sorted(bins, key=lambda b: b.capacity - b.level, reverse=True):
                if remaining <= 0:
                    break
                put_amount = min(remaining, target.capacity - target.level)
                if put_amount > 0:
                    yield target.put(put_amount)
                    remaining -= put_amount
        yield env.timeout(step_s)


def feed_flasks_process(
    env: simpy.Environment,
    bins: list[Bin],
    flask: Flask,
    feed_step_minutes: float = 1.0,
):
    """Tops up one flask from the bins, drawing from whichever bin holds the
    most ore first and moving on to the next if one bin alone cannot cover
    the flask's free capacity. The conveyor between bins and flasks is
    assumed fast enough not to be a bottleneck itself, so the only limits
    are total bin stock and flask capacity."""
    step_s = feed_step_minutes * 60
    while True:
        remaining = flask.capacity - flask.level
        if remaining > 0:
            for source_bin in sorted(bins, key=lambda b: b.level, reverse=True):
                if remaining <= 0:
                    break
                move_amount = min(remaining, source_bin.level)
                if move_amount > 0:
                    yield source_bin.get(move_amount)
                    yield flask.put(move_amount)
                    remaining -= move_amount
        yield env.timeout(step_s)


def scheduled_maintenance_process(
    env: simpy.Environment,
    winder: Winder,
    hours_per_month: float,
    downtime_log: list[tuple[float, float, str]],
    monthly_overrides: dict[int, float] | None = None,
):
    """Takes the winder out of service for one maintenance block every 30
    simulated days, by requesting the same resource the skips use.

    monthly_overrides maps a zero indexed month number to its own total
    downtime hours, replacing hours_per_month for that month only. This is
    how a known event, such as a Christmas and New Year shutdown or a
    specific extended repair, gets fed into the model, the same way real
    historical downtime records would be if they were available. Month
    indices line up with the month bucketing used when reporting monthly
    tonnes, both count 30 day blocks from the start of the run.
    """
    seconds_per_month = 30 * 24 * 3600
    overrides = monthly_overrides or {}
    month = 0
    while True:
        duration_s = min(overrides.get(month, hours_per_month) * 3600, seconds_per_month)
        with winder.resource.request() as req:
            yield req
            start = env.now
            yield env.timeout(duration_s)
            winder.down_seconds += env.now - start
            downtime_log.append((start, duration_s, "scheduled"))
        remaining_in_month = seconds_per_month - duration_s
        if remaining_in_month > 0:
            yield env.timeout(remaining_in_month)
        month += 1


def breakdown_process(
    env: simpy.Environment,
    winder: Winder,
    mtbf_hours: float,
    mttr_hours: float,
    rng: random.Random,
    downtime_log: list[tuple[float, float, str]],
):
    """Random winder breakdowns, exponentially distributed time between
    failures and repair duration, competing for the winder resource the
    same way a scheduled maintenance block or a skip's hoist step does."""
    while True:
        yield env.timeout(rng.expovariate(1 / (mtbf_hours * 3600)))
        with winder.resource.request() as req:
            yield req
            start = env.now
            repair_s = rng.expovariate(1 / (mttr_hours * 3600))
            yield env.timeout(repair_s)
            winder.down_seconds += env.now - start
            downtime_log.append((start, repair_s, "breakdown"))


def record_bin_levels_process(
    env: simpy.Environment,
    bins: list[Bin],
    interval_minutes: float,
    level_log: list[tuple[float, str, float]],
):
    """Samples every bin's level at a fixed interval for the bin level over
    time output."""
    interval_s = interval_minutes * 60
    while True:
        for b in bins:
            level_log.append((env.now, b.name, b.level))
        yield env.timeout(interval_s)
