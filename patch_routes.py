import os

ROUTES_FILE = r"c:\Users\15717\Desktop\Forcust_tool_antigravity\src\api\routes.py"

NEW_CODE = '''@router.post("/models/walk_forward")
def walk_forward_endpoint(req: WalkForwardRequest, background_tasks: BackgroundTasks, _=Depends(check_busy)):
    """Async Walk-Forward: Starts Job and returns ID."""
    job_id = str(uuid.uuid4())
    JOBS[job_id] = {"status": "pending", "type": "walk_forward"}
    
    background_tasks.add_task(run_walk_forward_job, job_id, req)
    
    return {"status": "started", "job_id": job_id, "message": "Pipeline started in background."}

@router.get("/jobs/{job_id}")
def get_job_status(job_id: str):
    """Poll job status."""
    if job_id not in JOBS:
        raise HTTPException(status_code=404, detail="Job not found")
    return JOBS[job_id]

def run_walk_forward_job(job_id: str, req: WalkForwardRequest):
    """Background task wrapper for Walk-Forward."""
    try:
        JOBS[job_id]["status"] = "running"
        
        # Helper wrapper for sync calling (since WalkForwardForecaster is sync)
        def log_wrapper(msg: str):
             try:
                 # Running loop in thread is tricky, just append to logs
                 SIMULATION_LOGS.append(msg)
                 print(msg)
             except Exception:
                 pass

        symbol = req.symbol.upper().strip()
        loader = DataLoader(settings.DATA_CACHE_DIR)
        
        # 1. Fetch Data
        log_wrapper(f"Fetching {symbol} from yfinance...")
        df = loader.get_data(symbol)
        if df.empty:
             raise ValueError("Symbol data not found")
            
        # 2. Fetch External Data for Cross-Sectional Features
        external_data = {}
        # VIX, Dollar Index, 10Y Treasury
        for ext_sym in ["^VIX", "DX-Y.NYB", "^TNX"]:
            try:
                ext_df = loader.get_data(ext_sym)
                if not ext_df.empty:
                    # Map to friendly names if needed or use raw
                    friendly_name = ext_sym.replace("^", "").split("-")[0]
                    log_wrapper(f"Fetching {ext_sym} from yfinance...")
                    external_data[friendly_name] = ext_df
            except:
                pass
            
        # 3. Run Pipeline
        from src.models.walk_forward import WalkForwardForecaster
        # Updated arguments for new class
        wf = WalkForwardForecaster(
            symbol=symbol,
            df=df,
            external_data=external_data,
            prediction_horizon=req.horizon,
            train_window=req.train_window,
            step=req.step,
            transaction_cost=0.0005, # 5bps defaults
            slippage=0.0005,
            use_meta_learner=req.use_meta_learner,
            verbose=True,
            log_func=log_wrapper
        )
        
        results_df_raw = wf.run()
        
        if results_df_raw.empty:
             raise ValueError("Not enough data for walk-forward loop")
            
        # 4. Compute Metrics using class method
        stats = wf.performance_report(periods_per_year=252)
        
        # Map stats to Frontend expected keys
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
        # Note: Summary uses Date Index usually.
        # Check if Date is index
        if 'Date' not in summary.columns:
            summary = summary.reset_index().rename(columns={'index': 'Date', 'date': 'Date'})
            
        for idx, row in summary.iterrows():
             dt = row['Date'] # Timestamp
             date_str = dt.strftime("%Y-%m-%d") if hasattr(dt, 'strftime') else str(dt)
             
             price = row['Price']
             actual_log = row['Actual_LogRet']
             pred_log = row['Raw_Link'] # This is Raw Lgbm+Ensemble
             
             predicted_price = price * np.exp(pred_log)
             actual_price_next = price * np.exp(actual_log)
             
             # Calculate Cum Strategy from global equity curve if available
             cum_strat = 1.0
             if wf.equity_curve is not None:
                 try:
                     # timestamp match
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
             
        # Enhance benchmark
        if results_list:
            start_p = results_list[0]['Current_Price']
            for res in results_list:
                res['Cum_Benchmark'] = res['Current_Price'] / start_p if start_p else 1.0
                
        metrics["mae_pct"] = (abs(summary['Raw_Link'] - summary['Actual_LogRet'])).mean() * 100 # Approx
        
        final_response = {
            "symbol": symbol,
            "metrics": metrics,
            "results": results_list
        }
        
        JOBS[job_id]["status"] = "completed"
        JOBS[job_id]["result"] = final_response
        log_wrapper(f"Walk-Forward Job {job_id} Completed Successfully.")

    except Exception as e:
        import traceback
        traceback.print_exc()
        JOBS[job_id]["status"] = "failed"
        JOBS[job_id]["error"] = str(e)
        log_wrapper(f"Walk-Forward Job {job_id} Failed: {e}")
'''

def patch_routes():
    with open(ROUTES_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()
        
    start_idx = -1
    end_idx = -1
    
    for i, line in enumerate(lines):
        if '@router.post("/models/walk_forward")' in line:
            start_idx = i
        if '@router.get("/system/status")' in line:
            end_idx = i
            break
            
    if start_idx == -1:
        print("Could not find start marker")
        return
        
    if end_idx == -1:
        print("Could not find end marker")
        return
        
    # Check buffering
    # We want to replace everything from start_idx up to (but not including) end_idx (actually end_idx lines are section header)
    # The end marker is `# ===...`.
    # Let's find the section header before system/status
    
    real_end = end_idx
    # backtrack to empty lines or comments
    while real_end > start_idx and ('====' in lines[real_end-1] or lines[real_end-1].strip() == '' or lines[real_end-1].strip().startswith('#')):
        real_end -= 1
        
    print(f"Replacing lines {start_idx} to {real_end}")
    
    new_lines = lines[:start_idx] + [NEW_CODE + "\n\n"] + lines[end_idx:] # Skip the blank lines and comments before next section?
    # No, keep the next section clean.
    # Actually lines[end_idx] is `@router.get("/system/status")`.
    # Wait, in the file view, there is a header box:
    # # ============================================================================
    # # SYSTEM STATUS & LOGS
    # # ============================================================================
    # 
    # @router.get("/system/status")
    
    # My loop found `@router.get("/system/status")`. So `end_idx` points to that line.
    # The header box is before it.
    # I should find the header box.
    
    search_limit = 20
    header_start = end_idx
    for k in range(1, search_limit):
        if "# SYSTEM STATUS & LOGS" in lines[end_idx - k]:
            # Found the box content.
            # The box starts 2 lines above usually.
            header_start = end_idx - k - 2
            break
            
    print(f"Adjusted End to {header_start}")
    
    # Splicing
    final_content = "".join(lines[:start_idx]) + NEW_CODE + "\n\n" + "".join(lines[header_start:])
    
    with open(ROUTES_FILE, 'w', encoding='utf-8') as f:
        f.write(final_content)
        
    print("Patch successful.")

if __name__ == "__main__":
    patch_routes()
