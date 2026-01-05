import React, { useState, useEffect } from 'react';
import axios from 'axios';
import './AdvancedAnalytics.css';

const AdvancedAnalytics = ({ symbol, onClose }) => {
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

    useEffect(() => {
        if (symbol) {
            fetchData();
        }
    }, [symbol]);

    const fetchData = async () => {
        setLoading(true);
        setError(null);
        try {
            const res = await axios.get(`${API_URL}/analytics/advanced/${symbol}`);
            setData(res.data);
        } catch (err) {
            setError(err.response?.data?.detail || "Failed to load advanced analytics.");
        } finally {
            setLoading(false);
        }
    };

    if (loading) return <div className="aa-loading">Loading Deep Dive for {symbol}...</div>;
    if (error) return <div className="aa-error">Error: {error}</div>;
    if (!data) return null;

    // Helper for heat map color
    const getProbColor = (prob) => {
        const p = parseFloat(prob);
        if (p > 0.7) return '#4caf50'; // Strong
        if (p > 0.4) return '#ffeb3b'; // Med
        return '#f44336'; // Low (or high switch prob? context matters)
    };

    return (
        <div className="aa-panel">
            <div className="aa-header">
                <h3>High-Value Analytics: {symbol}</h3>
                <button onClick={onClose} className="aa-close">×</button>
            </div>

            <div className="aa-grid">
                {/* 1. Regime Profile */}
                <div className="aa-card">
                    <h4>Regime Profile</h4>
                    <div className="aa-metric-row">
                        <span className="label">Current State:</span>
                        <span className={`value badge ${data.regime.includes('Bull') || data.regime.includes('Up') ? 'badge-green' : 'badge-red'}`}>
                            {data.regime}
                        </span>
                    </div>
                    <div className="aa-metric-row">
                        <span className="label">Duration (Stickiness):</span>
                        <span className="value">{data.regime_duration_days} days</span>
                    </div>
                    <div className="aa-metric-desc">
                        {data.regime_duration_days > 20 ? "Regime is entrenched (High Persistence)." : "Regime is fresh/unstable."}
                    </div>
                </div>

                {/* 2. Volatility Structure */}
                <div className="aa-card">
                    <h4>Volatility Structure</h4>
                    <div className="aa-metric-row">
                        <span className="label">Trend:</span>
                        <span className={`value ${data.volatility_trend === 'Rising' ? 'text-red' : 'text-green'}`}>
                            {data.volatility_trend}
                        </span>
                    </div>
                    <div className="aa-metric-desc">
                        {data.volatility_trend === 'Rising'
                            ? "Risk is increasing. Caution advised."
                            : "Volatility is compressing or falling."}
                    </div>
                </div>

                {/* 3. Market Breadth (Conditional) */}
                {data.breadth && Object.keys(data.breadth).length > 0 && (
                    <div className="aa-card">
                        <h4>Market Health (Breadth)</h4>
                        <div className="aa-metric-row">
                            <span className="label">% &gt; SMA50:</span>
                            <span className="value">{data.breadth.percent_above_sma_50}%</span>
                        </div>
                        <div className="aa-metric-row">
                            <span className="label">% Uptrend (20d):</span>
                            <span className="value">{data.breadth.percent_uptrend_20d}%</span>
                        </div>
                        <div className="aa-metric-row">
                            <span className="label">Agreement:</span>
                            <span className="value">{data.breadth.agreement}</span>
                        </div>
                    </div>
                )}
            </div>

            {/* 4. Transition Matrix */}
            <div className="aa-section">
                <h4>Regime Transition Matrix (Next Day Probabilities)</h4>
                <div className="aa-matrix-container">
                    <table className="aa-matrix">
                        <thead>
                            <tr>
                                <th>From \ To</th>
                                {Object.keys(data.transition_matrix).map(k => <th key={k}>{k}</th>)}
                            </tr>
                        </thead>
                        <tbody>
                            {Object.entries(data.transition_matrix).map(([fromState, transitions]) => (
                                <tr key={fromState} className={fromState === data.regime ? 'current-row' : ''}>
                                    <td className="row-header">
                                        {fromState}
                                        {fromState === data.regime && <span className="current-badge">(Current)</span>}
                                    </td>
                                    {Object.keys(data.transition_matrix).map(toState => {
                                        const prob = transitions[toState] || 0;
                                        const pct = (prob * 100).toFixed(1) + '%';
                                        // Highlight diagonal (persistence) vs off-diagonal (switch)
                                        const isPersistence = fromState === toState;
                                        return (
                                            <td key={toState} style={{ opacity: Math.max(0.2, prob) }}>
                                                <div className="prob-cell">
                                                    <span className="prob-val">{pct}</span>
                                                </div>
                                            </td>
                                        );
                                    })}
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            </div>
        </div>
    );
};

export default AdvancedAnalytics;
