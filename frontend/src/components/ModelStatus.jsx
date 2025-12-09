
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ModelStatus = () => {
    const [status, setStatus] = useState(null);
    const [logs, setLogs] = useState({ content: 'Loading logs...' });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        const fetchData = async () => {
            try {
                const [statusRes, logsRes] = await Promise.all([
                    axios.get(`${API_URL}/system/status`),
                    axios.get(`${API_URL}/system/logs`)
                ]);
                setStatus(statusRes.data);
                setLogs(logsRes.data);
            } catch (err) {
                console.error("Failed to fetch system status", err);
                setStatus({ error: "Failed to connect to backend." });
            } finally {
                setLoading(false);
            }
        };

        fetchData();
        const interval = setInterval(fetchData, 30000); // 30s Poll
        return () => clearInterval(interval);
    }, []);

    const getStatusColor = (state) => {
        if (!state) return '#ffff88';
        const s = state.toLowerCase();
        if (s === 'online' || s === 'connected' || s === 'success') return '#44ff44';
        if (s.includes('running')) return '#00d4ff'; // Blue for running
        if (s === 'error' || s.includes('error') || s.includes('fail')) return '#ff4444';
        return '#ffff88';
    };

    if (loading) return <div className="dashboard"><h2>Loading Mission Control...</h2></div>;

    // Transform Tasks Object to Array
    const tasks = status?.tasks ? Object.entries(status.tasks).map(([name, data]) => ({ name, ...data })) : [];

    return (
        <div className="dashboard">
            <header className="header" style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem' }}>🚀 System Mission Control</h1>
                <p style={{ color: '#888' }}>
                    Heartbeat Monitoring • Autonomic Task tracking • Intelligence Reports
                </p>
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem' }}>
                    <div style={{ background: '#111', padding: '0.5rem 1rem', borderRadius: '4px', border: `1px solid ${getStatusColor(status?.api)}` }}>
                        API: {status?.api?.toUpperCase()}
                    </div>
                    <div style={{ background: '#111', padding: '0.5rem 1rem', borderRadius: '4px', border: `1px solid ${getStatusColor(status?.database)}` }}>
                        DB: {status?.database?.toUpperCase()}
                    </div>
                    <div style={{ background: '#111', padding: '0.5rem 1rem', borderRadius: '4px', color: '#888' }}>
                        Last Updated: {new Date().toLocaleTimeString()}
                    </div>
                </div>
            </header>

            <div className="content">

                {/* 1. Task Health Table */}
                <div className="card" style={{ marginBottom: '2rem', padding: '0' }}>
                    <div style={{ padding: '1rem 1.5rem', borderBottom: '1px solid #333' }}>
                        <h3 style={{ margin: 0 }}>Autonomic Task Heartbeats</h3>
                    </div>
                    <div className="table-container">
                        <table className="indices-table">
                            <thead>
                                <tr>
                                    <th>Task Name</th>
                                    <th>Status</th>
                                    <th>Last Run</th>
                                    <th>Duration</th>
                                    <th>Metrics / Details</th>
                                </tr>
                            </thead>
                            <tbody>
                                {tasks.length === 0 && (
                                    <tr><td colSpan="5" style={{ textAlign: 'center', color: '#888' }}>No tasks have reported yet.</td></tr>
                                )}
                                {tasks.map((task, i) => (
                                    <tr key={i}>
                                        <td style={{ fontWeight: 'bold' }}>{task.name}</td>
                                        <td>
                                            <span style={{
                                                color: getStatusColor(task.status),
                                                background: `${getStatusColor(task.status)}22`,
                                                padding: '2px 8px',
                                                borderRadius: '4px',
                                                fontSize: '0.85rem'
                                            }}>
                                                {task.status?.toUpperCase()}
                                            </span>
                                        </td>
                                        <td>{new Date(task.timestamp).toLocaleString()}</td>
                                        <td>{task.duration_sec ? `${task.duration_sec}s` : '-'}</td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '0.9rem', color: '#aaa' }}>
                                            {JSON.stringify(task.details || {}).substring(0, 60)}...
                                        </td>
                                    </tr>
                                ))}
                            </tbody>
                        </table>
                    </div>
                </div>

                {/* 2. Logs Viewer */}
                <div style={{ background: '#1e1e1e', padding: '1rem', borderRadius: '12px', border: '1px solid #333' }}>
                    <div
                        onClick={() => setLogs(p => ({ ...p, expanded: !p.expanded }))}
                        style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', cursor: 'pointer' }}
                    >
                        <h2 style={{ margin: 0, fontSize: '1.2rem' }}>
                            {logs.expanded ? '▼' : '▶'} 📄 Latest Intelligence Briefing
                        </h2>
                        {logs.filename && <span style={{ color: '#888', fontFamily: 'monospace', background: '#222', padding: '2px 6px', borderRadius: '4px' }}>{logs.filename}</span>}
                    </div>

                    {logs.expanded && (
                        <div style={{
                            background: '#111',
                            padding: '1.5rem',
                            marginTop: '1rem',
                            borderRadius: '8px',
                            fontFamily: 'monospace',
                            whiteSpace: 'pre-wrap',
                            color: '#ddd',
                            border: '1px solid #333',
                            maxHeight: '600px',
                            overflowY: 'auto',
                            fontSize: '0.9rem',
                            lineHeight: '1.5'
                        }}>
                            {logs.content}
                        </div>
                    )}
                </div>
            </div>
        </div>
    );
};

export default ModelStatus;
