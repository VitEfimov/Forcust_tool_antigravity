import React, { useState, useEffect } from 'react';
import axios from 'axios';
import API_URL from '../config';
import OverviewTable from './OverviewTable';

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
                        max={new Date().toISOString().split('T')[0]}
                        className="date-picker"
                    />
                    <button
                        onClick={() => changeDate(1)}
                        disabled={selectedDate >= new Date().toISOString().split('T')[0]}
                    >
                        Next Day →
                    </button>
                    <button onClick={() => setSelectedDate(new Date().toISOString().split('T')[0])}>Today</button>
                </div>
            </div>

            {loading ? <p>Loading (this may take a moment)...</p> : (
                <OverviewTable data={overview} />
            )}
        </div>
    );
};

export default MarketOverview;
