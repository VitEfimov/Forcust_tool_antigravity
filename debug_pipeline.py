from tests.test_pipeline import test_indicators, test_pipeline_training_data, test_pipeline_inference_data
import traceback

print("Running test_indicators...")
try:
    test_indicators()
    print("test_indicators passed")
except Exception:
    traceback.print_exc()

print("Running test_pipeline_training_data...")
try:
    test_pipeline_training_data()
    print("test_pipeline_training_data passed")
except Exception:
    traceback.print_exc()

print("Running test_pipeline_inference_data...")
try:
    test_pipeline_inference_data()
    print("test_pipeline_inference_data passed")
except Exception:
    traceback.print_exc()
