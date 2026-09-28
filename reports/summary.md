# HoistDigiTwin: a digital twin for predictive maintenance

**A portfolio project applying surrogate modelling and predictive
maintenance to a simulated mine hoist circuit, end to end: simulation,
fast surrogate, optimisation, remaining life prediction, and a live
public dashboard.**

Live demo: hoistdigitwin-frontend.onrender.com
Repository: github.com/duytrangiale/HoistDigiTwin

## The problem

Mining operations need two related things from a digital twin: a model
accurate enough to trust for planning decisions, and fast enough to
actually search or run live. Those two goals usually pull in opposite
directions, a detailed physical simulation is slow, a model fast enough
to search is usually a rough approximation. This project builds both
halves properly and connects them, then goes one step further: using the
same twin to show, with real numbers, what predictive maintenance is
actually worth.

## What was built

- **A discrete event simulation** of a hoist circuit (SimPy): two ore
  sources, three bins, two skips sharing one winder, calibrated against
  a research grounded reference year to within 5% every month.
- **A machine learning surrogate** (XGBoost and a Gaussian process)
  trained to reproduce that simulation in under a millisecond instead of
  about 10 seconds, accurate to within 2% on settings it never trained
  on. This is the same problem as surrogate modelling a physics
  simulation, applied here to an operational system instead of a
  granular material.
- **An optimisation search** over that surrogate (random search and
  Bayesian optimisation), checked against the real simulation at the
  answer it found rather than trusted blindly, worth about 80% more
  monthly output at the settings it identified.
- **A remaining useful life model**, first proven on NASA's public
  C-MAPSS turbofan engine dataset (a linear baseline, XGBoost, and an
  LSTM), then the same technique applied to the twin's own simulated
  winder, complete with a genuine wear pattern instead of a memoryless
  random failure rate, so predicting a breakdown is actually meaningful.
- **A live comparison of maintenance policies**, run entirely inside the
  twin: fixing the winder only after it breaks, against watching the
  health signal and acting early. Run 20 times over, same underlying
  conditions both times, to separate a real effect from noise.
- **A public dashboard** (FastAPI, React), deployed free, with an
  animated schematic that reacts to the same models live: move a
  setting, watch the predicted output and the diagram respond together.

## Results, all checked against something real

| | |
|---|---|
| Simulation validation | All 12 months within 5% of a research grounded reference year |
| Surrogate speed | About 10 seconds to under a millisecond per prediction |
| Surrogate accuracy | About 2% error on unseen settings |
| Optimisation gain | About 80% more monthly tonnes, confirmed against the real simulation |
| RUL accuracy, NASA C-MAPSS | RMSE of about 15 cycles, best of three models tried |
| Predictive vs reactive maintenance | About 27,000 more tonnes and 80 fewer downtime hours a year, p < 0.001 |

## Why this matters for the role

The core skill this project demonstrates, building a fast, trustworthy
surrogate for something too slow to search or run live, is the same
methodology behind surrogate modelling of physical systems generally,
applied here to an operational process instead of a material. The
predictive maintenance half shows the other side of the same coin: a
model is only worth building if it changes a decision, and this project
measures that change directly rather than asserting it.

## Stack

SimPy, scikit-learn, XGBoost, PyTorch, MLflow, FastAPI, React, pytest.
