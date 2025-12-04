import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_URL from '../config';

const Indices = () => {
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);

    useEffect(() => {
        const fetchHistory = async () => {
            setLoading(true);
            try {
                const response = await axios.get(`${API_URL}/indices/history`);
                setHistory(response.data.history);
            } catch (err) {
                console.error(err);
            } finally {
                setLoading(false);
            }
        };
        fetchHistory();
    }, []);

    // Group by date for the "Big Table" view
    // We want rows to be dates, and columns to be (Index, Horizon) tuples? 
    // Or just a flat list of all forecasts?
    // The user asked for: columns: "S&P 500", "NASDAQ", etc.
    // date, forcust, real price

    // Let's organize it as:
    // Date | Index | Horizon | Forecast | Real Price
    // Or maybe a pivot table?
    // "1 more page with big table, columns: S&P 500... date, forcust, real price"
    // This sounds like a table where each row is a Date, and we have columns for each Index?
    // But we have multiple horizons.

    // Let's stick to a flat table for now, but filterable/sortable.
    // Or maybe grouped by Index?

    // Let's try to group by Date and Index.

    return (
        <div className="indices-page">
            <h2>Major Indices History</h2>
            {loading ? <p>Loading...</p> : (
                <div className="table-container">
                    <table className="indices-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Index</th>
                                <th>Horizon</th>
                                <th>Forecast (Log)</th>
                                <th>Start Price</th>
                                <th>Target Date</th>
                                <th>Actual Return</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history.map((row) => (
                                <tr key={row.id}>
                                    <td>{row.date}</td>
                                    <td>{row.symbol}</td>
                                    <td>{row.horizon}d</td>
                                    <td className={row.prediction > 0 ? 'bullish-text' : 'bearish-text'}>
                                        {row.prediction.toFixed(4)}
                                    </td>
                                    <td>{row.start_price ? row.start_price.toFixed(2) : '-'}</td>
                                    <td>{row.target_date}</td>
                                    <td className={row.actual > 0 ? 'bullish-text' : (row.actual < 0 ? 'bearish-text' : '')}>
                                        {row.actual ? row.actual.toFixed(4) : '-'}
                                    </td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default Indices;
