import os

ROUTES_FILE = r"c:\Users\15717\Desktop\Forcust_tool_antigravity\src\api\routes.py"

NEW_BLOCK = '''
class AdvancedSimulationRequest(BaseModel):
    symbol: str
    engine: str = "ensemble"
    conservative: bool = True

def run_advanced_simulation_job(job_id: str, req: AdvancedSimulationRequest):
    """Background task for Advanced Simulation V2."""
    
    # Init Job State
    job = _load_job(job_id) or {}
    job["status"] = "running"
    _save_job(job_id, job)
    
    try:
        from src.core.monitoring import monitor
        monitor.log_activity("AdvancedSimulation", "running", {"job_id": job_id, "symbol": req.symbol})
    except: pass
    
    def log_wrapper(msg: str):
         try:
             current = _load_job(job_id)
             if current:
                 ts = datetime.now().strftime("%H:%M:%S")
                 log_entry = f"[{ts}] {msg}"
                 current["logs"].append(log_entry)
                 _save_job(job_id, current)
             print(f"[JOB {job_id}] {msg}")
         except Exception:
             pass

    try:
        symbol = req.symbol.upper().strip()
        log_wrapper(f"Starting V2 Simulation for {symbol} (Engine={req.engine})...")
        
        # 1. Fetch Data
        from src.data.loader import DataLoader
        loader = DataLoader(settings.DATA_CACHE_DIR)
        df = loader.get_data(symbol)
        
        if df.empty or len(df) < 500:
             raise ValueError("Insufficient data for simulation (need 500+ days).")
             
        # 2. Market Regimes (HMM)
        from src.models.hmm import RegimeDetector
        log_wrapper("Detecting Market Regimes (HMM)...")
        returns = df['Close'].pct_change().dropna()
        
        rd = RegimeDetector(n_components=2)
        rd.fit(returns)
        regimes = rd.predict(returns)
        transmat = rd.get_transition_matrix() 
        # AdvancedSimulator needs raw matrix, not dict labels
        # But wait, simulate_paths takes transmat as matrix?
        # Let's check rd.model.transmat_
        raw_transmat = rd.model.transmat_
        
        # 3. Fit Regime-Switching GARCH
        from src.models.advanced_simulation import AdvancedSimulator
        log_wrapper("Fitting Regime-Switching GARCH Parameters...")
        sim_engine = AdvancedSimulator(cache_dir=settings.DATA_CACHE_DIR)
        
        params = sim_engine.fit_regime_params(returns, regimes)
        
        # 4. Run Monte Carlo
        start_price = df['Close'].iloc[-1]
        start_regime = regimes[-1]
        
        log_wrapper(f"Running Monte Carlo (Sims=1000, Horizon=730d)...")
        
        # HMM model might have 2 or 3 components.
        # fit_regime_params handles whatever number of unique regimes passed.
        
        sim_res = sim_engine.simulate_paths(
            start_price=start_price,
            start_regime=start_regime,
            params=params,
            transmat=raw_transmat,
            days=730,
            sims=1000,
            conservative=req.conservative,
            engine=req.engine
        )
        
        # 5. Save to Database
        log_wrapper("Persisting results to Database...")
        from src.core.database import Database
        from src.core.models import AdvancedSimulationResult
        
        p50_val = sim_res['quantiles'][365]['p50'] # 1 Year
        p10_val = sim_res['quantiles'][365]['p10']
        p90_val = sim_res['quantiles'][365]['p90']
        
        db_item = AdvancedSimulationResult(
            symbol=symbol,
            date=datetime.now().strftime("%Y-%m-%d"),
            mc_p10=p10_val,
            mc_p50=p50_val,
            mc_p90=p90_val,
            conservative_mode=req.conservative
        )
        db = Database()
        db.save_advanced_simulation_result(db_item)
        
        # 6. Prepare Response
        # We need paths for chart.
        # 'paths' is (1000, 731). Too big for JSON.
        # Sample 50 paths.
        sample_paths = sim_res['paths'][:50].tolist() 
        
        result_payload = {
            "symbol": symbol,
            "paths_sample": sample_paths,
            "quantiles": sim_res['quantiles'],
            "metrics": {
                "upside_1y": (p50_val - start_price) / start_price * 100.0,
                "risk_1y": (p10_val - start_price) / start_price * 100.0
            }
        }
        
        job = _load_job(job_id)
        job["status"] = "completed"
        job["result"] = result_payload
        job["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] Simulation Completed.")
        _save_job(job_id, job)
        
        try:
            monitor.log_activity("AdvancedSimulation", "success", {"job_id": job_id, "symbol": symbol})
        except: pass

    except Exception as e:
        import traceback
        traceback.print_exc()
        job = _load_job(job_id) or {}
        job["status"] = "failed"
        job["error"] = str(e)
        _save_job(job_id, job)
        try:
             from src.core.monitoring import monitor
             monitor.log_activity("AdvancedSimulation", "failed", {"job_id": job_id, "error": str(e)[:100]})
        except: pass

@router.post("/simulation/v2/run")
def start_advanced_simulation(req: AdvancedSimulationRequest, background_tasks: BackgroundTasks):
    """Start Async Job for Advanced Simulation V2."""
    job_id = str(uuid.uuid4())
    job_data = {
        "id": job_id,
        "status": "pending", 
        "type": "advanced_simulation",
        "created_at": datetime.now().isoformat(),
        "logs": [],
        "result": None
    }
    _save_job(job_id, job_data)
    
    background_tasks.add_task(run_advanced_simulation_job, job_id, req)
    
    return {"status": "started", "job_id": job_id}
'''

def patch_backend():
    with open(ROUTES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()

    # Append to end of file
    with open(ROUTES_FILE, 'a', encoding='utf-8') as f:
        f.write("\n" + NEW_BLOCK + "\n")
        
    print("Backend Patch Successful")

if __name__ == "__main__":
    patch_backend()
