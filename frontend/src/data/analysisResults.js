// Precomputed, already verified findings from the project's own notebooks.
// These are facts checked once against the real simulation and the twin's
// own validation data (see phase4_plan.md and phase6_plan.md), not
// something that needs a live backend call every time someone loads the
// page.

// How many extra tonnes a month each setting is worth on its own, changed
// from the baseline to its best value, everything else held fixed. From
// notebooks/04_optimise.ipynb, the Gaussian process ranking (the model
// actually deployed here). Sorted highest impact first.
export const SENSITIVITY_RANKING = [
  { label: "Winder speed", tonnesGained: 38215 },
  { label: "Skip payload", tonnesGained: 34887 },
  { label: "Scheduled downtime", tonnesGained: 5047 },
  { label: "Breakdown MTBF", tonnesGained: 2221 },
  { label: "Feed rate", tonnesGained: -2295 },
];

// The twin's own remaining life model, accuracy broken down by how much
// true remaining life a reading actually had. From
// notebooks/06_combined.ipynb. Lower is better, hours.
export const WINDER_MODEL_ACCURACY = [
  { label: "0-25 hours left", rmse: 4.9 },
  { label: "25-50 hours left", rmse: 8.3 },
  { label: "50-100 hours left", rmse: 11.1 },
  { label: "100-200 hours left", rmse: 23.8 },
  { label: "200-400 hours left", rmse: 44.1 },
];

// Reactive versus predictive maintenance, 20 replications of each, same
// underlying randomness. From notebooks/06_combined.ipynb /
// reports/combined.md.
export const POLICY_COMPARISON = {
  reactive: { breakdownsPerYear: 42.4, downtimeHoursPerYear: 430.6, annualTonnes: 2845079 },
  predictive: { breakdownsPerYear: 0, downtimeHoursPerYear: 350.5, annualTonnes: 2872027 },
  annualTonnesDiff: 26948,
  downtimeHoursDiff: -80.1,
};
