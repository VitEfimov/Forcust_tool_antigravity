import React, { useState } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import API_URL from '../config';

const AdvancedSimulationV2 = () => {
    const [symbol, setSymbol] = useState('SPY'); // Default to Market (SPY)
    const [conservative, setConservative] = useState(true); // Default to Conservative (Thinner tails)
    const [engine, setEngine] = useState('ensemble'); // Default to Ensemble Professional
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const runSimulation = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setData(null);

        try {
            const response = await axios.get(`${API_URL}/simulation/v2/${symbol}`, {
                params: { conservative, engine }
            });
            setData(response.data);
        } catch (err) {
            setError(err.response?.data?.detail || "Simulation failed");
        } finally {
            setLoading(false);
        }
    };

    // Prepare chart data from paths_sample
    const getChartData = () => {
        if (!data || !data.paths_sample) return [];

        const samplePaths = data.paths_sample.slice(0, 20);
        const chartData = [];
        const numPoints = samplePaths[0]?.length || 0;

        for (let i = 0; i < numPoints; i++) {
            const point = { day: i * 10 }; // Every 10th day
            samplePaths.forEach((path, idx) => {
                point[`path${idx}`] = path[i];
            });
            chartData.push(point);
        }
        return chartData;
    };

    const getRiskColor = (label) => {
        if (label?.includes('Extreme') || label?.includes('High Downside')) return '#ff4444';
        if (label?.includes('Elevated') || label?.includes('High Risk')) return '#ff8800';
        if (label?.includes('Bullish') || label?.includes('Upside')) return '#00cc66';
        return '#888888';
    };

    return (
        <div className="dashboard">
            <header className="header">
                <h1>🔬 Advanced Simulation V2</h1>
                <p style={{ color: '#888', marginTop: '0.5rem' }}>
                    Regime-aware GARCH • Student-t Shocks • Jump Diffusion • Multi-Horizon Analysis
                </p>
            </header>

            <div className="content">
                {/* Controls */}
                <div className="controls-card" style={{ background: '#1e1e1e', padding: '1.5rem', borderRadius: '12px', marginBottom: '2rem' }}>
                    <form onSubmit={runSimulation} style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '1.5rem', alignItems: 'end' }}>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#aaa' }}>Symbol</label>
                            <input
                                type="text"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                style={{ padding: '0.6rem 1rem', fontSize: '1rem', borderRadius: '6px', border: '1px solid #444', background: '#2a2a2a', color: 'white', width: '100%', boxSizing: 'border-box' }}
                            />
                        </div>
                        <div>
                            <label style={{ display: 'block', marginBottom: '0.5rem', color: '#aaa' }}>Engine</label>
                            <select
                                value={engine}
                                onChange={(e) => setEngine(e.target.value)}
                                style={{ padding: '0.6rem 1rem', fontSize: '1rem', borderRadius: '6px', border: '1px solid #444', background: '#2a2a2a', color: 'white', width: '100%', boxSizing: 'border-box' }}
                            >
                                <option value="ensemble">Ensemble (Professional)</option>
                                <option value="legacy">Standard (Slow)</option>
                                <option value="numpy">Vectorized (Fast)</option>
                                <option value="numba">Numba (JIT)</option>
                                <option value="torch">Torch (GPU)</option>
                            </select>
                        </div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', height: '100%', paddingBottom: '0.6rem' }}>
                            <input
                                type="checkbox"
                                checked={conservative}
                                onChange={(e) => setConservative(e.target.checked)}
                                id="conservative-check-v2"
                                style={{ width: '1.2rem', height: '1.2rem' }}
                            />
                            <label htmlFor="conservative-check-v2" style={{ cursor: 'pointer', color: '#ddd' }}>
                                Conservative Tails
                            </label>
                        </div>
                        <button
                            type="submit"
                            disabled={loading}
                            style={{
                                padding: '0.7rem 2rem',
                                background: loading ? '#555' : 'linear-gradient(135deg, #00d4ff, #0099cc)',
                                border: 'none',
                                borderRadius: '6px',
                                cursor: loading ? 'not-allowed' : 'pointer',
                                fontWeight: 'bold',
                                color: 'white',
                                fontSize: '1rem',
                                width: '100%'
                            }}
                        >
                            {loading ? 'Simulating...' : 'Run V2 Simulation'}
                        </button>
                        {data && (
                            <button
                                type="button"
                                onClick={async () => {
                                    try {
                                        await axios.post(`${API_URL}/simulation/save`, data);
                                        alert('V2 Results saved successfully!');
                                    } catch (e) {
                                        alert('Failed to save results.');
                                    }
                                }}
                                style={{
                                    padding: '0.7rem 2rem',
                                    background: '#4CAF50',
                                    border: 'none',
                                    borderRadius: '6px',
                                    cursor: 'pointer',
                                    fontWeight: 'bold',
                                    color: 'white',
                                    fontSize: '1rem',
                                    marginLeft: '15px'
                                }}
                            >
                                Save Results
                            </button>
                        )}
                    </form>
                </div>

                {error && <div className="error" style={{ color: '#ff6666', padding: '1rem', background: '#331111', borderRadius: '8px', marginBottom: '1rem' }}>{error}</div>}

                {data && (
                    <div className="results-grid">
                        {/* Summary Card */}
                        <div className="summary-card" style={{ gridColumn: '1 / -1', background: '#1a1a1a', padding: '1.5rem', borderRadius: '12px', marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
                                <div>
                                    <h2 style={{ margin: 0 }}>{data.symbol}</h2>
                                    <p style={{ color: '#888', margin: '0.5rem 0 0 0' }}>{data.method}</p>
                                </div>
                                <div style={{ textAlign: 'right' }}>
                                    <div style={{ fontSize: '1.8rem', fontWeight: 'bold' }}>${data.current_price}</div>
                                    <div style={{
                                        display: 'inline-block',
                                        padding: '0.3rem 0.8rem',
                                        borderRadius: '20px',
                                        background: data.current_regime?.id === 0 ? '#1a4d1a' : '#4d1a1a',
                                        color: data.current_regime?.id === 0 ? '#66ff66' : '#ff6666',
                                        fontSize: '0.85rem'
                                    }}>
                                        {data.current_regime?.label || 'Unknown'}
                                    </div>
                                </div>
                            </div>
                            {data.conservative_mode && (
                                <div style={{ marginTop: '1rem', padding: '0.5rem', background: '#2a2a1a', borderRadius: '6px', fontSize: '0.85rem', color: '#cccc66' }}>
                                    ⚠️ Conservative Mode: Jump frequency and volatility reduced for safer estimates
                                </div>
                            )}
                        </div>

                        {/* Multi-Horizon Analysis Table */}
                        <div className="table-card" style={{ gridColumn: '1 / -1', background: '#1a1a1a', padding: '1.5rem', borderRadius: '12px', overflowX: 'auto' }}>
                            <h3 style={{ marginTop: 0 }}>📊 Multi-Horizon Risk Analysis</h3>
                            <table className="overview-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid #333' }}>
                                        <th style={{ textAlign: 'left', padding: '0.8rem' }}>Horizon</th>
                                        <th style={{ textAlign: 'right', padding: '0.8rem' }}>P10 (Bear)</th>
                                        <th style={{ textAlign: 'right', padding: '0.8rem' }}>P50 (Base)</th>
                                        <th style={{ textAlign: 'right', padding: '0.8rem' }}>P90 (Bull)</th>
                                        <th style={{ textAlign: 'center', padding: '0.8rem' }}>Risk</th>
                                        <th style={{ textAlign: 'left', padding: '0.8rem' }}>Outlook</th>
                                        <th style={{ textAlign: 'left', padding: '0.8rem' }}>Description</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.analysis && Object.entries(data.analysis)
                                        .sort((a, b) => Number(a[0]) - Number(b[0]))
                                        .map(([horizon, a]) => (
                                            <tr key={horizon} style={{ borderBottom: '1px solid #2a2a2a' }}>
                                                <td style={{ padding: '0.8rem', fontWeight: 'bold' }}>{horizon}d</td>
                                                <td style={{ padding: '0.8rem', textAlign: 'right', color: '#ff6666' }}>
                                                    ${a.p10} <span style={{ fontSize: '0.8rem' }}>({a.downside_pct}%)</span>
                                                </td>
                                                <td style={{ padding: '0.8rem', textAlign: 'right', color: '#aaaaaa' }}>
                                                    ${a.p50} <span style={{ fontSize: '0.8rem' }}>({a.median_change_pct > 0 ? '+' : ''}{a.median_change_pct}%)</span>
                                                </td>
                                                <td style={{ padding: '0.8rem', textAlign: 'right', color: '#66ff66' }}>
                                                    ${a.p90} <span style={{ fontSize: '0.8rem' }}>(+{a.upside_pct}%)</span>
                                                </td>
                                                <td style={{ padding: '0.8rem', textAlign: 'center' }}>
                                                    <span style={{
                                                        padding: '0.2rem 0.6rem',
                                                        borderRadius: '12px',
                                                        background: getRiskColor(a.risk_label) + '33',
                                                        color: getRiskColor(a.risk_label),
                                                        fontSize: '0.8rem'
                                                    }}>
                                                        {a.risk_label}
                                                    </span>
                                                </td>
                                                <td style={{ padding: '0.8rem', color: '#888', fontSize: '0.85rem' }}>
                                                    {a.volatility_outlook}
                                                </td>
                                                <td style={{ padding: '0.8rem', color: '#666', fontSize: '0.8rem', maxWidth: '200px' }}>
                                                    {a.horizon_description}
                                                </td>
                                            </tr>
                                        ))}
                                </tbody>
                            </table>
                        </div>

                        {/* Simulation Paths Chart */}
                        {data.paths_sample && (
                            <div className="chart-card" style={{ gridColumn: '1 / -1', height: '400px', background: '#1a1a1a', padding: '1.5rem', borderRadius: '12px' }}>
                                <h3 style={{ marginTop: 0 }}>📈 Sample Simulation Paths (2 Years)</h3>
                                <ResponsiveContainer width="100%" height="85%">
                                    <LineChart data={getChartData()}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                        <XAxis
                                            dataKey="day"
                                            stroke="#888"
                                            label={{ value: 'Days', position: 'insideBottom', offset: -5, fill: '#888' }}
                                        />
                                        <YAxis
                                            domain={['auto', 'auto']}
                                            stroke="#888"
                                            tickFormatter={(v) => `$${v.toFixed(0)}`}
                                        />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#2a2a2a', border: '1px solid #444', borderRadius: '8px' }}
                                            formatter={(value) => [`$${value.toFixed(2)}`, '']}
                                            labelFormatter={(label) => `Day ${label}`}
                                        />
                                        {Object.keys(getChartData()[0] || {}).filter(k => k !== 'day').slice(0, 20).map((key, idx) => (
                                            <Line
                                                key={key}
                                                type="monotone"
                                                dataKey={key}
                                                stroke={idx % 3 === 0 ? '#00d4ff' : idx % 3 === 1 ? '#ff6666' : '#66ff66'}
                                                dot={false}
                                                strokeWidth={1}
                                                opacity={0.4}
                                            />
                                        ))}
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        )}

                        {/* Transition Matrix (Technical Detail) */}
                        {data.transition_matrix && (
                            <div className="matrix-card" style={{ gridColumn: '1 / -1', background: '#1a1a1a', padding: '1.5rem', borderRadius: '12px' }}>
                                <h3 style={{ marginTop: 0 }}>🔄 Regime Transition Matrix</h3>
                                <p style={{ color: '#888', fontSize: '0.85rem', marginBottom: '1rem' }}>
                                    Probability of transitioning from one regime to another (rows sum to 1)
                                </p>
                                <table style={{ borderCollapse: 'collapse', fontSize: '0.9rem' }}>
                                    <thead>
                                        <tr>
                                            <th style={{ padding: '0.5rem', borderBottom: '1px solid #444' }}></th>
                                            <th style={{ padding: '0.5rem', borderBottom: '1px solid #444', color: '#66ff66' }}>To Bull</th>
                                            <th style={{ padding: '0.5rem', borderBottom: '1px solid #444', color: '#ffcc00' }}>To Transition</th>
                                            <th style={{ padding: '0.5rem', borderBottom: '1px solid #444', color: '#ff6666' }}>To Bear</th>
                                        </tr>
                                    </thead>
                                    <tbody>
                                        {data.transition_matrix.map((row, i) => (
                                            <tr key={i}>
                                                <td style={{ padding: '0.5rem', fontWeight: 'bold', color: i === 0 ? '#66ff66' : i === 1 ? '#ffcc00' : '#ff6666' }}>
                                                    From {i === 0 ? 'Bull' : i === 1 ? 'Trans' : 'Bear'}
                                                </td>
                                                {row.map((p, j) => (
                                                    <td key={j} style={{ padding: '0.5rem', textAlign: 'center' }}>
                                                        {(p * 100).toFixed(1)}%
                                                    </td>
                                                ))}
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        )}
                    </div>
                )}
            </div>
        </div>
    );
};

export default AdvancedSimulationV2;
