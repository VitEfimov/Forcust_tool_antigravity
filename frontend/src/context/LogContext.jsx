import React, { createContext, useState, useContext, useCallback } from 'react';

const LogContext = createContext();

export const useLog = () => useContext(LogContext);

export const LogProvider = ({ children }) => {
    const [logs, setLogs] = useState([]);
    const [isOpen, setIsOpen] = useState(true);

    const addLog = useCallback((message, source = 'System', type = 'info') => {
        const timestamp = new Date().toLocaleTimeString();
        setLogs(prev => [...prev, { timestamp, message, source, type }]);
    }, []);

    const clearLogs = () => setLogs([]);

    return (
        <LogContext.Provider value={{ logs, addLog, clearLogs, isOpen, setIsOpen }}>
            {children}
        </LogContext.Provider>
    );
};
