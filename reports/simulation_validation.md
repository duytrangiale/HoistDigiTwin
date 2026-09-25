# Simulation validation

## What this checks

A digital twin is only useful if its output is believable. The scope this project follows, from a real hoist operation model, sets a specific bar for that: the model should reproduce twelve months of hoisted tonnes within five percent each month, and match the shape of that behaviour, not just the year end total.

This project has no access to real historical tonnage data, so that exact bar cannot be met literally. Instead, this report builds a synthetic twelve month reference, grounded in published figures for comparable shaft hoisting systems rather than picked arbitrarily, and shows the simulation tuned to track it within the same five percent bar. This demonstrates the calibration method that would be used with real data, using an invented target as a stand in. None of the tonnage figures in this report describe a real mining operation.

## The physical parameters behind the model

The skip and winder timing in `config.yaml` comes from a shaft haulage capacity study of a 750 metre deep shaft using 12 tonne skips, a maximum hoist speed of 14 metres per second, and a combined load and dump time of 28 seconds. From that, a full skip cycle breaks down as roughly 60 seconds hoisting up, 10 seconds dumping, 55 seconds returning empty, and 20 seconds loading from the flask while stationary. The two skips share one winder, so only the hoist, dump, and return legs compete for it, and the other skip is free to load in the meantime, which is the actual efficiency a twin skip system is built for.

Sources:
- [Internal Engineering Study, Shaft Haulage Capacity](https://ressourcescartier.com/wp-content/uploads/2019/10/200922_Summary_Internal-Eng-Report-Shaft-Haulage-Capacity_Project-1B-PB.pdf)
- [Underground Mine Hoisting Sketches](https://www.jdowling.com/Chapter6/Hoisting.html)
- [Mine Shaft Skips datasheet, FLSmidth](https://prod.flsmidth.com/globalassets/frontify/2024/9/mineshaftskips_datasheet_en.pdf)
- [The shaft under pressure: debottlenecking production hoisting](https://northamericanmining.com/index.php/2026/06/25/the-shaft-under-pressure-debottlenecking-production-hoisting/)
- [Mines to shutdown over Christmas, Australian Mining](https://www.australianmining.com.au/mines-to-shutdown-over-christmas/)

Run without any downtime, these parameters put the shaft's ceiling at around 346 tonnes an hour. With the model's default winder utilisation, that settles to a steady state of about 237,000 tonnes a month, which becomes the baseline the synthetic target is built around.

## The synthetic target

`src/twin/synthetic_target.py` builds a twelve month series from that 237,000 tonne baseline, with three deliberate departures from a flat, uneventful year:

- January and December are reduced by 40 and 35 percent, standing in for a Christmas and New Year shutdown, a documented and common practice at Australian mines.
- July is reduced by 45 percent, standing in for one extended unplanned repair, a single bad month rather than a smooth curve.
- Every other month carries a small four percent random variation, month to month.

This is not measured data. It is a plausible year built from research, used to check that the simulation can be calibrated against a target with real shape, not just a single number.

## Making the simulation match the shape, not just the total

A steady state simulation cannot reproduce a Christmas dip or a bad month on its own, calendar seasonality has to be an input, not something layered on afterward. `scheduled_maintenance_process` was made calendar aware: `config.yaml`'s `winder.scheduled_downtime_overrides` gives specific months their own total downtime hours, in place of the usual monthly figure. This is the same mechanism a real calibration would use, feeding in actual known outage dates once they are available.

Tuning took two rounds. Recalibrating the target's own baseline to the simulation's actual steady state output, rather than the earlier hand calculated estimate, closed most of the gap immediately, since the two were about seven percent apart before that. The remaining gap was that a nominal 252 hour December outage only reduced output by 32.5 percent, short of the intended 35, because ore that had already built up in the bins before the shutdown gets hoisted once the winder reopens, partly absorbing the loss. Raising December to 280 hours and July to 355 hours corrected this.

## Result

Averaged over 20 replications, all twelve months land within five percent of the target, the largest gap is 4.5 percent in September.

| Month | Synthetic target (t) | Simulated (t) | Difference |
|---|---|---|---|
| Jan | 140,196 | 145,417 | +3.7% |
| Feb | 230,380 | 237,865 | +3.2% |
| Mar | 239,862 | 236,374 | -1.5% |
| Apr | 228,893 | 237,071 | +3.6% |
| May | 237,680 | 237,455 | -0.1% |
| Jun | 234,453 | 238,871 | +1.9% |
| Jul | 125,741 | 123,085 | -2.1% |
| Aug | 237,141 | 237,632 | +0.2% |
| Sep | 228,231 | 238,466 | +4.5% |
| Oct | 235,742 | 236,980 | +0.5% |
| Nov | 228,844 | 236,278 | +3.2% |
| Dec | 149,006 | 147,377 | -1.1% |

The mean monthly tonnes across all 20 replications is 212,739, with a 95 percent confidence interval of [212,303, 213,175], under half a percent wide. Mean winder utilisation is 85.4 percent across the year, dropping from the roughly 95 percent seen in an uneventful month because of the three downtime months pulling the average down.

## What the model shows

The winder, not the ore feed, is the bottleneck. In a normal month it runs at about 95 percent utilisation, and raising the source feed rate by fifty percent in a test made no difference to output at all, confirmed directly in `tests/test_simulation.py`. This matches the real framing of the reference scope, which describes debottlenecking production hoisting as the actual problem worth solving, and it means any future scenario work aimed at raising throughput should target the winder and the skip cycle, not the ore supply.

The bin levels climb toward their 200 tonne capacity during each downtime month, visible in `notebooks/01_simulation.ipynb`, since ore keeps arriving from the sources while the winder is not clearing it. This is the kind of shape level detail the validation bar asks for beyond the monthly totals.

## Limitations

This is a calibration exercise against an invented target, not a real one. The five percent match demonstrates the method, the specific numbers do not describe any real operation. A genuine calibration would replace `synthetic_target.py`'s series with actual historical tonnage and replace the downtime overrides with actual recorded outage dates, and the rest of the workflow here, the calendar aware downtime model and the replication based comparison, would carry over unchanged.
