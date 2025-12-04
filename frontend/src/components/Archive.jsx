import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer } from 'recharts';

const Archive = () => {
    const [symbol, setSymbol] = useState('SPY');
    const [history, setHistory] = useState([]);
    const [loading, setLoading] = useState(false);

    const fetchHistory = async () => {
        setLoading(true);
        try {
            const response = await axios.get(`http://localhost:8000/archive/${symbol}`);
            setHistory(response.data.history);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchHistory();
    }, [symbol]);

    return (
        <div className="archive-page">
            <h2>Forecast Archive: {symbol}</h2>
            <div className="controls">
                <input
                    value={symbol}
                    onChange={(e) => setSymbol(e.target.value.toUpperCase())}
                    placeholder="Symbol"
                />
                <button onClick={fetchHistory}>Load</button>
            </div>

            {loading ? <p>Loading...</p> : (
                <div className="history-table-container">
                    <table className="history-table">
                        <thead>
                            <tr>
                                <th>Date</th>
                                <th>Horizon</th>
                                <th>Prediction (Log)</th>
                                <th>Target Date</th>
                                <th>Actual</th>
                            </tr>
                        </thead>
                        <tbody>
                            {history.map((row) => (
                                <tr key={row.id}>
                                    <td>{row.date}</td>
                                    <td>{row.horizon}d</td>
                                    <td>{row.prediction.toFixed(4)}</td>
                                    <td>{row.target_date}</td>
                                    <td>{row.actual ? row.actual.toFixed(4) : '-'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default Archive;
