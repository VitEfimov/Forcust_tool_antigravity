import os

ROUTES_FILE = r"c:\Users\15717\Desktop\Forcust_tool_antigravity\src\api\routes.py"

# New version of run_walk_forward_job
NEW_FUNCTION = '''def run_walk_forward_job(job_id: str, req: WalkForwardRequest):
    """Background task wrapper for Walk-Forward."""
    
    # Load initial state
    job = _load_job(job_id) or {}
    job["status"] = "running"
    _save_job(job_id, job)
    
    # Helper wrapper for File-Based Logging
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

        # 6. Save to Database
        try:
            from src.core.database import Database
            from src.core.models import WalkForwardResult
            db = Database()
            
            saved_count = 0
            for res in results_list:
                item = WalkForwardResult(
                    symbol=symbol,
                    date=res['Date'],
                    prediction_price=float(res['Predicted_Price'] or 0.0),
                    reliability_score=float(res['Reliability'] or 0.5),
                    regime_label=str(res['Regime']),
                    mode="walk_forward_validation",
                    trained=True
                )
                db.save_walk_forward_result(item)
                saved_count += 1
            log_wrapper(f"Persisted {saved_count} records to database.")
            
        except Exception as db_err:
             log_wrapper(f"Database Save Warning: {db_err}")
             print(f"DB Error: {db_err}")

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

def patch_db():
    with open(ROUTES_FILE, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Identify function block
    start_sig = 'def run_walk_forward_job(job_id: str, req: WalkForwardRequest):'
    
    start_idx = content.find(start_sig)
    if start_idx == -1:
        print("Could not find function to patch")
        return
        
    # Assume it goes to end of file or looking for something that follows?
    # In my V2 patch, I put it at the very end of the block I inserted.
    # But checking file content, it might be followed by other things if I didn't verify end.
    # Actually, `run_walk_forward_job` is potentially the last function in that inserted block.
    # But wait, routes.py has `system/status` after it?
    # In V2 patch, I inserted proper order.
    
    # Let's find where the NEXT function starts?
    # Actually, simplistic logic: replace from start definition to end of "failed" exception block.
    # End signature: `_save_job(job_id, job)` inside `except Exception as e`.
    
    # Let's use string split logic if safe.
    
    # Safer: Read content, find start line, count indentation to find end block
    
    lines = content.splitlines()
    func_start_line = -1
    for i, line in enumerate(lines):
        if start_sig in line:
            func_start_line = i
            break
            
    if func_start_line == -1:
        print("Line not found")
        return
        
    # Determine end of function by indentation
    func_end_line = func_start_line + 1
    while func_end_line < len(lines):
        line = lines[func_end_line]
        if line.strip() and not line.startswith(' ') and not line.startswith('\t'):
            # Found non-indented line (next function or strict outdent)
            # Check if it's a decorator or def
            break
        func_end_line += 1
        
    print(f"Replacing lines {func_start_line} to {func_end_line}")
    
    # Splicing
    new_lines = lines[:func_start_line] + NEW_FUNCTION.splitlines() + lines[func_end_line:]
    
    with open(ROUTES_FILE, 'w', encoding='utf-8') as f:
        f.write("\n".join(new_lines))
        
    print("Database Patch Successful")

if __name__ == "__main__":
    patch_db()
