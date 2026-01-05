import React, { useState, useEffect } from 'react';
import axios from 'axios';
import {
    LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer,
    AreaChart, Area
} from 'recharts';
import './Analytics.css'; // We will create this as well
import AdvancedAnalytics from './AdvancedAnalytics';

const Analytics = () => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);
    const [selectedSnapshot, setSelectedSnapshot] = useState(null);
    const [selectedDetailedSymbol, setSelectedDetailedSymbol] = useState(null);

    useEffect(() => {
        fetchHistory();
    }, []);

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    const fetchHistory = async () => {
        try {
            const response = await axios.get(`${API_URL}/market/history?limit=30`);
            const data = response.data.history || [];

            // Process data for charts
            // Each item has { date, data: { overview: [...] } }
            // We want to calculate aggregate stats for each date

            const processed = data.map(item => {
                const overview = item.data?.overview || [];
                const date = new Date(item.timestamp || item.date).toLocaleDateString();

                let uptrend = 0;
                let downtrend = 0;
                let highVol = 0;
                let lowVol = 0;
                let moderateVol = 0;

                overview.forEach(stock => {
                    if (stock.regime === 'Uptrend') uptrend++;
                    if (stock.regime === 'Downtrend') downtrend++;

                    if (stock.risk_label === 'High Volatility') highVol++;
                    else if (stock.risk_label === 'Low Volatility') lowVol++;
                    else if (stock.risk_label === 'Moderate') moderateVol++;
                });

                return {
                    date,
                    fullDate: item.timestamp || item.date,
                    uptrend,
                    downtrend,
                    highVol,
                    lowVol,
                    moderateVol,
                    total: overview.length,
                    rawOverview: overview
                };
            }).reverse(); // Oldest first for charts

            setHistory(processed);
            if (processed.length > 0) {
                setSelectedSnapshot(processed[processed.length - 1]);
            }
            setLoading(false);
        } catch (err) {
            console.error("Failed to fetch history:", err);
            const msg = err.response?.data?.detail || err.message || "Failed to load market history.";
            setError(`Error: ${msg}`);
            setLoading(false);
        }
    };

    if (loading) return <div className="analytics-loading">Loading Analytics...</div>;
    if (error) return <div className="analytics-error">{error}</div>;

    return (
        <div className="analytics-container">
            <header className="analytics-header">
                <h2>Market Analytics</h2>
                <p>Historical trend analysis of market regimes and volatility.</p>
            </header>

            <div className="charts-grid">
                <div className="chart-card">
                    <h3>Regime Distribution (Market Breadth)</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <BarChart data={history}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                            <XAxis dataKey="date" stroke="#ccc" />
                            <YAxis stroke="#ccc" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#222', borderColor: '#444' }}
                                itemStyle={{ color: '#ccc' }}
                            />
                            <Legend />
                            <Bar dataKey="uptrend" stackId="a" fill="#4caf50" name="Uptrend" />
                            <Bar dataKey="downtrend" stackId="a" fill="#f44336" name="Downtrend" />
                        </BarChart>
                    </ResponsiveContainer>
                </div>

                <div className="chart-card">
                    <h3>Volatility Risk Profile</h3>
                    <ResponsiveContainer width="100%" height={300}>
                        <AreaChart data={history}>
                            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                            <XAxis dataKey="date" stroke="#ccc" />
                            <YAxis stroke="#ccc" />
                            <Tooltip
                                contentStyle={{ backgroundColor: '#222', borderColor: '#444' }}
                                itemStyle={{ color: '#ccc' }}
                            />
                            <Legend />
                            <Area type="monotone" dataKey="highVol" stackId="1" stroke="#ff5252" fill="#ff5252" name="High Risk" />
                            <Area type="monotone" dataKey="moderateVol" stackId="1" stroke="#ffeb3b" fill="#ffeb3b" name="Moderate" />
                            <Area type="monotone" dataKey="lowVol" stackId="1" stroke="#4caf50" fill="#4caf50" name="Stable" />
                        </AreaChart>
                    </ResponsiveContainer>
                </div>
            </div>

            <div className="snapshot-section">
                <h3>Detailed Snapshot: {selectedSnapshot?.date}</h3>
                <div className="snapshot-controls">
                    {history.map((h, i) => (
                        <button
                            key={i}
                            className={selectedSnapshot?.fullDate === h.fullDate ? 'active' : ''}
                            onClick={() => setSelectedSnapshot(h)}
                        >
                            {h.date}
                        </button>
                    ))}
                </div>

                {selectedSnapshot && (
                    <div className="table-container">
                        <table className="analytics-table">
                            <thead>
                                <tr>
                                    <th>Symbol</th>
                                    <th>Price</th>
                                    <th>Change %</th>
                                    <th>Regime</th>
                                    <th>Volatility</th>
                                    <th>Forecast (30d)</th>
                                </tr>
                            </thead>
                            <tbody>
                                {selectedSnapshot.rawOverview.map((stock, idx) => (
                                    <tr key={idx} className="analytics-row" onClick={() => setSelectedDetailedSymbol(stock.symbol)}>
                                        <td className="font-bold symbol-cell">{stock.symbol} 🔍</td>
                                        <td>${stock.price?.toFixed(2)}</td>
                                        <td className={stock.change_pct >= 0 ? 'text-green' : 'text-red'}>
                                            {stock.change_pct > 0 ? '+' : ''}{stock.change_pct}%
                                        </td>
                                        <td>
                                            <span className={`badge ${stock.regime === 'Uptrend' ? 'badge-green' : 'badge-red'}`}>
                                                {stock.regime}
                                            </span>
                                        </td>
                                        <td>
                                            <span className={`badge ${stock.risk_label === 'High Volatility' ? 'badge-red' : stock.risk_label === 'Low Volatility' ? 'badge-green' : 'badge-yellow'}`}>
                                                {stock.risk_label}
                                            </span>
                                        </td>
                                        <td>
                                            {stock.forecast_30d_pct ? (
                                                <span className={stock.forecast_30d_pct >= 0 ? 'text-green' : 'text-red'}>
                                                    {stock.forecast_30d_pct > 0 ? '+' : ''}{stock.forecast_30d_pct}%
                                                </span>
                                            ) : 'N/A'}
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                )}
            </div>

            {/* Advanced Analytics Overlay/Modal */}
            {
                selectedDetailedSymbol && (
                    <div className="analytics-overlay">
                        <AdvancedAnalytics
                            symbol={selectedDetailedSymbol}
                            onClose={() => setSelectedDetailedSymbol(null)}
                        />
                    </div>
                )
            }
        </div >
    );
};

export default Analytics;
