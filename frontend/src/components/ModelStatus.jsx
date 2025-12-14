
import React, { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ModelStatus = () => {
    const [status, setStatus] = useState(null);
    const [logs, setLogs] = useState({ content: 'Loading logs...' });
    const [loading, setLoading] = useState(true);
    const [expandedTask, setExpandedTask] = useState(null);

    useEffect(() => {
        const fetchStatus = async () => {
            try {
                // Timeout: 120s (2 mins) for server wakeup
                const config = { timeout: 120000 };

                // Fetch Status & Heartbeats
                const [statusRes, heartbeatsRes] = await Promise.all([
                    axios.get(`${API_URL}/system/status`, config),
                    axios.get(`${API_URL}/system/heartbeats?limit=50`, config)
                ]);

                // Merge status summary with full events list
                setStatus({ ...statusRes.data, tasks: heartbeatsRes.data.events });
            } catch (err) {
                console.error("Failed to fetch system status", err);
                setStatus({ error: "Failed to connect to backend (Timeout or Error)." });
            } finally {
                setLoading(false);
            }
        };

        fetchStatus();
        const interval = setInterval(fetchStatus, 30000); // 30s Poll for Status
        return () => clearInterval(interval);
    }, []);

    // Separate Effect for Logs (Only fetch when expanded)
    useEffect(() => {
        if (!logs.expanded) return;

        const fetchLogs = async () => {
            try {
                const res = await axios.get(`${API_URL}/system/logs`);
                setLogs(prev => ({ ...prev, ...res.data })); // Merge content, keep expanded true
            } catch (e) {
                setLogs(prev => ({ ...prev, content: "Error loading logs." }));
            }
        };

        fetchLogs();
        const interval = setInterval(fetchLogs, 60000); // 60s Poll for Logs (slower)
        return () => clearInterval(interval);
    }, [logs.expanded]);

    const getStatusColor = (state) => {
        if (!state) return '#ffff88';
        const s = state.toLowerCase();
        if (s === 'online' || s === 'connected' || s === 'success') return '#44ff44';
        if (s.includes('running')) return '#00d4ff'; // Blue for running
        if (s === 'error' || s.includes('error') || s.includes('fail')) return '#ff4444';
        return '#ffff88';
    };

    if (loading) return <div className="dashboard"><h2>Loading Mission Control...</h2></div>;

    // status.tasks is now an array from /system/heartbeats
    const tasks = Array.isArray(status?.tasks) ? status.tasks : [];

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
                    <button
                        onClick={async () => {
                            if (confirm("Start Daily Analysis? This forces a full run.")) {
                                try { await axios.post(`${API_URL}/system/run/daily`); alert("Started!"); }
                                catch (e) { alert("Error: " + e.message); }
                            }
                        }}
                        style={{ background: '#00d4ff', border: 'none', borderRadius: '4px', padding: '0.5rem 1rem', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                        ▶ Run Intelligence Briefing
                    </button>
                    <div style={{ background: '#111', padding: '0.5rem 1rem', borderRadius: '4px', color: '#888' }}>
                        Last Updated: {new Date().toLocaleTimeString()}
                    </div>
                </div>
            </header>

            <div className="content">

                {/* 1. Task Health Table */}
                <div className="card" style={{ marginBottom: '2rem', padding: '0' }}>
                    <div style={{ padding: '1rem 1.5rem', borderBottom: '1px solid #333' }}>
                        <h3 style={{ margin: 0 }}>Autonomic Task Heartbeats (Recent 50)</h3>
                    </div>
                    <div className="table-container">
                        <table className="indices-table">
                            <thead>
                                <tr>
                                    <th>Task Name</th>
                                    <th>Status</th>
                                    <th>Time</th>
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
                                        <td style={{ fontWeight: 'bold' }}>{task.task || task.name}</td>
                                        <td>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                                <span style={{
                                                    color: getStatusColor(task.status),
                                                    background: `${getStatusColor(task.status)}22`,
                                                    padding: '2px 8px',
                                                    borderRadius: '4px',
                                                    fontSize: '0.85rem'
                                                }}>
                                                    {task.status?.toUpperCase()}
                                                </span>
                                                {task.status?.toLowerCase() === 'running' && (
                                                    <button
                                                        onClick={async () => {
                                                            if (confirm(`Stop task ${task.task}?`)) {
                                                                try {
                                                                    await axios.post(`${API_URL}/system/control/stop/${task.task}`);
                                                                    alert("Stop signal sent.");
                                                                } catch (e) {
                                                                    alert("Error: " + e.message);
                                                                }
                                                            }
                                                        }}
                                                        style={{
                                                            background: '#ff4444', color: 'white', border: 'none',
                                                            borderRadius: '4px', padding: '2px 6px',
                                                            cursor: 'pointer', fontSize: '0.7rem', fontWeight: 'bold'
                                                        }}
                                                    >
                                                        ■ STOP
                                                    </button>
                                                )}
                                            </div>
                                        </td>
                                        <td>{new Date(task.timestamp).toLocaleString()}</td>
                                        <td>{task.duration_sec ? `${task.duration_sec}s` : '-'}</td>
                                        <td style={{ fontFamily: 'monospace', fontSize: '0.9rem', color: '#aaa' }}>
                                            <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                                                <span style={{ opacity: 0.6 }}>{JSON.stringify(task.details || {}).substring(0, 30)}...</span>
                                                <button
                                                    onClick={() => setExpandedTask(task)}
                                                    style={{
                                                        background: '#333', border: 'none', color: '#fff',
                                                        padding: '2px 8px', borderRadius: '4px', cursor: 'pointer', fontSize: '0.8rem'
                                                    }}
                                                >
                                                    View Full
                                                </button>
                                            </div>
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

            {/* DETAILS MODAL */}
            {expandedTask && (
                <div style={{
                    position: 'fixed', top: 0, left: 0, right: 0, bottom: 0,
                    background: 'rgba(0,0,0,0.85)', display: 'flex', alignItems: 'center', justifyContent: 'center',
                    zIndex: 9999
                }} onClick={() => setExpandedTask(null)}>
                    <div style={{
                        background: '#1e1e1e', padding: '2rem', borderRadius: '12px',
                        border: '1px solid #444', maxWidth: '800px', width: '90%', maxHeight: '80vh',
                        display: 'flex', flexDirection: 'column'
                    }} onClick={e => e.stopPropagation()}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '1rem' }}>
                            <h2 style={{ margin: 0 }}>🔍 Task Details: {expandedTask.name}</h2>
                            <button onClick={() => setExpandedTask(null)} style={{
                                background: 'transparent', border: 'none', color: '#fff', fontSize: '1.5rem', cursor: 'pointer'
                            }}>×</button>
                        </div>
                        <div style={{
                            background: '#000', padding: '1rem', borderRadius: '8px',
                            overflow: 'auto', flex: 1, fontFamily: 'monospace', color: '#4f4'
                        }}>
                            <pre style={{ margin: 0 }}>{JSON.stringify(expandedTask.details, null, 2)}</pre>
                        </div>
                        <div style={{ marginTop: '1rem', textAlign: 'right', color: '#888', fontSize: '0.9rem' }}>
                            Start Time: {new Date(expandedTask.timestamp).toLocaleString()} | Duration: {expandedTask.duration_sec}s
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default ModelStatus;
