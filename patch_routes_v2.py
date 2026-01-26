import os
import json
from pathlib import Path

ROUTES_FILE = r"c:\Users\15717\Desktop\Forcust_tool_antigravity\src\api\routes.py"

# New helper functions and refactored endpoints
NEW_BLOCK = '''
import json
from pathlib import Path

# --- File-Based Job System ---
JOB_DIR = Path("data/jobs")
JOB_DIR.mkdir(parents=True, exist_ok=True)

def _save_job(job_id: str, data: dict):
    """Persist job state to disk."""
    try:
        with open(JOB_DIR / f"{job_id}.json", "w") as f:
            json.dump(data, f, default=str)
    except Exception as e:
        print(f"Job Save Error: {e}")

def _load_job(job_id: str) -> dict:
    """Load job from disk."""
    p = JOB_DIR / f"{job_id}.json"
    if not p.exists():
        return None
    try:
        with open(p, "r") as f:
            return json.load(f)
    except:
        return None

@router.post("/models/walk_forward")
def walk_forward_endpoint(req: WalkForwardRequest, background_tasks: BackgroundTasks, _=Depends(check_busy)):
    """Async Walk-Forward: Starts Job and returns ID."""
    job_id = str(uuid.uuid4())
    
    # Init Job
    job_data = {
        "id": job_id,
        "status": "pending", 
        "type": "walk_forward",
        "created_at": datetime.now().isoformat(),
        "logs": [],
        "result": None,
        "error": None
    }
    _save_job(job_id, job_data)
    
    background_tasks.add_task(run_walk_forward_job, job_id, req)
    
    return {"status": "started", "job_id": job_id, "message": "Pipeline started in background."}

@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Poll job status from disk."""
    job = _load_job(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return job

def run_walk_forward_job(job_id: str, req: WalkForwardRequest):
    """Background task wrapper for Walk-Forward."""
    
    # Load initial state
    job = _load_job(job_id) or {}
    job["status"] = "running"
    _save_job(job_id, job)
    
    # Helper wrapper for File-Based Logging
    def log_wrapper(msg: str):
         try:
             # Reload latest state to append (in case of other changes, though rare)
             # Optimization: Keep local log list and flush periodically?
             # For robustness, we read-modify-write. Collision risk is low (single writer).
             current = _load_job(job_id)
             if current:
                 ts = datetime.now().strftime("%H:%M:%S")
                 log_entry = f"[{ts}] {msg}"
                 current["logs"].append(log_entry)
                 _save_job(job_id, current)
             
             # Still print to console
             print(f"[JOB {job_id}] {msg}")
         except Exception:
             pass

    try:
        symbol = req.symbol.upper().strip()
        loader = DataLoader(settings.DATA_CACHE_DIR)
        
        # 1. Fetch Data
        log_wrapper(f"Fetching {symbol} from yfinance...")
        df = loader.get_data(symbol)
        if df.empty:
             raise ValueError("Symbol data not found")
            
        # 2. Fetch External Data
        external_data = {}
        for ext_sym in ["^VIX", "DX-Y.NYB", "^TNX"]:
            try:
                ext_df = loader.get_data(ext_sym)
                if not ext_df.empty:
                    friendly_name = ext_sym.replace("^", "").split("-")[0]
                    log_wrapper(f"Fetching {ext_sym} from yfinance...")
                    external_data[friendly_name] = ext_df
            except: pass
            
        # 3. Run Pipeline
        from src.models.walk_forward import WalkForwardForecaster
        wf = WalkForwardForecaster(
            symbol=symbol,
            df=df,
            external_data=external_data,
            prediction_horizon=req.horizon,
            train_window=req.train_window,
            step=req.step,
            transaction_cost=0.0005, 
            slippage=0.0005,
            use_meta_learner=req.use_meta_learner,
            verbose=True,
            log_func=log_wrapper
        )
        
        results_df_raw = wf.run()
        
        if results_df_raw.empty:
             raise ValueError("Not enough data for walk-forward loop")
            
        # 4. Compute Metrics
        stats = wf.performance_report(periods_per_year=252)
        
        metrics = {
            "mae_pct": 0.0, 
            "rmse_log": 0.0, 
            "dir_acc": _sanitize_val(stats['directional_accuracy']),
            "total_strategy_return_pct": _sanitize_val(stats['total_return_pct']),
            "total_benchmark_return_pct": _sanitize_val(stats['benchmark_return_pct']),
            "sharpe_ratio": _sanitize_val(stats['sharpe']),
            "cagr_pct": _sanitize_val(stats['cagr']),
            "max_drawdown_pct": _sanitize_val(stats['max_drawdown_pct']),
            "n_predictions": stats['n_folds']
        }
        
        # 5. Prepare Response List
        summary = wf.summary_dataframe()
        
        results_list = []
        if 'Date' not in summary.columns:
            summary = summary.reset_index().rename(columns={'index': 'Date', 'date': 'Date'})
            
        for idx, row in summary.iterrows():
             dt = row['Date'] 
             date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, 'strftime') else str(dt)
             
             price = row['Price']
             actual_log = row['Actual_LogRet']
             pred_log = row['Raw_Link'] 
             
             predicted_price = price * np.exp(pred_log)
             actual_price_next = price * np.exp(actual_log)
             
             cum_strat = 1.0
             if wf.equity_curve is not None:
                 try:
                     ts = pd.Timestamp(date_str)
                     if ts in wf.equity_curve.index:
                        cum_strat = float(wf.equity_curve.loc[ts])
                 except: pass
             
             results_list.append({
                "Date": date_str,
                "Current_Price": _sanitize_val(price),
                "Predicted_Log_Ret": _sanitize_val(pred_log),
                "Predicted_Price": _sanitize_val(predicted_price),
                "Actual_Price": _sanitize_val(actual_price_next), 
                "Actual_Log_Ret": _sanitize_val(actual_log),
                "Regime": row['Regime'],
                "Direction_Correct": (np.sign(pred_log) == np.sign(actual_log)) if pred_log != 0 else False,
                "Reliability": _sanitize_val(row['Reliability']),
                "Cum_Strategy": _sanitize_val(cum_strat),
                "Cum_Benchmark": 1.0 
             })
             
        if results_list:
            start_p = results_list[0]['Current_Price']
            for res in results_list:
                res['Cum_Benchmark'] = res['Current_Price'] / start_p if start_p else 1.0
                
        metrics["mae_pct"] = (abs(summary['Raw_Link'] - summary['Actual_LogRet'])).mean() * 100 
        
        final_response = {
            "symbol": symbol,
            "metrics": metrics,
            "results": results_list
        }
        
        # Save Final Success State
        job = _load_job(job_id)
        job["status"] = "completed"
        job["result"] = final_response
        job["logs"].append(f"[{datetime.now().strftime('%H:%M:%S')}] Job Completed Successfully.")
        _save_job(job_id, job)

    except Exception as e:
        import traceback
        traceback.print_exc()
        job = _load_job(job_id) or {}
        job["status"] = "failed"
        job["error"] = str(e)
        _save_job(job_id, job)
'''

def patch_routes_v2():
    with open(ROUTES_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx = -1
    end_idx = -1
    
    # Locate the block we added in V1 patch
    for i, line in enumerate(lines):
        if '@router.post("/models/walk_forward")' in line:
            start_idx = i
        if '@router.get("/system/status")' in line:
            end_idx = i
            break
            
    if start_idx == -1 or end_idx == -1:
        print("Could not find block to replace.")
        return

    # Back track to avoid duplicating header or catching blank lines
    # Last patch ensured NEW_CODE + \n\n + Header
    # So end_idx lines point to system/status.
    
    # Important: Cleanup the `JOBS = {}` from previous patch if it exists at top?
    # No, simple variable override is fine.
    
    header_start = end_idx
    search_limit = 20
    for k in range(1, search_limit):
        if "# SYSTEM STATUS & LOGS" in lines[end_idx - k]:
            header_start = end_idx - k - 2
            break
            
    # Splicing
    final_content = "".join(lines[:start_idx]) + NEW_BLOCK + "\n\n" + "".join(lines[header_start:])
    
    with open(ROUTES_FILE, 'w', encoding='utf-8') as f:
        f.write(final_content)
        
    print("Patch V2 successful.")

if __name__ == "__main__":
    patch_routes_v2()
