import React, { useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, ReferenceLine } from 'recharts';
import API_URL from '../config';

const AdvancedSimulation = () => {
    const [symbol, setSymbol] = useState('AAPL');
    const [method, setMethod] = useState('garch');
    const [conservative, setConservative] = useState(false);
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const runSimulation = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setData(null);

        try {
            const response = await axios.get(`${API_URL}/simulation/advanced/${symbol}`, {
                params: { method, conservative }
            });
            setData(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || "Simulation failed");
        } finally {
            setLoading(false);
        }
    };

    // Prepare chart data
    const getChartData = () => {
        if (!data || !data.paths) return [];

        const samplePaths = data.paths.slice(0, 20);
        const chartData = [];
        const numPoints = samplePaths[0].length;

        for (let i = 0; i < numPoints; i++) {
            const point = { day: i * 5 };
            samplePaths.forEach((path, idx) => {
                point[`path${idx}`] = path[i];
            });
            chartData.push(point);
        }
        return chartData;
    };

    return (
        <div className="dashboard">
            <header className="header">
                <h1>Advanced Realistic Simulation</h1>
            </header>

            <div className="content">
                <div className="controls-card" style={{ background: '#1e1e1e', padding: '1.5rem', borderRadius: '12px', marginBottom: '2rem' }}>
                    <form onSubmit={runSimulation} style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap', alignItems: 'end' }}>
                        <div>
                            <label>Symbol</label>
                            <input
                                type="text"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                style={{ display: 'block', marginTop: '0.5rem', padding: '0.5rem' }}
                            />
                        </div>
                        {/* Horizon is now fixed/all */}
                        <div>
                            <label>Method</label>
                            <select
                                value={method}
                                onChange={(e) => setMethod(e.target.value)}
                                style={{ display: 'block', marginTop: '0.5rem', padding: '0.5rem', background: '#333', color: 'white', border: '1px solid #444' }}
                            >
                                <option value="garch">Regime-Switching GARCH + Jumps</option>
                                <option value="bootstrap">Empirical Block Bootstrap</option>
                            </select>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', marginBottom: '0.5rem' }}>
                            <input
                                type="checkbox"
                                checked={conservative}
                                onChange={(e) => setConservative(e.target.checked)}
                                id="conservative-check"
                                style={{ marginRight: '0.5rem', width: 'auto' }}
                            />
                            <label htmlFor="conservative-check" style={{ cursor: 'pointer' }}>Conservative Tails</label>
                        </div>
                        <button type="submit" disabled={loading} style={{ padding: '0.7rem 1.5rem', background: '#00d4ff', border: 'none', borderRadius: '4px', cursor: 'pointer', fontWeight: 'bold' }}>
                            {loading ? 'Simulating...' : 'Run Simulation'}
                        </button>
                    </form>
                </div>

                {error && <div className="error">{error}</div>}

                {data && (
                    <div className="results-grid">
                        <div className="summary-card" style={{ gridColumn: '1 / -1' }}>
                            <h2>Results: {data.symbol}</h2>
                            <p>Current Price: ${data.current_price.toFixed(2)}</p>
                            {data.current_regime && (
                                <p>Detected Regime: <strong>{data.current_regime.label}</strong></p>
                            )}

                            <div className="table-container" style={{ marginTop: '2rem', overflowX: 'auto' }}>
                                <table className="overview-table">
                                    <thead>
                                        <tr>
                                            <th>Horizon</th>
                                            <th>P10 (Bearish)</th>
                                            <th>P50 (Median)</th>
                                            <th>P90 (Bullish)</th>
                                            <th>Risk Analysis</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.quantiles && Object.entries(data.quantiles).sort((a, b) => Number(a[0]) - Number(b[0])).map(([horizon, q]) => (
                                            <tr key={horizon}>
                                                <td>{horizon} Days</td>
                                                <td className="bearish-text">${q.p10.toFixed(2)}</td>
                                                <td>${q.p50.toFixed(2)}</td>
                                                <td className="bullish-text">${q.p90.toFixed(2)}</td>
                                                <td>
                                                    {data.analysis && data.analysis[horizon] ? (
                                                        <span>{data.analysis[horizon].interpretation}</span>
                                                    ) : '-'}
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </div>

                        {data.paths && (
                            <div className="chart-card" style={{ height: '400px', marginTop: '2rem', background: '#1e1e1e', padding: '1rem', borderRadius: '12px', gridColumn: '1 / -1' }}>
                                <h3>Simulation Paths (2 Years)</h3>
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={getChartData()}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                        <XAxis dataKey="day" stroke="#888" label={{ value: 'Days', position: 'insideBottom', offset: -5 }} />
                                        <YAxis domain={['auto', 'auto']} stroke="#888" />
                                        <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none' }} />
                                        {Object.keys(getChartData()[0] || {}).filter(k => k !== 'day').map((key, idx) => (
                                            <Line key={key} type="monotone" dataKey={key} stroke="#8884d8" dot={false} strokeWidth={1} opacity={0.5} />
                                        ))}
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default AdvancedSimulation;
