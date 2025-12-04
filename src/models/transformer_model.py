import torch
import torch.nn as nn
import numpy as np
import pandas as pd
from typing import Tuple

class TimeSeriesTransformer(nn.Module):
    def __init__(self, input_dim=1, d_model=64, nhead=4, num_layers=2, output_dim=1, dropout=0.1):
        super(TimeSeriesTransformer, self).__init__()
        
        self.input_embedding = nn.Linear(input_dim, d_model)
        self.pos_encoder = PositionalEncoding(d_model, dropout)
        
        encoder_layers = nn.TransformerEncoderLayer(d_model, nhead, dim_feedforward=128, dropout=dropout)
        self.transformer_encoder = nn.TransformerEncoder(encoder_layers, num_layers)
        
        self.decoder = nn.Linear(d_model, output_dim)
        
    def forward(self, src):
        # src shape: [seq_len, batch_size, input_dim]
        src = self.input_embedding(src)
        src = self.pos_encoder(src)
        output = self.transformer_encoder(src)
        # Take the last time step output
        output = self.decoder(output[-1])
        return output

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
    def __init__(self, input_dim=11, seq_len=30):
        self.model = TimeSeriesTransformer(input_dim=input_dim)
        self.seq_len = seq_len
        self.optimizer = torch.optim.Adam(self.model.parameters(), lr=0.001)
        self.criterion = nn.MSELoss()
        
    def fit(self, X: pd.DataFrame, y: pd.Series, epochs=10):
        """
        Simple training loop.
        X: Feature DataFrame
        y: Target Series
        """
        self.model.train()
        X_vals = X.values
        y_vals = y.values
        
        # Create sequences
        X_seq, y_seq = [], []
        for i in range(len(X_vals) - self.seq_len):
            X_seq.append(X_vals[i:i+self.seq_len])
            y_seq.append(y_vals[i+self.seq_len])
            
        X_tensor = torch.FloatTensor(np.array(X_seq)).permute(1, 0, 2) # [seq_len, batch, dim]
        y_tensor = torch.FloatTensor(np.array(y_seq)).unsqueeze(1)
        
        for epoch in range(epochs):
            self.optimizer.zero_grad()
            output = self.model(X_tensor)
            loss = self.criterion(output, y_tensor)
            loss.backward()
            self.optimizer.step()
            
    def predict(self, X: pd.DataFrame) -> float:
        """
        Predict next step.
        """
        self.model.eval()
        with torch.no_grad():
            # Take last seq_len rows
            if len(X) < self.seq_len:
                return 0.0
                
            X_seq = X.iloc[-self.seq_len:].values
            X_tensor = torch.FloatTensor(X_seq).unsqueeze(1) # [seq_len, 1, dim]
            output = self.model(X_tensor)
            return float(output.item())
