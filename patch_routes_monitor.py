import os

ROUTES_FILE = r"c:\Users\15717\Desktop\Forcust_tool_antigravity\src\api\routes.py"

def patch_monitor():
    with open(ROUTES_FILE, 'r', encoding='utf-8') as f:
        lines = f.readlines()

    # 1. Inject Start Log
    # Look for: job["status"] = "running"
    # Insert after: monitor.log_activity("WalkForward", "running", {"job_id": job_id})
    
    modified = False
    
    # We'll use a new list
    new_lines = []
    
    for line in lines:
        new_lines.append(line)
        if 'job["status"] = "running"' in line and 'WalkForward' not in line: # Avoid double patch if rerun
            # Indentation
            indent = line[:line.find('job')]
            new_lines.append(f'{indent}try: monitor.log_activity("WalkForward", "running", {{"job_id": job_id}})\n')
            new_lines.append(f'{indent}except: pass\n')
            modified = True
            
        if 'job["status"] = "completed"' in line:
            indent = line[:line.find('job')]
            new_lines.append(f'{indent}try: monitor.log_activity("WalkForward", "success", {{"job_id": job_id, "symbol": symbol}})\n')
            new_lines.append(f'{indent}except: pass\n')
            modified = True
            
        if 'job["status"] = "failed"' in line:
             indent = line[:line.find('job')]
             new_lines.append(f'{indent}try: monitor.log_activity("WalkForward", "failed", {{"job_id": job_id, "error": str(e)[:100]}})\n')
             new_lines.append(f'{indent}except: pass\n')
             modified = True

    if modified:
        with open(ROUTES_FILE, 'w', encoding='utf-8') as f:
            f.writelines(new_lines)
        print("Monitor Patch Successful")
    else:
        print("No injection points found (or already patched).")

if __name__ == "__main__":
    patch_monitor()
