import React, { useEffect, useRef } from 'react';
import { useLog } from '../context/LogContext';

const LogConsole = () => {
    const { logs, isOpen, setIsOpen, clearLogs } = useLog();
    const endRef = useRef(null);

    // Auto-scroll to bottom
    useEffect(() => {
        if (isOpen) {
            endRef.current?.scrollIntoView({ behavior: "smooth" });
        }
    }, [logs, isOpen]);

    if (!isOpen) {
        return (
            <div className="fixed bottom-4 right-4 z-50">
                <button
                    onClick={() => setIsOpen(true)}
                    className="bg-blue-600 text-white px-4 py-2 rounded-full shadow-lg border border-blue-500 hover:bg-blue-500 transition-all transform hover:scale-105 font-bold"
                >
                    Show Logs ({logs.length})
                </button>
            </div>
        );
    }

    return (
        <div className="fixed top-0 right-0 h-full w-96 bg-gray-900 border-l border-gray-700 shadow-2xl z-50 flex flex-col font-mono text-xs md:text-sm transform transition-transform duration-300 ease-in-out">
            {/* Header */}
            <div className="flex justify-between items-center p-3 bg-gray-800 border-b border-gray-700 shadow-sm">
                <h3 className="font-bold text-gray-200">System Activity</h3>
                <div className="flex gap-2">
                    <button
                        onClick={clearLogs}
                        className="text-xs bg-gray-700 hover:bg-gray-600 px-3 py-1 rounded text-red-300 transition-colors border border-gray-600"
                    >
                        Clear
                    </button>
                    <button
                        onClick={() => setIsOpen(false)}
                        className="bg-red-600 hover:bg-red-500 text-white px-3 py-1 rounded text-xs transition-colors font-bold shadow-sm"
                    >
                        X
                    </button>
                </div>
            </div>

            {/* Content */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-black/40">
                {logs.length === 0 && (
                    <div className="flex flex-col items-center justify-center h-full text-gray-500 italic opacity-50">
                        <p>No activity recorded yet...</p>
                    </div>
                )}

                {logs.map((log, i) => (
                    <div key={i} className="flex flex-col gap-1 border-b border-gray-800 pb-3 last:border-0 animation-fade-in">
                        <div className="flex justify-between text-xs text-gray-500 uppercase tracking-wider mb-1">
                            <span>{log.timestamp}</span>
                            <span className={`font-bold ${log.source === 'WalkForward' ? 'text-blue-400' :
                                    log.source === 'Simulation' ? 'text-purple-400' :
                                        log.source === 'Training' ? 'text-green-400' :
                                            'text-orange-400'
                                }`}>{log.source}</span>
                        </div>
                        <p className={`break-words whitespace-pre-wrap leading-relaxed ${log.type === 'error' ? 'text-red-400 bg-red-900/10 p-2 rounded' :
                                log.type === 'success' ? 'text-green-300' :
                                    'text-gray-300'
                            }`}>
                            {log.message}
                        </p>
                    </div>
                ))}
                <div ref={endRef} />
            </div>
        </div>
    );
};

export default LogConsole;
