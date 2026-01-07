import { useState, useEffect } from 'react';
import axios from 'axios';

const API_URL = import.meta.env.VITE_API_URL || 'http://localhost:8000';

export const useSystemStatus = () => {
    const [status, setStatus] = useState({ isBusy: false, runningTask: null });
    const [loading, setLoading] = useState(true);

    useEffect(() => {
        let isMounted = true;

        const checkStatus = async () => {
            try {
                const ts = Date.now();
                const res = await axios.get(`${API_URL}/system/heartbeats?limit=20&t=${ts}`);
                const events = res.data.events || [];

                // Check basically any running task except "MarketOverview"/Status which are light
                // Heavy tasks: DailyAutomation, WeeklyTraining, MLTraining, WalkForward, AdvancedSimulation
                const heavyTasks = ["DailyAutomation", "WeeklyTraining", "MLTraining", "WalkForward", "AdvancedSimulation"];

                const runningItem = events.find(t => {
                    const isRunning = heavyTasks.includes(t.task) && t.status?.toLowerCase().includes('running');
                    if (!isRunning) return false;

                    // Stale Lock Check (15 mins)
                    if (t.timestamp) {
                        try {
                            const taskTime = new Date(t.timestamp).getTime();
                            const now = Date.now();
                            if ((now - taskTime) > 15 * 60 * 1000) {
                                return false; // Ignore stale tasks
                            }
                        } catch (e) { return true; }
                    }
                    return true;
                });

                if (isMounted) {
                    if (runningItem) {
                        setStatus({ isBusy: true, runningTask: runningItem.task });
                    } else {
                        setStatus({ isBusy: false, runningTask: null });
                    }
                    setLoading(false);
                }
            } catch (e) {
                console.error("Status check failed", e);
                if (isMounted) setLoading(false);
            }
        };

        checkStatus();
        const interval = setInterval(checkStatus, 5000); // 5s poll
        return () => {
            isMounted = false;
            clearInterval(interval);
        };
    }, []);

    return { ...status, loading };
};
