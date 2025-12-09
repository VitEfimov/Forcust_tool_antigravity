import React, { useState, useEffect } from 'react';
import axios from 'axios';
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
                        <p>Current Price: ${data.current_price?.toFixed(2)}</p>
                        <p>Regime: <span style={{
                            color: data.regime?.includes('Low') ? '#66ff66' : '#ff6666',
                            fontWeight: 'bold'
                        }}>{data.regime || 'Unknown'}</span></p>
                    </div>

                    <div className="forecasts-section" style={{ marginTop: '2rem' }}>
                        <h3>📊 Multi-Horizon Forecast</h3>
                        <div className="table-container" style={{ overflowX: 'auto' }}>
                            <table className="overview-table" style={{ width: '100%', borderCollapse: 'collapse' }}>
                                <thead>
                                    <tr style={{ borderBottom: '2px solid #333' }}>
                                        <th style={{ textAlign: 'left', padding: '0.8rem' }}>Horizon</th>
                                        <th style={{ textAlign: 'right', padding: '0.8rem' }}>ML Forecast</th>
                                        <th style={{ textAlign: 'right', padding: '0.8rem' }}>MC P10 (Bear)</th>
                                        <th style={{ textAlign: 'right', padding: '0.8rem' }}>MC P50 (Base)</th>
                                        <th style={{ textAlign: 'right', padding: '0.8rem' }}>MC P90 (Bull)</th>
                                        <th style={{ textAlign: 'left', padding: '0.8rem' }}>Risk Assessment</th>
                                    </tr>
                                </thead>
                                <tbody>
                                    {data.forecasts && data.forecasts.map((f) => (
                                        <tr key={f.horizon} style={{ borderBottom: '1px solid #2a2a2a' }}>
                                            <td style={{ padding: '0.8rem', fontWeight: 'bold' }}>{f.horizon}d</td>
                                            <td style={{
                                                padding: '0.8rem',
                                                textAlign: 'right',
                                                color: f.ml_forecast_pct > 0 ? '#66ff66' : f.ml_forecast_pct < 0 ? '#ff6666' : '#aaa'
                                            }}>
                                                {f.ml_forecast_pct > 0 ? '+' : ''}{f.ml_forecast_pct?.toFixed(2)}%
                                            </td>
                                            <td style={{
                                                padding: '0.8rem',
                                                textAlign: 'right',
                                                color: '#ff6666'
                                            }}>
                                                {f.mc_p10_pct > 0 ? '+' : ''}{f.mc_p10_pct?.toFixed(2)}%
                                            </td>
                                            <td style={{
                                                padding: '0.8rem',
                                                textAlign: 'right',
                                                color: f.mc_p50_pct > 0 ? '#66ff66' : f.mc_p50_pct < 0 ? '#ff6666' : '#aaa'
                                            }}>
                                                {f.mc_p50_pct > 0 ? '+' : ''}{f.mc_p50_pct?.toFixed(2)}%
                                            </td>
                                            <td style={{
                                                padding: '0.8rem',
                                                textAlign: 'right',
                                                color: '#66ff66'
                                            }}>
                                                {f.mc_p90_pct > 0 ? '+' : ''}{f.mc_p90_pct?.toFixed(2)}%
                                            </td>
                                            <td style={{
                                                padding: '0.8rem',
                                                color: f.risk_assessment?.includes('Upside') ? '#66ff66' :
                                                    f.risk_assessment?.includes('Downside') ? '#ff6666' : '#888'
                                            }}>
                                                {f.risk_assessment}
                                            </td>
                                        </tr>
                                    ))}
                                </tbody>
                            </table>
                        </div>
                    </div>

                    <div className="history-section" style={{ marginTop: '2rem' }}>
                        <h3>📈 Recent Price History</h3>
                        <div style={{
                            display: 'grid',
                            gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
                            gap: '0.5rem',
                            maxHeight: '200px',
                            overflowY: 'auto'
                        }}>
                            {data.history && data.history.slice(-10).map((h, i) => (
                                <div key={i} style={{
                                    background: '#1a1a1a',
                                    padding: '0.5rem',
                                    borderRadius: '4px',
                                    textAlign: 'center'
                                }}>
                                    <div style={{ fontSize: '0.8rem', color: '#888' }}>{h.date}</div>
                                    <div style={{ fontWeight: 'bold' }}>${h.price?.toFixed(2)}</div>
                                </div>
                            ))}
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default Dashboard;
