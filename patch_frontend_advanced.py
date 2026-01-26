import os

FILE_PATH = r"c:\Users\15717\Desktop\Forcust_tool_antigravity\frontend\src\components\AdvancedSimulationV2.jsx"

NEW_CONTENT = '''    const { isBusy, runningTask } = useSystemStatus();
    const [symbol, setSymbol] = useState('SPY'); 
    const [conservative, setConservative] = useState(true); 
    const [engine, setEngine] = useState('ensemble'); 
    const [data, setData] = useState(null);
    const [loading, setLoading] = useState(false);
    const [error, setError] = useState(null);
    
    // Persistence
    const [jobId, setJobId] = useState(localStorage.getItem('adv_sim_job_id'));

    // Polling Effect
    React.useEffect(() => {
        if (!jobId) return;
        setLoading(true);
        
        const poll = setInterval(async () => {
             try {
                 const res = await axios.get(`${API_URL}/jobs/${jobId}`);
                 const job = res.data;
                 
                 if (job.status === 'completed') {
                     clearInterval(poll);
                     setData(job.result);
                     setLoading(false);
                     setJobId(null);
                     localStorage.removeItem('adv_sim_job_id');
                 } else if (job.status === 'failed') {
                     clearInterval(poll);
                     setLoading(false);
                     setJobId(null);
                     localStorage.removeItem('adv_sim_job_id');
                     setError(job.error || "Simulation Failed");
                 }
             } catch (e) {
                 if (e.response && e.response.status === 404) {
                     setJobId(null);
                     localStorage.removeItem('adv_sim_job_id');
                     setLoading(false);
                 }
             }
        }, 2000);
        return () => clearInterval(poll);
    }, [jobId]);

    const runSimulation = async (e) => {
        e.preventDefault();
        setLoading(true);
        setError(null);
        setData(null);

        try {
            const res = await axios.post(`${API_URL}/simulation/v2/run`, {
                symbol, conservative, engine
            });
            const newId = res.data.job_id;
            setJobId(newId);
            localStorage.setItem('adv_sim_job_id', newId);
        } catch (err) {
            setError(err.message);
            setLoading(false);
        }
    };
'''

def patch_fe():
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        content = f.read()

    # Markers
    # Start: const AdvancedSimulationV2 = () => {
    # End: // Prepare chart data
    
    start_marker = "const AdvancedSimulationV2 = () => {"
    end_marker = "// Prepare chart data"
    
    start_idx = content.find(start_marker)
    end_idx = content.find(end_marker)
    
    if start_idx == -1 or end_idx == -1:
        print("Markers not found")
        return
        
    # Splice
    new_file_content = content[:start_idx + len(start_marker)] + "\n" + NEW_CONTENT + "    " + content[end_idx:]
    
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        f.write(new_file_content)
        
    print("Frontend Advanced Patch Successful")

if __name__ == "__main__":
    patch_fe()
