import os

FILE_PATH = r"c:\Users\15717\Desktop\Forcust_tool_antigravity\frontend\src\components\WalkForward.jsx"

NEW_CONTENT = '''    const { isBusy, runningTask } = useSystemStatus();
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

'''

def patch():
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()
      
    # Markers
    start_marker = "const WalkForward = () => {"
    end_marker = "const downloadCSV = () => {"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("Markers not found")
        return
        
    # Splice
    new_file_content = content[:start_idx + len(start_marker)] + "\n" + NEW_CONTENT + "    " + content[end_idx:]
    
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(new_file_content)
        
    print("Frontend Patch Successful")

if __name__ == "__main__":
    patch()
