import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import API_URL from '../config';

const Dashboard = () => {
    const [symbol, setSymbol] = useState('SPY');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get(`${API_URL}/forecast/${symbol}`);
            setData(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || 'Failed to fetch data');
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchData();
    }, []);

    const handleSearch = (e) => {
        e.preventDefault();
        fetchData();
    };

    return (
        <div className="dashboard">
            <header className="header">
                <h1>Antigravity Forecast</h1>
                <form onSubmit={handleSearch} className="search-form">
                    <input
                        type="text"
                        value={symbol}
                        onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                        placeholder="Enter Symbol (e.g. SPY)"
                    />
                    <button type="submit">Forecast</button>
                </form>
            </header>

            {loading && <div className="loading">Loading...</div>}
            {error && <div className="error">{error}</div>}

            {data && (
                <div className="content">
                    <div className="summary-card">
                        <h2>{data.symbol}</h2>
                        <p>Date: {data.date}</p>
                        <p>Current Price: ${data.current_price.toFixed(2)}</p>
                        <p>Regime: {data.regime.label || (data.regime.current === 0 ? 'Low Volatility' : 'High Volatility')}</p>
                    </div>

                    <div className="forecasts-grid">
                        {Object.entries(data.forecasts).map(([horizon, forecast]) => (
                            forecast ? (
                                <div key={horizon} className={`forecast-card ${forecast.expected_return_pct > 0 ? 'bullish' : 'bearish'}`}>
                                    <h3>{horizon} Horizon</h3>
                                    <p className="return">{forecast.expected_return_pct > 0 ? '+' : ''}{forecast.expected_return_pct.toFixed(2)}%</p>
                                    <p className="target">Target: ${forecast.target_price.toFixed(2)}</p>
                                    <p className="date">By: {forecast.target_date}</p>
                                </div>
                            ) : (
                                <div key={horizon} className="forecast-card neutral">
                                    <h3>{horizon} Horizon</h3>
                                    <p>Insufficient Data</p>
                                </div>
                            )
                        ))}
                    </div>

                    <div className="simulation-section">
                        <h3>Simulation Scenarios (10 Days)</h3>
                        <div className="sim-cards">
                            <div className="sim-card bearish">
                                <h4>P10 (Bearish)</h4>
                                <p>${data.simulation.p10.toFixed(2)}</p>
                            </div>
                            <div className="sim-card base">
                                <h4>P50 (Base)</h4>
                                <p>${data.simulation.p50.toFixed(2)}</p>
                            </div>
                            <div className="sim-card bullish">
                                <h4>P90 (Bullish)</h4>
                                <p>${data.simulation.p90.toFixed(2)}</p>
                            </div>
                        </div>
                    </div>

                    <div className="model-breakdown-section" style={{ marginTop: '2rem' }}>
                        <h3>Model Contribution Breakdown (10d Horizon)</h3>
                        <table className="overview-table">
                            <thead>
                                <tr>
                                    <th>Model Component</th>
                                    <th>Raw Output (Log Return / Value)</th>
                                    <th>Description</th>
                                </tr>
                            </thead>
                            <tbody>
                                {data.forecasts["10d"] && data.forecasts["10d"].components && Object.entries(data.forecasts["10d"].components).map(([key, value]) => (
                                    <tr key={key}>
                                        <td>{key}</td>
                                        <td>{typeof value === 'number' ? value.toFixed(4) : value}</td>
                                        <td>
                                            {key === 'LightGBM' && 'Gradient Boosting Regressor'}
                                            {key === 'Transformer' && 'Deep Learning Sequence Model'}
                                            {key === 'GARCH Volatility' && 'Volatility Clustering Model'}
                                            {key === 'Kalman Trend' && 'Noise-Filtered Trend Slope'}
                                            {key === 'HMM Regime' && 'Market Regime Context'}
                                            {key === 'Copula Adjustment' && 'Multi-Asset Correlation Stress'}
                                            {key === 'Monte Carlo P50' && 'Probabilistic Median Price'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>

                    <div className="regime-section">
                        <h3>Regime Probabilities</h3>
                        <div className="regime-bar">
                            <div
                                className="regime-segment low-vol"
                                style={{ width: `${data.regime.probs[0] * 100}%` }}
                                title={`Low Vol: ${(data.regime.probs[0] * 100).toFixed(1)}%`}
                            >
                                Low Vol
                            </div>
                            <div
                                className="regime-segment high-vol"
                                style={{ width: `${data.regime.probs[1] * 100}%` }}
                                title={`High Vol: ${(data.regime.probs[1] * 100).toFixed(1)}%`}
                            >
                                High Vol
                            </div>
                        </div>
                        <p>Current Regime: <strong>{data.regime.label || (data.regime.current === 0 ? 'Low Volatility' : 'High Volatility')}</strong></p>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
