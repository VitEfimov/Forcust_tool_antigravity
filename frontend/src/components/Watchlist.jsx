import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_URL from '../config';
import OverviewTable from './OverviewTable';

const Watchlist = () => {
    const [symbols, setSymbols] = useState([]);
    const [newSymbol, setNewSymbol] = useState('');
    const [overview, setOverview] = useState([]);
    const [loading, setLoading] = useState(false);
    const [adding, setAdding] = useState(false);

    // Fetch watchlist symbols on mount
    useEffect(() => {
        fetchWatchlist();
    }, []);

    // Fetch overview data when symbols change (or manually)
    useEffect(() => {
        if (symbols.length > 0) {
            fetchOverview();
        } else {
            setOverview([]);
        }
    }, [symbols]);

    const fetchWatchlist = async () => {
        try {
            const response = await axios.get(`${API_URL}/watchlist`);
            setSymbols(response.data);
        } catch (err) {
            console.error("Failed to fetch watchlist", err);
        }
    };

    const fetchOverview = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`${API_URL}/watchlist/overview`);
            setOverview(response.data.overview);
        } catch (err) {
            console.error("Failed to fetch overview", err);
        } finally {
            setLoading(false);
        }
    };

    const handleAdd = async (e) => {
        e.preventDefault();
        if (!newSymbol) return;
        setAdding(true);
        try {
            await axios.post(`${API_URL}/watchlist/${newSymbol}`);
            setNewSymbol('');
            fetchWatchlist(); // Refresh list
        } catch (err) {
            alert("Failed to add symbol. It might be invalid or network error.");
        } finally {
            setAdding(false);
        }
    };

    const handleRemove = async (symbol) => {
        try {
            await axios.delete(`${API_URL}/watchlist/${symbol}`);
            fetchWatchlist(); // Refresh list
        } catch (err) {
            console.error("Failed to remove symbol", err);
        }
    };

    return (
        <div className="watchlist-page">
            <div className="overview-header">
                <h2>My Custom Watchlist</h2>
                <div className="watchlist-controls">
                    <form onSubmit={handleAdd} className="add-form">
                        <input
                            type="text"
                            value={newSymbol}
                            onChange={(e) => setNewSymbol(e.target.value.toUpperCase())}
                            placeholder="Add Symbol (e.g. NVDA)"
                        />
                        <button type="submit" disabled={adding}>
                            {adding ? 'Adding...' : 'Add'}
                        </button>
                    </form>
                </div>
            </div>

            <div className="tags-container" style={{ marginBottom: '1rem', display: 'flex', flexWrap: 'wrap', gap: '0.5rem' }}>
                {symbols.map(sym => (
                    <span key={sym} className="symbol-tag" style={{
                        background: '#333', padding: '5px 10px', borderRadius: '15px', display: 'flex', alignItems: 'center', gap: '5px'
                    }}>
                        {sym}
                        <button
                            onClick={() => handleRemove(sym)}
                            style={{ background: 'none', border: 'none', color: '#ff4444', cursor: 'pointer', fontSize: '1.2em', padding: 0 }}
                        >
                            ×
                        </button>
                    </span>
                ))}
            </div>

            {loading ? <p>Loading data for your watchlist...</p> : (
                <>
                    {symbols.length === 0 ? (
                        <p>Your watchlist is empty. Add symbols above to track them.</p>
                    ) : (
                        <OverviewTable data={overview} />
                    )}
                </>
            )}
        </div>
    );
};

export default Watchlist;
