
import React, { useState } from 'react';
import axios from 'axios';
import API_URL from '../config';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';

const DeepDiveAnalysis = () => {
    const [symbol, setSymbol] = useState('');
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);

    const handleAnalyze = async (e) => {
        e.preventDefault();
        if (!symbol) return;

        setLoading(true);
        setError(null);
        setData(null);

        try {
            const response = await axios.get(`${API_URL}/forecast/${symbol.toUpperCase()}`);
            setData(response.data);
        } catch (err) {
            console.error("Analysis Error:", err);
            setError(err.response?.data?.detail || "Failed to fetch analysis");
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="deep-dive-container" style={{ padding: '20px', color: '#e0e0e0', maxWidth: '1200px', margin: '0 auto' }}>
            <h1 style={{ borderBottom: '1px solid #333', paddingBottom: '10px' }}>🔍 Deep Dive Analysis</h1>

            {/* Search Section */}
            <form onSubmit={handleAnalyze} style={{ display: 'flex', gap: '10px', margin: '20px 0' }}>
                <input
                    type="text"
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value)}
                    placeholder="Enter Symbol (e.g. NVDA)"
                    style={{
                        padding: '12px',
                        borderRadius: '8px',
                        border: '1px solid #444',
                        background: '#222',
                        color: 'white',
                        fontSize: '1rem',
                        flex: 1,
                        maxWidth: '300px'
                    }}
                />
                <button
                    type="submit"
                    disabled={loading}
                    style={{
                        padding: '12px 24px',
                        borderRadius: '8px',
                        border: 'none',
                        background: loading ? '#555' : '#007bff',
                        color: 'white',
                        fontSize: '1rem',
                        cursor: loading ? 'not-allowed' : 'pointer',
                        fontWeight: 'bold'
                    }}
                >
                    {loading ? 'Running Models...' : 'Analyze'}
                </button>
            </form>

            {error && (
                <div style={{ padding: '15px', background: 'rgba(255, 0, 0, 0.1)', border: '1px solid #ff4444', borderRadius: '8px', color: '#ff4444' }}>
                    {error}
                </div>
            )}

            {data && (
                <div className="results-grid" style={{ display: 'flex', flexDirection: 'column', gap: '30px' }}>

                    {/* Top Stats Cards */}
                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '20px' }}>
                        <div style={cardStyle}>
                            <h3 style={labelStyle}>Current Price</h3>
                            <div style={valueStyle}>${data.current_price?.toFixed(2)}</div>
                        </div>
                        <div style={cardStyle}>
                            <h3 style={labelStyle}>Market Regime</h3>
                            <div style={{ ...valueStyle, color: getRegimeColor(data.regime) }}>{data.regime}</div>
                        </div>
                        <div style={cardStyle}>
                            <h3 style={labelStyle}>Analyst Verdict</h3>
                            <div style={valueStyle}>{getVerdict(data.forecasts)}</div>
                        </div>
                    </div>

                    {/* Forecast Table */}
                    <div style={cardStyle}>
                        <h3 style={{ ...labelStyle, marginBottom: '15px' }}>🚀 Multi-Horizon Forecasts</h3>
                        <div style={{ overflowX: 'auto' }}>
                            <table style={{ width: '100%', borderCollapse: 'collapse', textAlign: 'left' }}>
                                <thead>
                                    <tr style={{ borderBottom: '1px solid #444', color: '#888' }}>
                                        <th style={thStyle}>Horizon</th>
                                        <th style={thStyle}>ML Forecast</th>
                                        <th style={thStyle}>Simulation P50</th>
                                        <th style={thStyle}>Risk Assessment</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.forecasts?.map((f) => {
                                        // UI Logic: Identify Derived Horizons
                                        const isDerived = ![10, 100].includes(f.horizon);
                                        const val = f.ml_forecast_pct;

                                        return (
                                            <tr key={f.horizon} style={{ borderBottom: '1px solid #2a2a2a' }}>
                                                <td style={tdStyle}>
                                                    {f.horizon} Days
                                                    {isDerived && <span style={{ fontSize: '0.8em', color: '#888', marginLeft: '6px', fontStyle: 'italic' }}>(Derived)</span>}
                                                </td>
                                                <td style={{ ...tdStyle, color: val != null ? (val >= 0 ? '#4caf50' : '#f44336') : '#888', fontWeight: 'bold' }}>
                                                    {val != null ? `${val > 0 ? '+' : ''}${val.toFixed(2)}%` : '--'}
                                                </td>
                                                <td style={tdStyle}>
                                                    ${f.mc_p50_price?.toFixed(2)}
                                                </td>
                                                <td style={tdStyle}>
                                                    <span style={{
                                                        padding: '4px 8px',
                                                        borderRadius: '4px',
                                                        background: f.risk_assessment.includes('High Upside') ? 'rgba(76, 175, 80, 0.2)' :
                                                            f.risk_assessment.includes('Downside') ? 'rgba(244, 67, 54, 0.2)' : 'rgba(255, 255, 255, 0.1)',
                                                        color: f.risk_assessment.includes('High Upside') ? '#81c784' :
                                                            f.risk_assessment.includes('Downside') ? '#e57373' : '#ccc',
                                                        fontSize: '0.9rem'
                                                    }}>
                                                        {f.risk_assessment}
                                                    </span>
                                                </td>
                                            </tr>
                                        )
                                    })}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    {/* Chart Section */}
                    {data.history && (
                        <div style={cardStyle}>
                            <h3 style={labelStyle}>Recent Price Action</h3>
                            <div style={{ height: '300px', marginTop: '20px' }}>
                                <ResponsiveContainer width="100%" height="100%">
                                    <LineChart data={data.history}>
                                        <CartesianGrid strokeDasharray="3 3" stroke="#333" />
                                        <XAxis dataKey="date" stroke="#666" />
                                        <YAxis domain={['auto', 'auto']} stroke="#666" />
                                        <Tooltip
                                            contentStyle={{ backgroundColor: '#222', border: '1px solid #444' }}
                                            itemStyle={{ color: '#fff' }}
                                        />
                                        <Line type="monotone" dataKey="price" stroke="#007bff" strokeWidth={2} dot={false} />
                                    </LineChart>
                                </ResponsiveContainer>
                            </div>
                        </div>
                    )}

                </div>
            )}
        </div>
    );
};

// Styles
const cardStyle = {
    background: '#1a1a1a',
    padding: '20px',
    borderRadius: '12px',
    border: '1px solid #333',
    boxShadow: '0 4px 6px rgba(0,0,0,0.3)'
};

const labelStyle = {
    color: '#888',
    fontSize: '0.9rem',
    marginBottom: '5px',
    textTransform: 'uppercase',
    letterSpacing: '1px'
};

const valueStyle = {
    color: '#fff',
    fontSize: '1.8rem',
    fontWeight: 'bold'
};

const thStyle = {
    padding: '12px',
    fontWeight: 'normal',
    fontSize: '0.9rem'
};

const tdStyle = {
    padding: '12px',
    fontSize: '1rem'
};

const getRegimeColor = (regime) => {
    if (!regime) return '#fff';
    if (regime.includes('Bull')) return '#4caf50';
    if (regime.includes('Bear')) return '#f44336';
    return '#ff9800';
};

const getVerdict = (forecasts) => {
    if (!forecasts || forecasts.length === 0) return 'N/A';
    // Simple logic: check 100d forecast
    const f100 = forecasts.find(f => f.horizon === 100);
    if (!f100) return 'Neutral';
    if (f100.ml_forecast_pct > 15) return 'Strong Buy';
    if (f100.ml_forecast_pct > 5) return 'Buy';
    if (f100.ml_forecast_pct < -15) return 'Strong Sell';
    if (f100.ml_forecast_pct < -5) return 'Sell';
    return 'Hold';
};

export default DeepDiveAnalysis;
