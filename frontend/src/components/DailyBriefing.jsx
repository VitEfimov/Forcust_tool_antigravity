import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const DailyBriefing = () => {
    const [report, setReport] = useState({ content: '', filename: '' });
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState(null);

    useEffect(() => {
        const fetchReport = async () => {
            try {
                const res = await axios.get(`${API_URL}/system/logs`);
                setReport(res.data);
                setError(null);
            } catch (err) {
                console.error("Failed to load briefing", err);
                setError("Failed to load the latest briefing.");
            } finally {
                setLoading(false);
            }
        };

        fetchReport();
    }, []);

    if (loading) {
        return (
            <div className="dashboard" style={{ display: 'flex', justifyContent: 'center', alignItems: 'center', height: '50vh' }}>
                <div className="animate-spin" style={{ fontSize: '2rem' }}>↻</div>
            </div>
        );
    }

    return (
        <div className="dashboard">
            <header className="header" style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem' }}>📑 Daily Intelligence Briefing</h1>
                <p style={{ color: '#888' }}>
                    Automated market analysis and strategic outlook
                </p>
                {report.filename && (
                    <div style={{ marginTop: '0.5rem' }}>
                        <span style={{
                            background: '#222',
                            color: '#aaa',
                            padding: '4px 8px',
                            borderRadius: '4px',
                            fontSize: '0.8rem',
                            fontFamily: 'monospace'
                        }}>
                            File: {report.filename}
                        </span>
                    </div>
                )}
            </header>

            <div className="content">
                {error ? (
                    <div className="card" style={{ padding: '2rem', textAlign: 'center', color: '#ff4444' }}>
                        {error}
                    </div>
                ) : (
                    <div className="card" style={{ padding: '0', overflow: 'hidden' }}>
                        <div style={{
                            background: '#1a1a1a',
                            padding: '2rem',
                            fontFamily: 'monospace',
                            whiteSpace: 'pre-wrap',
                            color: '#e0e0e0',
                            fontSize: '1rem',
                            lineHeight: '1.6',
                            borderLeft: '4px solid #00d4ff'
                        }}>
                            {report.content || "No briefing available."}
                        </div>
                    </div>
                )}
            </div>
        </div>
    );
};

export default DailyBriefing;
