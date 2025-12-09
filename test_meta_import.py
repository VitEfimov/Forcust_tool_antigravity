
try:
    from src.models.meta_learner import MetaLearner
    print("MetaLearner imported successfully.")
    
    from src.models.walk_forward import WalkForwardForecaster
    print("WalkForwardForecaster imported successfully.")
    
    ml = MetaLearner()
    print("MetaLearner instantiated.")
    
except Exception as e:
    print(f"Error: {e}")
