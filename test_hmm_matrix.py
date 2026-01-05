from src.models.hmm import RegimeDetector
import pandas as pd
import numpy as np
import json

def test_hmm_transition():
    print("Testing HMM Transition Matrix...")
    
    # Generate synthetic returns
    np.random.seed(42)
    # 200 days of low vol, 100 days of high vol
    ret1 = np.random.normal(0.001, 0.01, 200)
    ret2 = np.random.normal(-0.002, 0.03, 100)
    returns = pd.Series(np.concatenate([ret1, ret2]))
    
    hmm = RegimeDetector(n_components=2)
    hmm.fit(returns)
    
    matrix = hmm.get_transition_matrix()
    print("Transition Matrix:")
    print(json.dumps(matrix, indent=2))
    
    # Check if probabilities sum to roughly 1
    for state, trans in matrix.items():
        total = sum(trans.values())
        print(f"State {state} total prob: {total:.4f}")
        if not (0.99 <= total <= 1.01):
            print("ERROR: Probability sum invalid!")
            exit(1)
            
    print("Verification Successful!")

if __name__ == "__main__":
    test_hmm_transition()
