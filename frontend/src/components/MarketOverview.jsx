import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_URL from '../config';

const MarketOverview = () => {
    const [overview, setOverview] = useState([]);
    const [loading, setLoading] = useState(false);
    const [selectedDate, setSelectedDate] = useState(new Date().toISOString().split('T')[0]);

    const fetchOverview = async (date) => {
        setLoading(true);
        try {
            const url = date
                ? `${API_URL}/market/overview?date=${date}`
                : `${API_URL}/market/overview`;
            const response = await axios.get(url);
            setOverview(response.data.overview);
        } catch (err) {
            console.error(err);
        } finally {
            setLoading(false);
        }
    };

    useEffect(() => {
        fetchOverview(selectedDate);
    }, [selectedDate]);

    const handleDateChange = (e) => {
        setSelectedDate(e.target.value);
    };

    const changeDate = (days) => {
        const date = new Date(selectedDate);
        date.setDate(date.getDate() + days);
        setSelectedDate(date.toISOString().split('T')[0]);
    };

    return (
        <div className="market-overview">
            <div className="overview-header">
                <h2>Top 50 S&P 500 Overview</h2>
                <div className="date-controls">
                    <button onClick={() => changeDate(-1)}>← Prev Day</button>
                    <input
                        type="date"
                        value={selectedDate}
                        onChange={handleDateChange}
                        className="date-picker"
                    />
                    <button onClick={() => changeDate(1)}>Next Day →</button>
                    <button onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}>Today</button>
                </div>
            </div>

            {loading ? <p>Loading (this may take a moment)...</p> : (
                <div className="table-container" style={{ overflowX: 'auto' }}>
                    <table className="overview-table">
                        <thead>
                            <tr>
                                <th style={{ position: 'sticky', left: 0, zIndex: 1, backgroundColor: '#333' }}>Symbol</th>
                                <th>Date</th>
                                <th>Close</th>
                                <th>10d %</th>
                                <th>10d Price</th>
                                <th>100d %</th>
                                <th>100d Price</th>
                                <th>1yr %</th>
                                <th>1yr Price</th>
                                <th>1.5yr %</th>
                                <th>1.5yr Price</th>
                                <th>2yr %</th>
                                <th>2yr Price</th>
                            </tr>
                        </thead>
                        <tbody>
                            {overview.map((item) => (
                                <tr key={item.symbol}>
                                    <td className="symbol-cell" style={{ position: 'sticky', left: 0, zIndex: 1, backgroundColor: '#2a2a2a' }}>{item.symbol}</td>
                                    <td>{item.date}</td>
                                    <td>${item.today_close.toFixed(2)}</td>

                                    <td className={item.forecast_10d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                        {item.forecast_10d_pct ? `${item.forecast_10d_pct > 0 ? '+' : ''}${item.forecast_10d_pct.toFixed(2)}%` : 'N/A'}
                                    </td>
                                    <td>${item.forecast_10d_price ? item.forecast_10d_price.toFixed(2) : 'N/A'}</td>

                                    <td className={item.forecast_100d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                        {item.forecast_100d_pct ? `${item.forecast_100d_pct > 0 ? '+' : ''}${item.forecast_100d_pct.toFixed(2)}%` : 'N/A'}
                                    </td>
                                    <td>${item.forecast_100d_price ? item.forecast_100d_price.toFixed(2) : 'N/A'}</td>

                                    <td className={item.forecast_365d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                        {item.forecast_365d_pct ? `${item.forecast_365d_pct > 0 ? '+' : ''}${item.forecast_365d_pct.toFixed(2)}%` : 'N/A'}
                                    </td>
                                    <td>${item.forecast_365d_price ? item.forecast_365d_price.toFixed(2) : 'N/A'}</td>

                                    <td className={item.forecast_547d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                        {item.forecast_547d_pct ? `${item.forecast_547d_pct > 0 ? '+' : ''}${item.forecast_547d_pct.toFixed(2)}%` : 'N/A'}
                                    </td>
                                    <td>${item.forecast_547d_price ? item.forecast_547d_price.toFixed(2) : 'N/A'}</td>

                                    <td className={item.forecast_730d_pct > 0 ? 'bullish-text' : 'bearish-text'}>
                                        {item.forecast_730d_pct ? `${item.forecast_730d_pct > 0 ? '+' : ''}${item.forecast_730d_pct.toFixed(2)}%` : 'N/A'}
                                    </td>
                                    <td>${item.forecast_730d_price ? item.forecast_730d_price.toFixed(2) : 'N/A'}</td>
                                </tr>
                            ))}
                        </tbody>
                    </table>
                </div>
            )}
        </div>
    );
};

export default MarketOverview;
