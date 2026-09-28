# Predictive maintenance, connected to the twin

## What this is for

Phase 5 built the skill on its own: given a machine's recent readings, predict how much life it has left, checked honestly against data the model never saw during training. This report answers the next question, the one that actually matters for a real operation: if the hoist winder had a real health signal instead of failing at random, and a model watched it, how much would that actually be worth in tonnes and downtime.

Two ways of running the winder were compared, run many times each under the same underlying conditions. Reactive means the winder is only repaired after it actually breaks down. Predictive means a trained model watches the winder's health and steps in early, before the break happens, with a shorter planned repair instead of an emergency one.

## Why this needed a real health signal first

The twin's original breakdown model assumed the winder could fail at any random moment with equal likelihood, regardless of how long it had been running. That is a fine way to model pure bad luck, but it means there is nothing for a model to actually predict, a machine that fails completely at random gives no early warning to catch.

So the winder was given a genuine wear pattern instead: each time it is repaired, health starts fresh and declines toward failure, with some natural variation in exactly how long that takes. A noisy reading of that health is taken regularly, standing in for a real condition monitoring sensor. This is what makes watching the signal worth anything at all.

## How accurate the model actually is

A model was trained to predict how many hours of life the winder has left, using only its recent noisy readings and how long it has run since its last repair, the same kind of approach used for the jet engines in Phase 5. Overall it predicts remaining life to within about 22 hours on average, well ahead of a naive guess that always assumes the average outcome, which misses by about 82 hours on average.

More importantly, the model is most accurate exactly where a maintenance decision would actually be made, close to failure, typically within about 5 hours when there are 25 hours or less genuinely left. Accuracy loosens further out, when nobody would act on the warning anyway.

## The result, run many times under matched conditions

| | Reactive | Predictive |
|---|---|---|
| Breakdowns per year | 42.4 | 0 |
| Total downtime per year | 431 hours | 350 hours |
| Annual tonnes hoisted | 2,845,079 | 2,872,027 |

Predictive maintenance added about 26,900 tonnes a year and cut total downtime by about 80 hours a year. Both differences held up clearly across many repeated runs, not just one lucky comparison, the odds either difference is due to chance alone are less than one in a million.

## The takeaway

Predicting a breakdown is not a theoretical exercise here, it is directly worth a measurable amount of production and downtime, produced by the twin's own numbers rather than asserted. In this comparison, watching the health signal and acting early prevented essentially every real breakdown, trading it for a shorter, planned repair instead. The same idea that worked on real jet engine data in Phase 5 works just as well on the twin's own equipment, which is the whole point of building a digital twin that combines both halves: a simulation that reflects how the operation actually behaves, and a model that knows when to act on it.
