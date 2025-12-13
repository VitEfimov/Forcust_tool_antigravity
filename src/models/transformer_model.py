import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from torch.utils.data import DataLoader, Dataset
from typing import Tuple

class TimeSeriesDataset(Dataset):
    def __init__(self, X, y, seq_len):
        self.X = X
        self.y = y
        self.seq_len = seq_len

    def __len__(self):
        return len(self.X) - self.seq_len

    def __getitem__(self, idx):
        return (
            torch.tensor(self.X[idx:idx+self.seq_len], dtype=torch.float32),
            torch.tensor(self.y[idx+self.seq_len], dtype=torch.float32),
        )

class TimeSeriesTransformer(nn.Module):
    def __init__(self, input_dim=1, d_model=64, nhead=4, num_layers=2, output_dim=1, dropout=0.1):
        """
        V3 Transformer: Causal Masking, LayerNorm, Dropout enabled.
        """
        super(TimeSeriesTransformer, self).__init__()
        
        self.input_embedding = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model, dropout)
        self.layernorm = nn.LayerNorm(d_model)
        
        encoder_layers = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=128, dropout=dropout, batch_first=False)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        
        self.decoder = nn.Linear(d_model, output_dim)
        
    def generate_causal_mask(self, seq_len, device):
        # True = Masked (Ignored). Upper triangle is future.
        return torch.triu(
            torch.ones(seq_len, seq_len, device=device), diagonal=1
        ).bool()
        
    def forward(self, src):
        # src shape values: [seq_len, batch_size, input_dim]
        # 1. Embed & Norm
        src = self.input_embedding(src)
        src = self.pos_encoder(src)
        src = self.layernorm(src)
        
        # 2. Causal Mask
        seq_len = src.size(0)
        mask = self.generate_causal_mask(seq_len, src.device)
        
        # 3. Transform
        # TransformerEncoder expects src_mask=mask
        output = self.transformer_encoder(src, mask=mask)
        
        # 4. Decode Last Step
        last_step = output[-1, :, :] # [batch, d_model]
        prediction = self.decoder(last_step) # [batch, output_dim]
        
        return prediction

class PositionalEncoding(nn.Module):
    def __init__(self, d_model, dropout=0.1, max_len=5000):
        super(PositionalEncoding, self).__init__()
        self.dropout = nn.Dropout(p=dropout)

        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len, dtype=torch.float).unsqueeze(1)
        div_term = torch.exp(torch.arange(0, d_model, 2).float() * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        pe = pe.unsqueeze(0).transpose(0, 1)
        self.register_buffer('pe', pe)

    def forward(self, x):
        x = x + self.pe[:x.size(0), :]
        return self.dropout(x)

class TransformerForecaster:
    def __init__(self, input_dim=11, seq_len=30, device=None):
        self.device = device if device else torch.device("cuda" if torch.cuda.is_available() else "cpu")
        # Output dim 1 because we use MC Dropout for uncertainty, not explicit sigma output
        self.model = TimeSeriesTransformer(input_dim=input_dim, output_dim=1).to(self.device)
        self.seq_len = seq_len
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        self.batch_size = 32
        
        # 5. Torch Compile (Optional 'Ultra' Speedup)
        try:
            self.model = torch.compile(self.model)
        except:
            pass
        
    def fit(self, X: pd.DataFrame, y: pd.Series, epochs=5):
        """
        Fit with time-series preserving DataLoader (shuffle=False).
        Warm-starts by default as model persists.
        """
        self.model.train()
        X_vals = X.values.astype(np.float32)
        y_vals = y.values.astype(np.float32)
        
        if len(X_vals) <= self.seq_len:
            return

        dataset = TimeSeriesDataset(X_vals, y_vals, self.seq_len)
        loader = DataLoader(dataset, batch_size=self.batch_size, shuffle=False) 
        
        for epoch in range(epochs):
            for batch_X, batch_y in loader:
                # batch_X: [batch, seq_len, dim] -> permute to [seq_len, batch, dim]
                batch_X = batch_X.permute(1, 0, 2).to(self.device)
                batch_y = batch_y.to(self.device).unsqueeze(1) # [batch, 1]
                
                self.optimizer.zero_grad()
                pred = self.model(batch_X) # [batch, 1]
                
                loss = self.criterion(pred, batch_y)
                loss.backward()
                self.optimizer.step()
            
    def predict(self, X: pd.DataFrame, mc_samples: int = 20, fast: bool = False) -> Tuple[float, float]:
        """
        Predict next step.
        fast=True: Single forward pass (No Dropout), returns (Mean, 0.0).
        fast=False: Monte Carlo Dropout (20 passes), returns (Mean, StdDev).
        """
        if len(X) < self.seq_len:
            return 0.0, 1.0 # Default fallback
            
        X_seq = X.iloc[-self.seq_len:].values.astype(np.float32)
        X_tensor = torch.tensor(X_seq).unsqueeze(1).to(self.device) # [seq_len, 1, dim]

        # Fast Inference Mode (Prod / Speed)
        if fast:
            self.model.eval()
            with torch.no_grad():
                output = self.model(X_tensor)
                return float(output.item()), 0.0

        # Monte Carlo Dropout (Research / Robustness)
        self.model.train() 
        preds = []
        with torch.no_grad():
            for _ in range(mc_samples):
                output = self.model(X_tensor) # [1, 1]
                preds.append(output.item())
        
        preds = np.array(preds)
        mean_pred = float(np.mean(preds))
        std_pred = float(np.std(preds))
        
        # Ensure std is non-zero
        if std_pred < 1e-9:
            std_pred = 1e-9
            
        return mean_pred, std_pred
