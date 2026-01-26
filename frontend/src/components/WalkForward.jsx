import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import API_URL from '../config';
import { useSystemStatus } from '../hooks/useSystemStatus';
import { useLog } from '../context/LogContext';
import {
    LineChart, Line, XAxis, YAxis, Tooltip, Legend, ResponsiveContainer,
    BarChart, Bar, CartesianGrid, AreaChart, Area
} from 'recharts';

const WalkForward = () => {
    const { isBusy, runningTask } = useSystemStatus();
    const { addLog } = useLog();
    const [config, setConfig] = useState({
        symbol: 'SPY',
        horizon: 10,
        train_window: 730,
        step: 30,
        use_meta_learner: true
    });
    
    const [loading, setLoading] = useState(false);
    const [data, setData] = useState(null);
    const [showLogs, setShowLogs] = useState(false);
    const [serverLogs, setServerLogs] = useState([]);
    
    // Persistence: effective session management
    const [jobId, setJobId] = useState(localStorage.getItem('wf_job_id'));

    // Helper for safe formatting
    const fmt = (val, dec = 2) => {
        if (val === null || val === undefined) return "N/A";
        return val.toFixed(dec);
    };

    // Robust Polling Effect
    useEffect(() => {
        if (!jobId) return;

        // If we have a job ID, we are loading/running
        setLoading(true);
        
        // Auto-show logs if persistence found a running job
        if (serverLogs.length === 0) setShowLogs(true);
        
        const poll = setInterval(async () => {
            try {
                const res = await axios.get(`${API_URL}/jobs/${jobId}`);
                const job = res.data;

                // Sync Logs (File based source)
                if (job.logs && Array.isArray(job.logs)) {
                    setServerLogs(job.logs);
                }

                if (job.status === 'completed') {
                    clearInterval(poll);
                    setData(job.result);
                    setLoading(false);
                    localStorage.removeItem('wf_job_id');
                    setJobId(null);
                    addLog(`Job ${jobId.slice(0,8)}... Completed.`, 'WalkForward', 'success');
                } else if (job.status === 'failed') {
                    clearInterval(poll);
                    setLoading(false);
                    localStorage.removeItem('wf_job_id');
                    setJobId(null);
                    const errorMsg = job.error || "Unknown Error";
                    addLog(`Job Failed: ${errorMsg}`, 'WalkForward', 'error');
                    alert(`Validation Job Failed: ${errorMsg}`);
                }
            } catch (e) {
                console.error("Polling Error (Job likely missing):", e);
                // If 404, clear ID
                if (e.response && e.response.status === 404) {
                    localStorage.removeItem('wf_job_id');
                    setJobId(null);
                    setLoading(false);
                }
            }
        }, 2000); // 2s polling

        return () => clearInterval(poll);
    }, [jobId]);

    const runPipeline = async () => {
        setLoading(true);
        setServerLogs([]);
        setData(null);
        
        // Cleanup old logs if any
        try { await axios.delete(`${API_URL}/simulation/logs`); } catch(e){}

        addLog(`Starting Walk-Forward for ${config.symbol} (H=${config.horizon})...`, 'WalkForward');

        try {
            const res = await axios.post(`${API_URL}/models/walk_forward`, config);
            const newId = res.data.job_id;
            
            // Persist ID
            localStorage.setItem('wf_job_id', newId);
            setJobId(newId);
            setShowLogs(true);
            
        } catch (err) {
            alert(`Error starting job: ${err.message}`);
            addLog(`Error starting pipeline: ${err.message}`, 'WalkForward', 'error');
            setLoading(false);
        }
    };

    const downloadCSV = () => {
        if (!data || !data.results) return;
        const headers = Object.keys(data.results[0]).join(',');
        const rows = data.results.map(r => Object.values(r).join(','));
        const csvContent = "data:text/csv;charset=utf-8," + [headers, ...rows].join('\n');
        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", `${config.symbol}_WalkForward.csv`);
        document.body.appendChild(link);
        link.click();
    };

    return (
        <div className="p-6 bg-gray-900 min-h-screen text-white font-sans">
            <header className="mb-8">
                <h1 className="text-3xl font-bold bg-clip-text text-transparent bg-gradient-to-r from-blue-400 to-indigo-500">
                    Walk-Forward Validation
                </h1>
                <p className="text-gray-400">Strict leakage-free backtesting pipeline with financial performance metrics.</p>
            </header>

            <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
                {/* Configuration Panel */}
                <div className="lg:col-span-1 space-y-6">
                    <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                        <div className="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
                            <h3 className="text-xl font-bold">Configuration</h3>
                            <button
                                onClick={() => setShowLogs(true)}
                                className="text-xs bg-gray-700 hover:bg-gray-600 px-2 py-1 rounded text-gray-300"
                            >
                                Show Live Logs
                            </button>
                        </div>

                        <div className="space-y-4">
                            <div>
                                <label className="block text-gray-400 text-sm mb-1">Symbol</label>
                                <input
                                    type="text"
                                    value={config.symbol}
                                    onChange={e => setConfig({ ...config, symbol: e.target.value.toUpperCase() })}
                                    className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white"
                                />
                            </div>
                            <div>
                                <label className="block text-gray-400 text-sm mb-1">Horizon (Days)</label>
                                <input
                                    type="number"
                                    value={config.horizon}
                                    onChange={e => setConfig({ ...config, horizon: parseInt(e.target.value) })}
                                    className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white"
                                />
                            </div>
                            <div>
                                <label className="block text-gray-400 text-sm mb-1">Train Window (Days)</label>
                                <input
                                    type="number"
                                    value={config.train_window}
                                    onChange={e => setConfig({ ...config, train_window: parseInt(e.target.value) })}
                                    className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white"
                                />
                            </div>
                            <div>
                                <label className="block text-gray-400 text-sm mb-1">Step Size (Days)</label>
                                <input
                                    type="number"
                                    value={config.step}
                                    onChange={e => setConfig({ ...config, step: parseInt(e.target.value) })}
                                    className="w-full bg-gray-900 border border-gray-600 rounded p-2 text-white"
                                />
                            </div>
                            <div className="flex items-center space-x-2 mt-2">
                                <input
                                    type="checkbox"
                                    id="metaLearner"
                                    checked={config.use_meta_learner ?? true}
                                    onChange={e => setConfig({ ...config, use_meta_learner: e.target.checked })}
                                    className="h-4 w-4 bg-gray-900 border-gray-600 rounded"
                                />
                                <label htmlFor="metaLearner" className="text-gray-400 text-sm">Use Meta-Learning (Reliability)</label>
                            </div>

                            <button
                                onClick={runPipeline}
                                disabled={loading || isBusy}
                                className="w-full py-3 bg-blue-600 hover:bg-blue-500 rounded font-bold transition-colors disabled:opacity-50 mt-4 disabled:cursor-not-allowed"
                            >
                                {loading ? 'Running Pipeline...' : isBusy ? `Busy (${runningTask})` : 'Run Simulation'}
                            </button>
                            {isBusy && <p className="text-red-400 text-xs text-center mt-2">Locked by active process.</p>}
                        </div>
                    </div>

                    {data && (
                        <div className="bg-gray-800 p-6 rounded-xl border border-gray-700">
                            <h3 className="text-lg font-bold mb-2">Strategy Stats</h3>
                            <div className="space-y-3 text-sm">
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Total Return</span>
                                    <span className={data.metrics.total_strategy_return_pct >= 0 ? "text-green-400" : "text-red-400"}>
                                        {fmt(data.metrics.total_strategy_return_pct)}%
                                    </span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">CAGR</span>
                                    <span className="text-blue-300">{fmt(data.metrics.cagr_pct)}%</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Max Drawdown</span>
                                    <span className="text-red-400">{fmt(data.metrics.max_drawdown_pct)}%</span>
                                </div>
                                <div className="flex justify-between">
                                    <span className="text-gray-400">Sharpe Ratio</span>
                                    <span className="text-yellow-400">{fmt(data.metrics.sharpe_ratio)}</span>
                                </div>
                                <div className="flex justify-between pb-2 border-b border-gray-700">
                                    <span className="text-gray-400">Benchmark Ret</span>
                                    <span className="text-gray-200">{fmt(data.metrics.total_benchmark_return_pct)}%</span>
                                </div>
                                <div className="flex justify-between pt-2">
                                    <span className="text-gray-400">Dir Accuracy</span>
                                    <span className="text-blue-400">{fmt(data.metrics.dir_acc, 1)}%</span>
                                </div>
                            </div>
                        </div>
                    )}
                </div>

                {/* Results Panel */}
                <div className="lg:col-span-3 space-y-6">
                    {data ? (
                        <>
                            {/* Visuals Grid */}
                            <div className="grid grid-cols-1 gap-6">
                                {/* Equity Curve */}
                                <div className="bg-gray-800 p-4 rounded-lg border border-gray-700 h-80">
                                    <h4 className="text-lg font-bold mb-4">Equity Curve (Strategy vs Benchmark)</h4>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <AreaChart data={data.results}>
                                            <defs>
                                                <linearGradient id="colorStrategy" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#8884d8" stopOpacity={0.8} />
                                                    <stop offset="95%" stopColor="#8884d8" stopOpacity={0} />
                                                </linearGradient>
                                                <linearGradient id="colorBench" x1="0" y1="0" x2="0" y2="1">
                                                    <stop offset="5%" stopColor="#82ca9d" stopOpacity={0.8} />
                                                    <stop offset="95%" stopColor="#82ca9d" stopOpacity={0} />
                                                </linearGradient>
                                            </defs>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                                            <XAxis dataKey="Date" stroke="#888" />
                                            <YAxis domain={['auto', 'auto']} stroke="#888" />
                                            <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none' }} />
                                            <Legend />
                                            <Area type="monotone" dataKey="Cum_Strategy" stroke="#8884d8" fillOpacity={1} fill="url(#colorStrategy)" name="Strategy (Long/Short)" />
                                            <Area type="monotone" dataKey="Cum_Benchmark" stroke="#82ca9d" fillOpacity={1} fill="url(#colorBench)" name="Buy & Hold" />
                                        </AreaChart>
                                    </ResponsiveContainer>
                                </div>

                                {/* Actual vs Predicted */}
                                <div className="bg-gray-800 p-4 rounded-lg border border-gray-700 h-64">
                                    <h4 className="text-lg font-bold mb-4">Price Forecast Accuracy</h4>
                                    <ResponsiveContainer width="100%" height="100%">
                                        <LineChart data={data.results}>
                                            <CartesianGrid strokeDasharray="3 3" stroke="#444" />
                                            <XAxis dataKey="Date" stroke="#888" />
                                            <YAxis domain={['auto', 'auto']} stroke="#888" />
                                            <Tooltip contentStyle={{ backgroundColor: '#333', border: 'none' }} />
                                            <Line type="monotone" dataKey="Actual_Price" stroke="#4ade80" dot={false} strokeWidth={2} name="Actual Price" />
                                            <Line type="monotone" dataKey="Predicted_Price" stroke="#60a5fa" dot={false} strokeWidth={2} name="Predicted Price" />
                                        </LineChart>
                                    </ResponsiveContainer>
                                </div>
                            </div>

                            {/* Trade Log Table */}
                            <div className="bg-gray-800 p-4 rounded-lg border border-gray-700 overflow-x-auto">
                                <div className="flex justify-between items-center mb-4">
                                    <h4 className="text-lg font-bold">Trade Log (Last 50 Entries)</h4>
                                    <button
                                        onClick={downloadCSV}
                                        className="bg-green-600 hover:bg-green-500 px-4 py-2 rounded text-sm font-bold transition-colors"
                                    >
                                        Export CSV
                                    </button>
                                </div>
                                <table className="w-full text-left text-sm text-gray-300">
                                    <thead className="bg-gray-900 text-gray-400 uppercase font-medium">
                                        <tr>
                                            <th className="px-4 py-3">Date</th>
                                            <th className="px-4 py-3">Price</th>
                                            <th className="px-4 py-3">Pred</th>
                                            <th className="px-4 py-3">Actual Ret</th>
                                            <th className="px-4 py-3">Pred Ret</th>
                                            <th className="px-4 py-3">Regime</th>
                                            <th className="px-4 py-3">Result</th>
                                        </tr>
                                    </thead>
                                    <tbody className="divide-y divide-gray-700">
                                        {data.results.slice().reverse().slice(0, 50).map((row, i) => (
                                            <tr key={i} className="hover:bg-gray-700/50 transition-colors">
                                                <td className="px-4 py-3">{row.Date}</td>
                                                <td className="px-4 py-3">${fmt(row.Current_Price)}</td>
                                                <td className="px-4 py-3">${fmt(row.Predicted_Price)}</td>
                                                <td className={`px-4 py-3 ${row.Actual_Log_Ret >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                    {fmt(row.Actual_Log_Ret * 100)}%
                                                </td>
                                                <td className={`px-4 py-3 ${row.Predicted_Log_Ret >= 0 ? 'text-green-400' : 'text-red-400'}`}>
                                                    {fmt(row.Predicted_Log_Ret * 100)}%
                                                </td>
                                                <td className="px-4 py-3">
                                                    <span className={`px-2 py-1 rounded text-xs font-bold ${row.Regime === 'BULL' ? 'bg-green-900/40 text-green-400' :
                                                        row.Regime === 'BEAR' ? 'bg-red-900/40 text-red-400' :
                                                            'bg-gray-700/50 text-gray-400'
                                                        }`}>
                                                        {row.Regime}
                                                    </span>
                                                </td>
                                                <td className="px-4 py-3">
                                                    {row.Direction_Correct ?
                                                        <span className="bg-green-900/50 text-green-400 px-2 py-1 rounded text-xs">WIN</span> :
                                                        <span className="bg-red-900/50 text-red-400 px-2 py-1 rounded text-xs">LOSS</span>
                                                    }
                                                </td>
                                            </tr>
                                        ))}
                                    </tbody>
                                </table>
                            </div>
                        </>
                    ) : (
                        <div className="flex h-full items-center justify-center bg-gray-800/50 rounded-xl border border-gray-700 border-dashed h-96">
                            <div className="text-center">
                                <p className="text-gray-500 mb-2">Configure parameters and run simulation to see results.</p>
                                <p className="text-green-400 text-sm font-bold">Defaults applied automatically.</p>
                            </div>
                        </div>
                    )}
                </div>
            </div>

            {/* Live Logs Drawer/Modal */}
            {showLogs && (
                <div className="fixed inset-0 z-50 flex justify-end">
                    <div className="absolute inset-0 bg-black bg-opacity-50" onClick={() => setShowLogs(false)}></div>
                    <div className="relative w-full max-w-lg bg-gray-800 h-full shadow-2xl p-4 flex flex-col border-l border-gray-700">
                        <div className="flex justify-between items-center mb-4 border-b border-gray-700 pb-2">
                            <h3 className="text-xl font-bold text-white">Live Server Logs</h3>
                            <button onClick={() => setShowLogs(false)} className="text-gray-400 hover:text-white text-2xl">&times;</button>
                        </div>
                        <div className="flex-1 overflow-y-auto bg-gray-900 p-3 rounded font-mono text-xs text-green-400 whitespace-pre-wrap">
                            {serverLogs.length === 0 ? (
                                <span className="text-gray-500">Waiting for logs...</span>
                            ) : (
                                serverLogs.join('\n')
                            )}
                            {/* Auto-scroll anchor */}
                            <div ref={(el) => { if (el) el.scrollIntoView({ behavior: "smooth" }); }}></div>
                        </div>
                        <div className="mt-2 text-right">
                            <button
                                onClick={() => setShowLogs(false)}
                                className="px-4 py-2 bg-gray-700 hover:bg-gray-600 rounded text-sm text-white"
                            >
                                Close
                            </button>
                        </div>
                    </div>
                </div>
            )}
        </div>
    );
};

export default WalkForward;
