import requests
import sys

def test_api():
    base_url = "http://localhost:8000"
    symbol = "SPY"
    
    print(f"Testing API for {symbol} with different engines...")
    
    engines = ['legacy', 'numpy']
    # Numba/Torch might fail if not installed, but fallback or error is expected.
    # We focus on confirming the parameter is accepted.
    
    for eng in engines:
        print(f"Requesting engine={eng}...")
        try:
            resp = requests.get(f"{base_url}/simulation/v2/{symbol}", params={"engine": eng, "conservative": False})
            if resp.status_code == 200:
                data = resp.json()
                method = data.get("method", "")
                print(f"SUCCESS: {eng} -> Method Label: '{method}'")
                with open("method_label.txt", "w") as f_out:
                    f_out.write(method)
                
                if eng in method.lower():
                     print("  -> Verified correct engine dispatch")
                else:
                     print(f"  -> WARNING: Method label mismatch? Expected '{eng}' in '{method}'")
            else:
                print(f"FAILED: {eng} -> Status {resp.status_code}: {resp.text[:200]}")
        except Exception as e:
            print(f"ERROR: {eng} -> {e}")

if __name__ == "__main__":
    test_api()
