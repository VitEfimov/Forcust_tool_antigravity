import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';

const Dashboard = () => {
    const [symbol, setSymbol] = useState('SPY');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const response = await axios.get(`http://localhost:8000/forecast/${symbol}`);
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
                        <p>Regime: {data.regime.current === 0 ? 'Low Volatility' : 'High Volatility'}</p>
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

                    <div className="chart-container">
                        <h3>Simulation Scenarios (10 Days)</h3>
                        <div className="quantiles">
                            <div className="quantile-box bad">
                                <span>P10 (Bearish)</span>
                                <span>${data.simulation.p10.toFixed(2)}</span>
                            </div>
                            <div className="quantile-box base">
                                <span>P50 (Base)</span>
                                <span>${data.simulation.p50.toFixed(2)}</span>
                            </div>
                            <div className="quantile-box good">
                                <span>P90 (Bullish)</span>
                                <span>${data.simulation.p90.toFixed(2)}</span>
                            </div>
                        </div>
                    </div>

                    <div className="regime-info">
                        <h3>Regime Probabilities</h3>
                        <div className="progress-bar">
                            <div
                                className="progress-segment low-vol"
                                style={{ width: `${data.regime.probs[0] * 100}%` }}
                                title={`Low Vol: ${(data.regime.probs[0] * 100).toFixed(1)}%`}
                            >
                                Low Vol
                            </div>
                            <div
                                className="progress-segment high-vol"
                                style={{ width: `${data.regime.probs[1] * 100}%` }}
                                title={`High Vol: ${(data.regime.probs[1] * 100).toFixed(1)}%`}
                            >
                                High Vol
                            </div>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
