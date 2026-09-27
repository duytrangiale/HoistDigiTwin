"""Remaining useful life models of increasing sophistication: a linear
regression baseline, an XGBoost regressor, and a small LSTM. See
phase5_plan.md at the repo root for the reasoning.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
import torch
import torch.nn as nn
from sklearn.linear_model import LinearRegression
from sklearn.preprocessing import StandardScaler
from torch.utils.data import DataLoader, TensorDataset
from xgboost import XGBRegressor


def train_linear_baseline(X: pd.DataFrame, y: pd.Series) -> LinearRegression:
    model = LinearRegression()
    model.fit(X, y)
    return model


def train_xgboost(X: pd.DataFrame, y: pd.Series, **params) -> XGBRegressor:
    """Matches the pattern already used in src/surrogate/train.py.
    Defaults are modest, since a portfolio scale FD001 training set does
    not need hundreds of deep trees to fit well."""
    defaults = dict(n_estimators=200, max_depth=4, learning_rate=0.05, subsample=0.8, random_state=42)
    defaults.update(params)
    model = XGBRegressor(**defaults)
    model.fit(X, y)
    return model


class RulLSTM(nn.Module):
    """Reads a window of recent cycles and predicts a single remaining
    useful life value. Kept small on purpose, hidden size 64, one or two
    layers, so it comfortably fits a 4GB GPU and trains just as well on
    CPU alone, since this dataset is small either way."""

    def __init__(self, n_features: int, hidden_size: int = 64, num_layers: int = 2):
        super().__init__()
        self.lstm = nn.LSTM(input_size=n_features, hidden_size=hidden_size, num_layers=num_layers, batch_first=True)
        self.output_layer = nn.Linear(hidden_size, 1)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        # x shape: (batch, window_length, n_features)
        _, (h_n, _) = self.lstm(x)
        last_layer_hidden_state = h_n[-1]  # (batch, hidden_size), the final layer's state at the window's last cycle
        return self.output_layer(last_layer_hidden_state).squeeze(-1)


def train_lstm(
    X_train: np.ndarray,
    y_train: np.ndarray,
    X_val: np.ndarray,
    y_val: np.ndarray,
    hidden_size: int = 64,
    num_layers: int = 2,
    batch_size: int = 64,
    n_epochs: int = 30,
    learning_rate: float = 1e-3,
    seed: int = 42,
) -> tuple[RulLSTM, StandardScaler, list[float], list[float]]:
    """Trains the small LSTM. Picks a CUDA device automatically if one is
    available, falls back to CPU otherwise, no code change needed either
    way. Inputs are standardised first, the scaler fit on the training
    windows only and applied to validation the same way, since neural
    networks need normalised inputs far more than tree or linear models
    do. Returns the model from whichever epoch had the best validation
    loss, not necessarily the last one, since a model this size overfits
    quickly: training loss keeps falling long after validation loss stops
    improving. Also returns the fitted scaler and the per epoch training
    and validation loss, so a caller can see that pattern directly rather
    than take it on faith.
    """
    torch.manual_seed(seed)
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

    n_features = X_train.shape[2]
    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train.reshape(-1, n_features)).reshape(X_train.shape)
    X_val_scaled = scaler.transform(X_val.reshape(-1, n_features)).reshape(X_val.shape)

    train_dataset = TensorDataset(
        torch.tensor(X_train_scaled, dtype=torch.float32),
        torch.tensor(y_train, dtype=torch.float32),
    )
    train_loader = DataLoader(train_dataset, batch_size=batch_size, shuffle=True)

    X_val_tensor = torch.tensor(X_val_scaled, dtype=torch.float32).to(device)
    y_val_tensor = torch.tensor(y_val, dtype=torch.float32).to(device)

    model = RulLSTM(n_features=n_features, hidden_size=hidden_size, num_layers=num_layers).to(device)
    optimizer = torch.optim.Adam(model.parameters(), lr=learning_rate)
    loss_fn = nn.MSELoss()

    train_losses = []
    val_losses = []
    best_val_loss = float("inf")
    best_state = None
    for _ in range(n_epochs):
        model.train()
        batch_losses = []
        for X_batch, y_batch in train_loader:
            X_batch, y_batch = X_batch.to(device), y_batch.to(device)
            optimizer.zero_grad()
            predictions = model(X_batch)
            loss = loss_fn(predictions, y_batch)
            loss.backward()
            optimizer.step()
            batch_losses.append(loss.item())
        train_losses.append(sum(batch_losses) / len(batch_losses))

        model.eval()
        with torch.no_grad():
            val_loss = loss_fn(model(X_val_tensor), y_val_tensor).item()
        val_losses.append(val_loss)

        # training loss keeps falling long after validation loss stops
        # improving, a small model like this overfits fast, so the epoch
        # with the best validation loss is kept, not just whatever the
        # model happens to look like after the last epoch
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            best_state = {k: v.clone() for k, v in model.state_dict().items()}

    model.load_state_dict(best_state)
    return model, scaler, train_losses, val_losses


def predict_lstm(model: RulLSTM, scaler: StandardScaler, X: np.ndarray) -> np.ndarray:
    """Runs the LSTM on a batch of windows, applying the same scaler used
    during training first."""
    device = next(model.parameters()).device
    n_features = X.shape[2]
    X_scaled = scaler.transform(X.reshape(-1, n_features)).reshape(X.shape)
    X_tensor = torch.tensor(X_scaled, dtype=torch.float32).to(device)
    model.eval()
    with torch.no_grad():
        predictions = model(X_tensor)
    return predictions.cpu().numpy()
