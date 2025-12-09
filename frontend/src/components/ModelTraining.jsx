import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_URL from '../config';

const ModelTraining = () => {
    const [symbol, setSymbol] = useState('SPY');
    const [indices, setIndices] = useState([]);
    const [selectedIndices, setSelectedIndices] = useState(['^VIX']); // Default VIX
    const [loading, setLoading] = useState(false);
    const [results, setResults] = useState(null);

    useEffect(() => {
        fetchIndices();
    }, []);

    const fetchIndices = async () => {
        try {
            const res = await axios.get(`${API_URL}/indices`);
            setIndices(res.data.indices);
        } catch (err) {
            console.error("Failed to fetch indices", err);
        }
    };

    const toggleIndex = (idxSymbol) => {
        if (selectedIndices.includes(idxSymbol)) {
            setSelectedIndices(selectedIndices.filter(s => s !== idxSymbol));
        } else {
            setSelectedIndices([...selectedIndices, idxSymbol]);
        }
    };

    const toggleSelectAll = () => {
        if (selectedIndices.length === indices.length) {
            setSelectedIndices([]);
        } else {
            setSelectedIndices(indices.map(i => i.symbol));
        }
    };

    const handleTrain = async (e) => {
        e.preventDefault();
        setLoading(true);
        setResults(null);
        try {
            const res = await axios.post(`${API_URL}/models/train`, {
                symbol: symbol,
                indices: selectedIndices,
                horizons: [10, 30, 100, 365]
            });
            setResults(res.data);
        } catch (err) {
            alert("Training failed: " + (err.response?.data?.detail || err.message));
        } finally {
            setLoading(false);
        }
    };

    return (
        <div className="model-training">
            <header className="header">
                <h1>ML Model Lab</h1>
                <p>Train custom forecast models with exogenous market variables.</p>
            </header>

            <div className="content">
                <div className="controls-card" style={{ background: '#1e1e1e', padding: '1.5rem', borderRadius: '12px' }}>
                    <form onSubmit={handleTrain}>
                        <div style={{ marginBottom: '1rem' }}>
                            <label>Target Symbol</label>
                            <input
                                type="text"
                                value={symbol}
                                onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                                style={{ display: 'block', marginTop: '0.5rem', padding: '0.5rem', width: '200px' }}
                            />
                        </div>

                        <div style={{ marginBottom: '1rem' }}>
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                                <label>Training Features (Indices)</label>
                                <button
                                    type="button"
                                    onClick={toggleSelectAll}
                                    style={{
                                        background: 'none',
                                        border: 'none',
                                        color: '#4dabf5',
                                        cursor: 'pointer',
                                        fontSize: '0.9rem',
                                        textDecoration: 'underline'
                                    }}
                                >
                                    {selectedIndices.length === indices.length ? 'Clear All' : 'Select All'}
                                </button>
                            </div>
                            <div className="indices-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '0.5rem', marginTop: '0.5rem' }}>
                                {indices.map(idx => (
                                    <div key={idx.symbol}
                                        onClick={() => toggleIndex(idx.symbol)}
                                        style={{
                                            padding: '0.5rem',
                                            background: selectedIndices.includes(idx.symbol) ? '#00d4ff' : '#333',
                                            color: selectedIndices.includes(idx.symbol) ? '#000' : '#fff',
                                            borderRadius: '4px',
                                            cursor: 'pointer',
                                            fontWeight: selectedIndices.includes(idx.symbol) ? 'bold' : 'normal'
                                        }}>
                                        {idx.name} ({idx.symbol})
                                    </div>
                                ))}
                            </div>
                        </div>

                        <button type="submit" disabled={loading} style={{
                            padding: '0.8rem 2rem',
                            background: '#4CAF50',
                            color: 'white',
                            border: 'none',
                            borderRadius: '4px',
                            cursor: 'pointer',
                            fontSize: '1rem',
                            fontWeight: 'bold'
                        }}>
                            {loading ? 'Training Models...' : 'Start Training Sequence'}
                        </button>
                    </form>
                </div>

                {/* Results */}
                {results && (
                    <div className="results-card" style={{ marginTop: '2rem' }}>
                        <h2>Training Results: {results.symbol}</h2>
                        <div style={{ display: 'flex', gap: '1rem', flexWrap: 'wrap' }}>
                            {Object.entries(results.results).map(([horizon, res]) => (
                                <div key={horizon} style={{ background: '#2a2a2a', padding: '1rem', borderRadius: '8px', minWidth: '200px' }}>
                                    <h3>Horizon: {horizon}</h3>
                                    {res.metrics ? (
                                        <div style={{ marginTop: '0.5rem' }}>
                                            {(() => {
                                                const mae = res.metrics.mae;
                                                const pct = (mae * 100).toFixed(2);
                                                let quality = "Low";
                                                let color = "#ff4d4d";
                                                let desc = "High uncertainty";

                                                if (mae < 0.05) { quality = "Excellent"; color = "#4CAF50"; desc = "Very precise"; }
                                                else if (mae < 0.10) { quality = "Good"; color = "#82ca9d"; desc = "Reliable"; }
                                                else if (mae < 0.20) { quality = "Fair"; color = "#ffd700"; desc = "Use caution"; }

                                                return (
                                                    <div>
                                                        <div style={{ fontSize: '1.2rem', color: color, fontWeight: 'bold' }}>{quality} fit</div>
                                                        <div style={{ color: '#aaa', fontSize: '0.9rem' }}>Avg Error: ±{pct}%</div>
                                                        <div style={{ fontSize: '0.8rem', fontStyle: 'italic', marginTop: '4px' }}>"{desc}"</div>
                                                        <hr style={{ borderColor: '#444', margin: '8px 0' }} />
                                                        <div style={{ fontSize: '0.8rem', color: '#888' }}>
                                                            Raw RMSE: {res.metrics.rmse.toFixed(4)} <br />
                                                            Raw MAE: {res.metrics.mae.toFixed(4)}
                                                        </div>
                                                        {res.metrics.ci_95 && (
                                                            <div style={{ fontSize: '0.8rem', color: '#888', marginTop: '4px' }}>
                                                                95% CI: ±{(res.metrics.ci_95 * 100).toFixed(1)}%
                                                            </div>
                                                        )}
                                                    </div>
                                                );
                                            })()}
                                        </div>
                                    ) : (
                                        <p>{res}</p>
                                    )}
                                </div>
                            ))}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default ModelTraining;
