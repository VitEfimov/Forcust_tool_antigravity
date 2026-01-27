import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_URL from '../config';
import OverviewTable from './OverviewTable';

const MarketOverview = () => {
    const [history, setHistory] = useState([]);
    const [selectedSnapshot, setSelectedSnapshot] = useState(null);
    const [overviewData, setOverviewData] = useState([]);
    const [loading, setLoading] = useState(false);

    // Initial Load
    useEffect(() => {
        const loadHistory = async () => {
            setLoading(true);
            try {
                // 1. Fetch Latest (default)
                const latestRes = await axios.get(`${API_URL}/market/overview`);
                setOverviewData(latestRes.data.overview || []);

                // 2. Fetch History List
                const histRes = await axios.get(`${API_URL}/market/history?limit=10`);
                setHistory(histRes.data.history || []);
            } catch (err) {
                console.error("Failed to load market data", err);
            } finally {
                setLoading(false);
            }
        };
        loadHistory();
    }, []);

    // Handle Snapshot Selection
    const handleSnapshotChange = (e) => {
        const ts = e.target.value;
        if (ts === 'latest') {
            setSelectedSnapshot(null);
            // Re-fetch latest to be safe or just use cached if we stored it? 
            // For simplicity, let's just trigger a re-fetch or reload page logic?
            // Better: just fetch latest again.
            setLoading(true);
            axios.get(`${API_URL}/market/overview`).then(res => {
                setOverviewData(res.data.overview || []);
                setLoading(false);
            });
        } else {
            const snap = history.find(h => h.timestamp === ts);
            if (snap && snap.data) {
                setSelectedSnapshot(ts);
                setOverviewData(snap.data.overview || []);
            }
        }
    };

    // Split Data into Indices and Stocks
    // Indices usually start with ^ or are in a known list
    const isIndex = (symbol) => symbol.startsWith('^') || ['HYG', 'LQD', 'DX-Y.NYB', 'CL=F', 'GC=F'].includes(symbol);

    const indices = overviewData.filter(item => isIndex(item.symbol));
    const stocks = overviewData.filter(item => !isIndex(item.symbol));

    return (
        <div className="market-overview">
            <div className="overview-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '2rem' }}>
                <div>
                    <h2 style={{ margin: 0 }}>🌍 Global Market Overview</h2>
                    <p style={{ color: '#888', margin: '0.5rem 0 0 0' }}>
                        Snapshot of Market Health • Indices • Top 50 Stocks
                    </p>
                </div>

                <div className="controls">
                    <span style={{ marginRight: '1rem', color: '#aaa' }}>Select Snapshot:</span>
                    <select
                        onChange={handleSnapshotChange}
                        style={{ padding: '0.5rem', background: '#222', color: '#fff', border: '1px solid #444', borderRadius: '4px' }}
                        value={selectedSnapshot || 'latest'}
                    >
                        <option value="latest">🔴 Live / Latest (Cached)</option>
                        {history.map((h, i) => (
                            <option key={i} value={h.timestamp}>
                                📅 {new Date(h.timestamp).toLocaleString()}
                            </option>
                        ))}
                    </select>
                </div>
            </div>

            {loading ? <div className="loading">Loading Market Intelligence...</div> : (
                <>
                    {/* 1. Indices Section */}
                    {indices.length > 0 && (
                        <div style={{ marginBottom: '2rem' }}>
                            <h3 style={{ borderBottom: '1px solid #333', paddingBottom: '0.5rem', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                📊 Major Indices & Factors
                            </h3>
                            <div className="indices-grid" style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))', gap: '1rem' }}>
                                {indices.map(idx => (
                                    <div key={idx.symbol} style={{
                                        background: '#1a1a1a', padding: '1rem', borderRadius: '8px', border: '1px solid #333',
                                        display: 'flex', flexDirection: 'column', gap: '0.5rem'
                                    }}>
                                        <div style={{ display: 'flex', justifyContent: 'space-between' }}>
                                            <span style={{ fontWeight: 'bold', fontSize: '1.1rem' }}>{idx.symbol}</span>
                                            <span style={{ color: idx.change_pct >= 0 ? '#4f4' : '#f44' }}>
                                                {idx.change_pct > 0 ? '+' : ''}{idx.change_pct}%
                                            </span>
                                        </div>
                                        <div style={{ fontSize: '1.5rem', fontWeight: 'bold' }}>
                                            ${idx.price?.toLocaleString()}
                                        </div>
                                        <div style={{ fontSize: '0.8rem', color: '#888' }}>
                                            Trend: <span style={{ color: '#fff' }}>{idx.trend_label || 'Neutral'}</span>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* 2. Stocks Section */}
                    <div>
                        <h3 style={{ borderBottom: '1px solid #333', paddingBottom: '0.5rem' }}>
                            🏢 Market Leaders (Top 50)
                        </h3>
                        <OverviewTable data={stocks} />
                    </div>
                </>
            )}
        </div>
    );
};

export default MarketOverview;
