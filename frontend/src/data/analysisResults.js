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

// One simulated winder life, true health and the noisy reading over
// time, the same sample notebooks/06_combined.ipynb itself plots.
export const WINDER_LIFETIME_SAMPLE = [
  {
    "elapsedHours": 24.0,
    "trueHealth": 95.17,
    "observedHealth": 94.19
  },
  {
    "elapsedHours": 48.0,
    "trueHealth": 90.34,
    "observedHealth": 90.8
  },
  {
    "elapsedHours": 72.0,
    "trueHealth": 85.51,
    "observedHealth": 84.36
  },
  {
    "elapsedHours": 96.0,
    "trueHealth": 80.69,
    "observedHealth": 78.71
  },
  {
    "elapsedHours": 120.0,
    "trueHealth": 75.86,
    "observedHealth": 73.62
  },
  {
    "elapsedHours": 144.0,
    "trueHealth": 71.03,
    "observedHealth": 72.83
  },
  {
    "elapsedHours": 168.0,
    "trueHealth": 66.2,
    "observedHealth": 64.53
  },
  {
    "elapsedHours": 192.0,
    "trueHealth": 61.37,
    "observedHealth": 64.58
  },
  {
    "elapsedHours": 216.0,
    "trueHealth": 56.54,
    "observedHealth": 55.61
  },
  {
    "elapsedHours": 240.0,
    "trueHealth": 51.72,
    "observedHealth": 51.05
  },
  {
    "elapsedHours": 264.0,
    "trueHealth": 46.89,
    "observedHealth": 49.06
  },
  {
    "elapsedHours": 288.0,
    "trueHealth": 42.06,
    "observedHealth": 40.34
  },
  {
    "elapsedHours": 312.0,
    "trueHealth": 37.23,
    "observedHealth": 37.01
  },
  {
    "elapsedHours": 336.0,
    "trueHealth": 32.4,
    "observedHealth": 29.64
  },
  {
    "elapsedHours": 360.0,
    "trueHealth": 27.57,
    "observedHealth": 29.54
  },
  {
    "elapsedHours": 384.0,
    "trueHealth": 22.75,
    "observedHealth": 24.57
  },
  {
    "elapsedHours": 408.0,
    "trueHealth": 17.92,
    "observedHealth": 18.31
  },
  {
    "elapsedHours": 432.0,
    "trueHealth": 13.09,
    "observedHealth": 15.61
  },
  {
    "elapsedHours": 456.0,
    "trueHealth": 8.26,
    "observedHealth": 6.04
  },
  {
    "elapsedHours": 480.0,
    "trueHealth": 3.43,
    "observedHealth": -0.5
  },
  {
    "elapsedHours": 497.1,
    "trueHealth": 0.0,
    "observedHealth": 1.68
  }
];

// Predicted versus true remaining life on the held out validation lives,
// downsampled from the full set for a fast, readable scatter plot.
export const RUL_SCATTER_SAMPLE = [{"trueHours": 171.2, "predictedHours": 156.6}, {"trueHours": 51.2, "predictedHours": 53.1}, {"trueHours": 69.8, "predictedHours": 85.2}, {"trueHours": 203.8, "predictedHours": 177.2}, {"trueHours": 59.8, "predictedHours": 52.5}, {"trueHours": 42.6, "predictedHours": 41.8}, {"trueHours": 58.3, "predictedHours": 81.0}, {"trueHours": 196.7, "predictedHours": 174.4}, {"trueHours": 52.7, "predictedHours": 57.3}, {"trueHours": 71.7, "predictedHours": 56.8}, {"trueHours": 300.0, "predictedHours": 304.8}, {"trueHours": 180.0, "predictedHours": 168.5}, {"trueHours": 36.0, "predictedHours": 26.6}, {"trueHours": 109.8, "predictedHours": 114.3}, {"trueHours": 110.0, "predictedHours": 106.5}, {"trueHours": 335.2, "predictedHours": 292.0}, {"trueHours": 191.2, "predictedHours": 190.1}, {"trueHours": 47.2, "predictedHours": 31.3}, {"trueHours": 131.4, "predictedHours": 116.0}, {"trueHours": 0.0, "predictedHours": 0.6}, {"trueHours": 49.0, "predictedHours": 53.8}, {"trueHours": 75.5, "predictedHours": 84.5}, {"trueHours": 243.5, "predictedHours": 212.2}, {"trueHours": 99.5, "predictedHours": 100.7}, {"trueHours": 150.2, "predictedHours": 143.3}, {"trueHours": 6.2, "predictedHours": 4.4}, {"trueHours": 168.2, "predictedHours": 163.5}, {"trueHours": 24.2, "predictedHours": 21.1}, {"trueHours": 27.5, "predictedHours": 29.8}, {"trueHours": 38.3, "predictedHours": 47.0}, {"trueHours": 92.2, "predictedHours": 93.9}, {"trueHours": 97.0, "predictedHours": 95.4}, {"trueHours": 0.0, "predictedHours": -1.1}, {"trueHours": 204.0, "predictedHours": 266.5}, {"trueHours": 60.0, "predictedHours": 56.0}, {"trueHours": 26.7, "predictedHours": 37.9}, {"trueHours": 83.5, "predictedHours": 71.7}, {"trueHours": 55.7, "predictedHours": 57.8}, {"trueHours": 148.0, "predictedHours": 155.3}, {"trueHours": 4.0, "predictedHours": 0.6}, {"trueHours": 175.1, "predictedHours": 187.5}, {"trueHours": 31.1, "predictedHours": 25.8}, {"trueHours": 64.3, "predictedHours": 55.8}, {"trueHours": 135.0, "predictedHours": 129.1}, {"trueHours": 0.0, "predictedHours": 0.4}, {"trueHours": 132.5, "predictedHours": 136.0}, {"trueHours": 0.0, "predictedHours": 3.6}, {"trueHours": 113.9, "predictedHours": 88.6}, {"trueHours": 109.1, "predictedHours": 97.9}, {"trueHours": 139.4, "predictedHours": 220.5}, {"trueHours": 0.0, "predictedHours": 3.1}, {"trueHours": 10.4, "predictedHours": 19.0}, {"trueHours": 76.9, "predictedHours": 68.1}, {"trueHours": 25.0, "predictedHours": 29.9}, {"trueHours": 170.8, "predictedHours": 184.0}, {"trueHours": 26.8, "predictedHours": 43.4}, {"trueHours": 219.3, "predictedHours": 220.1}, {"trueHours": 75.3, "predictedHours": 62.6}, {"trueHours": 88.9, "predictedHours": 75.6}, {"trueHours": 81.1, "predictedHours": 70.8}, {"trueHours": 34.1, "predictedHours": 34.7}, {"trueHours": 180.9, "predictedHours": 170.3}, {"trueHours": 36.9, "predictedHours": 25.2}, {"trueHours": 178.5, "predictedHours": 172.3}, {"trueHours": 34.5, "predictedHours": 46.1}, {"trueHours": 191.7, "predictedHours": 208.6}, {"trueHours": 47.7, "predictedHours": 44.4}, {"trueHours": 147.8, "predictedHours": 144.3}, {"trueHours": 3.8, "predictedHours": 8.6}, {"trueHours": 243.6, "predictedHours": 218.3}, {"trueHours": 99.6, "predictedHours": 78.2}, {"trueHours": 99.5, "predictedHours": 117.3}, {"trueHours": 46.6, "predictedHours": 43.1}, {"trueHours": 15.8, "predictedHours": 17.7}, {"trueHours": 188.2, "predictedHours": 183.7}, {"trueHours": 44.2, "predictedHours": 52.7}, {"trueHours": 0.0, "predictedHours": -1.0}, {"trueHours": 80.2, "predictedHours": 91.5}, {"trueHours": 286.8, "predictedHours": 268.6}, {"trueHours": 142.8, "predictedHours": 139.0}, {"trueHours": 0.0, "predictedHours": 4.8}, {"trueHours": 36.4, "predictedHours": 31.6}, {"trueHours": 29.0, "predictedHours": 34.9}, {"trueHours": 16.8, "predictedHours": 17.7}, {"trueHours": 202.9, "predictedHours": 189.3}, {"trueHours": 58.9, "predictedHours": 43.1}, {"trueHours": 36.9, "predictedHours": 36.1}, {"trueHours": 0.0, "predictedHours": -0.7}, {"trueHours": 85.0, "predictedHours": 78.7}, {"trueHours": 110.2, "predictedHours": 158.9}, {"trueHours": 200.3, "predictedHours": 217.8}, {"trueHours": 56.3, "predictedHours": 54.3}, {"trueHours": 202.1, "predictedHours": 178.2}, {"trueHours": 58.1, "predictedHours": 65.5}, {"trueHours": 178.6, "predictedHours": 187.0}, {"trueHours": 34.6, "predictedHours": 30.4}, {"trueHours": 51.8, "predictedHours": 54.1}, {"trueHours": 200.2, "predictedHours": 148.8}, {"trueHours": 56.2, "predictedHours": 48.9}, {"trueHours": 133.3, "predictedHours": 122.5}, {"trueHours": 0.0, "predictedHours": 0.3}, {"trueHours": 60.6, "predictedHours": 43.5}, {"trueHours": 176.1, "predictedHours": 170.3}, {"trueHours": 32.1, "predictedHours": 35.5}, {"trueHours": 103.4, "predictedHours": 120.8}, {"trueHours": 0.0, "predictedHours": 0.4}, {"trueHours": 266.6, "predictedHours": 313.4}, {"trueHours": 122.6, "predictedHours": 120.9}, {"trueHours": 0.0, "predictedHours": 3.3}, {"trueHours": 91.2, "predictedHours": 91.0}, {"trueHours": 130.6, "predictedHours": 146.0}, {"trueHours": 0.0, "predictedHours": 3.3}, {"trueHours": 44.0, "predictedHours": 33.7}, {"trueHours": 166.3, "predictedHours": 152.0}, {"trueHours": 22.3, "predictedHours": 31.7}, {"trueHours": 90.6, "predictedHours": 100.1}, {"trueHours": 46.5, "predictedHours": 55.0}, {"trueHours": 74.9, "predictedHours": 59.6}, {"trueHours": 85.5, "predictedHours": 77.2}, {"trueHours": 262.7, "predictedHours": 254.7}, {"trueHours": 118.7, "predictedHours": 121.5}, {"trueHours": 183.2, "predictedHours": 210.6}, {"trueHours": 39.2, "predictedHours": 67.5}, {"trueHours": 101.5, "predictedHours": 109.8}, {"trueHours": 153.9, "predictedHours": 191.0}, {"trueHours": 9.9, "predictedHours": 7.6}, {"trueHours": 35.8, "predictedHours": 33.6}, {"trueHours": 129.1, "predictedHours": 123.8}, {"trueHours": 0.0, "predictedHours": 0.6}, {"trueHours": 184.7, "predictedHours": 161.4}, {"trueHours": 40.7, "predictedHours": 35.9}, {"trueHours": 129.2, "predictedHours": 112.1}, {"trueHours": 0.0, "predictedHours": 0.6}, {"trueHours": 34.7, "predictedHours": 30.5}, {"trueHours": 67.8, "predictedHours": 81.5}, {"trueHours": 136.1, "predictedHours": 152.2}, {"trueHours": 16.1, "predictedHours": 10.9}, {"trueHours": 65.6, "predictedHours": 68.2}, {"trueHours": 77.2, "predictedHours": 62.2}, {"trueHours": 214.3, "predictedHours": 253.4}, {"trueHours": 70.3, "predictedHours": 73.5}, {"trueHours": 128.0, "predictedHours": 154.5}, {"trueHours": 0.0, "predictedHours": 0.4}, {"trueHours": 32.8, "predictedHours": 33.7}, {"trueHours": 110.3, "predictedHours": 143.4}, {"trueHours": 150.8, "predictedHours": 218.3}, {"trueHours": 6.8, "predictedHours": 7.8}, {"trueHours": 166.3, "predictedHours": 155.3}, {"trueHours": 22.3, "predictedHours": 12.8}, {"trueHours": 190.0, "predictedHours": 183.2}, {"trueHours": 46.0, "predictedHours": 56.9}, {"trueHours": 0.0, "predictedHours": 1.1}, {"trueHours": 148.8, "predictedHours": 138.7}, {"trueHours": 4.8, "predictedHours": 5.7}, {"trueHours": 97.0, "predictedHours": 105.0}, {"trueHours": 184.4, "predictedHours": 294.3}, {"trueHours": 40.4, "predictedHours": 35.2}, {"trueHours": 163.0, "predictedHours": 140.7}, {"trueHours": 19.0, "predictedHours": 20.2}, {"trueHours": 229.6, "predictedHours": 254.4}, {"trueHours": 85.6, "predictedHours": 90.6}, {"trueHours": 169.0, "predictedHours": 153.0}, {"trueHours": 25.0, "predictedHours": 29.9}, {"trueHours": 74.8, "predictedHours": 60.1}, {"trueHours": 279.0, "predictedHours": 366.7}, {"trueHours": 135.0, "predictedHours": 151.5}, {"trueHours": 0.0, "predictedHours": 3.2}, {"trueHours": 62.7, "predictedHours": 53.4}, {"trueHours": 67.0, "predictedHours": 72.3}, {"trueHours": 148.2, "predictedHours": 144.3}, {"trueHours": 4.2, "predictedHours": 8.0}, {"trueHours": 320.4, "predictedHours": 318.5}, {"trueHours": 176.4, "predictedHours": 154.1}, {"trueHours": 32.4, "predictedHours": 18.8}, {"trueHours": 309.3, "predictedHours": 271.8}, {"trueHours": 165.3, "predictedHours": 175.6}, {"trueHours": 21.3, "predictedHours": 22.8}, {"trueHours": 28.1, "predictedHours": 28.0}, {"trueHours": 158.6, "predictedHours": 160.7}, {"trueHours": 14.6, "predictedHours": 5.0}, {"trueHours": 0.0, "predictedHours": 0.2}, {"trueHours": 69.6, "predictedHours": 61.2}, {"trueHours": 41.9, "predictedHours": 54.3}, {"trueHours": 14.9, "predictedHours": 15.1}, {"trueHours": 172.5, "predictedHours": 165.1}, {"trueHours": 28.5, "predictedHours": 42.6}, {"trueHours": 299.3, "predictedHours": 283.7}, {"trueHours": 155.3, "predictedHours": 140.5}, {"trueHours": 35.3, "predictedHours": 30.5}, {"trueHours": 182.0, "predictedHours": 185.3}, {"trueHours": 38.0, "predictedHours": 61.3}, {"trueHours": 155.8, "predictedHours": 176.0}, {"trueHours": 11.8, "predictedHours": 4.4}, {"trueHours": 23.5, "predictedHours": 20.0}, {"trueHours": 116.1, "predictedHours": 127.9}, {"trueHours": 201.0, "predictedHours": 193.0}, {"trueHours": 57.0, "predictedHours": 84.6}, {"trueHours": 50.8, "predictedHours": 56.3}, {"trueHours": 72.4, "predictedHours": 61.9}, {"trueHours": 393.9, "predictedHours": 223.3}, {"trueHours": 249.9, "predictedHours": 201.4}, {"trueHours": 105.9, "predictedHours": 97.1}, {"trueHours": 100.0, "predictedHours": 111.2}, {"trueHours": 300.0, "predictedHours": 261.1}, {"trueHours": 156.0, "predictedHours": 146.7}, {"trueHours": 12.0, "predictedHours": 10.2}, {"trueHours": 12.9, "predictedHours": 17.2}, {"trueHours": 66.7, "predictedHours": 62.5}, {"trueHours": 165.7, "predictedHours": 175.9}, {"trueHours": 45.7, "predictedHours": 38.7}, {"trueHours": 55.3, "predictedHours": 58.7}, {"trueHours": 81.4, "predictedHours": 86.4}, {"trueHours": 105.6, "predictedHours": 119.5}, {"trueHours": 197.5, "predictedHours": 140.2}, {"trueHours": 53.5, "predictedHours": 59.7}, {"trueHours": 0.0, "predictedHours": -0.8}, {"trueHours": 70.1, "predictedHours": 85.1}, {"trueHours": 25.6, "predictedHours": 23.9}, {"trueHours": 0.0, "predictedHours": -0.7}, {"trueHours": 0.0, "predictedHours": -1.5}];
