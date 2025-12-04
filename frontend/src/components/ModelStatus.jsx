import React from 'react';

const ModelStatus = () => {
    const models = [
        { file: "hmm_regime.py", name: "Hidden Markov Model", desc: "Detects market regimes (Bull/Bear/Volatile) to adjust forecast confidence." },
        { file: "lightgbm_forecaster.py", name: "LightGBM Regressor", desc: "Gradient boosting model trained on 10-year business cycles for horizon-based forecasting." },
        { file: "transformer_model.py", name: "Transformer (Deep Learning)", desc: "Captures long-range dependencies and sequence patterns using attention mechanisms." },
        { file: "garch_volatility.py", name: "GARCH(1,1)", desc: "Forecasts future volatility to estimate risk and confidence intervals." },
        { file: "kalman_filter.py", name: "Kalman Filter", desc: "State-space model for noise filtering and extracting the true underlying trend." },
        { file: "copula_correlation.py", name: "Gaussian Copula", desc: "Models multi-asset correlations to detect systemic risk and contagion." },
        { file: "monte_carlo.py", name: "Monte Carlo Simulator", desc: "Generates thousands of future price paths to estimate probability distributions." },
        { file: "rl_agent.py", name: "RL Agent (Optional)", desc: "Reinforcement Learning agent for adaptive portfolio optimization." },
        { file: "ensemble.py", name: "Ensemble Meta-Model", desc: "Aggregates all model outputs into a final weighted prediction." }
    ];

    return (
        <div className="model-status">
            <h2>System Architecture & Model Status</h2>
            <div className="table-container">
                <table className="indices-table">
                    <thead>
                        <tr>
                            <th>Module File</th>
                            <th>Model Name</th>
                            <th>Description</th>
                            <th>Status</th>
                        </tr>
                    </thead>
                    <tbody>
                        {models.map((m, i) => (
                            <tr key={i}>
                                <td style={{ fontFamily: 'monospace', color: '#88ccff' }}>{m.file}</td>
                                <td style={{ fontWeight: 'bold' }}>{m.name}</td>
                                <td>{m.desc}</td>
                                <td><span style={{ color: '#44ff44' }}>● Active</span></td>
                            </tr>
                        ))}
                    </tbody>
                </table>
            </div>
        </div>
    );
};

export default ModelStatus;
