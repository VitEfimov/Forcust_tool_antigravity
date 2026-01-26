
import React, { useState, useEffect } from 'react';
import axios from 'axios';
import { useLog } from '../context/LogContext';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

const ModelStatus = () => {
    const [status, setStatus] = useState(null);
    const [logs, setLogs] = useState({ content: 'Loading logs...' });
    const [loading, setLoading] = useState(true);
    const [expandedTask, setExpandedTask] = useState(null);
    const [fullTraining, setFullTraining] = useState(false);

    // 1. Initial Log Load on Expand
    useEffect(() => {
        if (logs.expanded) {
            axios.get(`${API_URL}/system/logs`)
                .then(res => setLogs(p => ({ ...p, ...res.data })))
                .catch(() => setLogs(p => ({ ...p, content: "Error loading logs." })));
        }
    }, [logs.expanded]);

    // 2. Adaptive Polling Loop
    useEffect(() => {
        let isMounted = true;
        let timer = null;

        const loop = async () => {
            if (!isMounted) return;

            let isRunning = false;
            try {
                const config = { timeout: 120000 };
                // Fetch Status
                const ts = Date.now();
                const [statusRes, heartbeatsRes] = await Promise.all([
                    axios.get(`${API_URL}/system/status?t=${ts}`, config),
                    axios.get(`${API_URL}/system/heartbeats?limit=50&t=${ts}`, config)
                ]);

                const events = heartbeatsRes.data.events || [];

                // FIX: Separate Latest State (for Banner) from History (for Table)
                // The status endpoint returns tasks as a dict {TaskName: {...details}}
                const latestMap = statusRes.data.tasks || {};
                const activeTasks = Object.values(latestMap); // Convert map to array for banner use

                setStatus({ ...statusRes.data, tasks: events, activeTasks: activeTasks });

                // Check active state using the LATEST map, not history
                // Filter out stale tasks (older than 15 mins) to prevent UI lockup
                const now = new Date();
                isRunning = activeTasks.some(t => {
                    if (!t.status?.toLowerCase().includes('running')) return false;
                    try {
                        const taskTime = new Date(t.timestamp);
                        // If task started > 15 mins ago, assume it's stale/crashed
                        const diffMins = (now - taskTime) / 60000;
                        return diffMins < 15;
                    } catch (e) { return true; } // Safety
                });

                // Conditional Log Polling
                // ONLY fetch logs in the loop if we are ACTIVELY running a simulation.
                // Otherwise, the static fetch above is sufficient.
                if (logs.expanded && isRunning) {
                    try {
                        const logRes = await axios.get(`${API_URL}/system/logs`);
                        setLogs(prev => ({ ...prev, ...logRes.data }));
                    } catch (e) { /* ignore */ }
                }

            } catch (err) {
                console.error("Poll failed", err);
                setStatus(prev => ({ ...prev, error: "Connection lost." }));
            } finally {
                setLoading(false);
            }

            // Adaptive Interval
            const delay = isRunning ? 5000 : 60000;
            if (isMounted) timer = setTimeout(loop, delay);
        };

        loop();

        return () => {
            isMounted = false;
            if (timer) clearTimeout(timer);
        };
    }, [logs.expanded]);

    const getStatusColor = (state) => {
        if (!state) return '#ffff88';
        const s = state.toLowerCase();
        if (s === 'online' || s === 'connected' || s === 'success') return '#44ff44';
        if (s.includes('running')) return '#00d4ff'; // Blue for running
        if (s === 'error' || s.includes('error') || s.includes('fail')) return '#ff4444';
        return 'orange'; // Changed for Interrupted/Unknown
    };

    if (loading) return <div className="dashboard"><h2>Loading Mission Control...</h2></div>;

    // History List (Recent Heartbeats)
    const tasks = Array.isArray(status?.tasks) ? status.tasks : [];
    // Active List (Current State)
    const activeTasks = Array.isArray(status?.activeTasks) ? status.activeTasks : [];


    return (
        <div className="dashboard">
            <header className="header" style={{ marginBottom: '2rem' }}>
                <h1 style={{ fontSize: '2rem' }}>🚀 System Mission Control</h1>
                <p style={{ color: '#888' }}>
                    Heartbeat Monitoring • Autonomic Task tracking • Intelligence Reports
                </p>
                {/* Only show Cloud Warning if remotely deployed */}
                {!['localhost', '127.0.0.1'].includes(window.location.hostname) && (
                    <div style={{ background: '#332b00', color: '#ffcc00', padding: '0.5rem', borderRadius: '4px', fontSize: '0.8rem', marginTop: '0.5rem', display: 'inline-block' }}>
                        ⚠️ <strong>CLOUD DEPLOYMENT NOTE:</strong> Please keep this tab OPEN while automation is running to prevent server sleep (Free Tier).
                    </div>
                )}
                <div style={{ display: 'flex', gap: '1rem', marginTop: '1rem', flexWrap: 'wrap', alignItems: 'center' }}>
                    <div style={{ background: '#111', padding: '0.5rem 1rem', borderRadius: '4px', border: `1px solid ${getStatusColor(status?.api)}` }}>
                        API: {status?.api?.toUpperCase()}
                    </div>
                    <div style={{ background: '#111', padding: '0.5rem 1rem', borderRadius: '4px', border: `1px solid ${getStatusColor(status?.database)}` }}>
                        DB: {status?.database?.toUpperCase()}
                    </div>

                    <div style={{ display: 'flex', alignItems: 'center', background: '#222', padding: '4px 10px', borderRadius: '4px', border: '1px solid #444' }}>
                        <label style={{ display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer', fontSize: '0.9rem', color: '#eee' }}>
                            <input
                                type="checkbox"
                                checked={fullTraining}
                                onChange={(e) => setFullTraining(e.target.checked)}
                            />
                            ⚡ Enable Full Training
                        </label>
                    </div>

                    <button
                        onClick={async () => {
                            const modeStr = fullTraining ? "FULL TRAINING (INTENSIVE)" : "Standard";
                            if (confirm(`Start Daily Analysis [${modeStr}]? This runs ALL simulations.`)) {
                                try {
                                    if (fullTraining) {
                                        await axios.post(`${API_URL}/admin/training/deep`);
                                        console.log("Deep training enabled.");
                                    }
                                    await axios.post(`${API_URL}/system/run/daily`);
                                    alert(`Started ${modeStr} Run!`);
                                }
                                catch (e) {
                                    console.error(e);
                                    alert(`Error: ${e.message}\nTrying to access: ${e.config?.url}`);
                                }
                            }
                        }}
                        style={{ background: fullTraining ? '#ff9800' : '#00d4ff', color: fullTraining ? 'black' : 'white', border: 'none', borderRadius: '4px', padding: '0.5rem 1rem', cursor: 'pointer', fontWeight: 'bold' }}
                    >
                        ▶ Run All Simulations
                    </button>
                    <button
                        onClick={async () => {
                            if (confirm("FORCE UNLOCK: Are you sure? Only use this if the system is stuck in 'Busy' state but nothing is running.")) {
                                try {
                                    const res = await axios.post(`${API_URL}/system/unlock`);
                                    alert(res.data.message);
                                    window.location.reload();
                                }
                                catch (e) { alert("Error: " + e.message); }
                            }
                        }}
                        style={{ background: '#ff4444', border: 'none', borderRadius: '4px', padding: '0.5rem 1rem', cursor: 'pointer', fontWeight: 'bold', color: 'white' }}
                    >
                        🔓 Force Unlock
                    </button>
                    <div style={{ background: '#111', padding: '0.5rem 1rem', borderRadius: '4px', color: '#888' }}>
                        Last Updated: {new Date().toLocaleTimeString()}
                    </div>
                </div>
            </header>

            <div className="content">

                {/* 1. Task Health Table (HISTORY LOG) */}
                <div className="card" style={{ marginBottom: '2rem', padding: '0' }}>
                    <div style={{ padding: '1rem 1.5rem', borderBottom: '1px solid #333' }}>
                        <h3 style={{ margin: 0 }}>Autonomic Task Heartbeats (Historical Log - Recent 50)</h3>
                    </div>
                    <div className="table-container">
                        <table className="indices-table">
                            <thead>
                                <tr>
                                    <th>Task Name</th>
                                    <th>Status (At Time of Log)</th>
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

                {/* 1.5 Active Task Banner (Progress Visualization - CURRENT ONLY) */}
                {activeTasks.filter(t => t.status?.toLowerCase().includes('running')).map((t, i) => (
                    <div key={i} style={{
                        background: 'linear-gradient(90deg, #004466, #002233)',
                        border: '1px solid #00d4ff',
                        padding: '1rem',
                        borderRadius: '8px',
                        marginBottom: '2rem',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        boxShadow: '0 0 15px rgba(0, 212, 255, 0.2)'
                    }}>
                        <div>
                            <h3 style={{ margin: 0, color: '#00d4ff', display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                                <span className="animate-spin">⚙️</span>
                                {t.task} In Progress...
                            </h3>
                            {t.details?.step && (
                                <div style={{ marginTop: '0.5rem', color: '#ccc', fontSize: '0.9rem' }}>
                                    <strong>Step:</strong> {t.details.step.replace(/_/g, ' ').toUpperCase()}
                                    {t.details.symbol && <span> | Target: <span style={{ color: 'white', fontWeight: 'bold' }}>{t.details.symbol}</span></span>}
                                    {t.details.horizon && <span> (H={t.details.horizon})</span>}
                                </div>
                            )}
                        </div>
                        {t.details?.progress && (
                            <div style={{ textAlign: 'right' }}>
                                <div style={{ fontSize: '1.5rem', fontWeight: 'bold', color: 'white' }}>{t.details.progress}</div>
                                <div style={{ fontSize: '0.8rem', color: '#888' }}>COMPLETED</div>
                            </div>
                        )}
                    </div>
                ))}

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
