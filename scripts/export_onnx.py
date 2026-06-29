"""Export trained sklearn models to ONNX format."""
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
REPO_ROOT = SCRIPT_DIR.parent
sys.path.insert(0, str(REPO_ROOT))

import pickle
import numpy as np

def export_logs():
    models_dir = Path("src/ml/models")
    
    with open(models_dir / "logs_model.pkl", "rb") as f:
        model = pickle.load(f)
    
    # Determine input dimension from the model
    # For RandomForest, we can't easily get n_features, so we load a sample
    train_fps = np.load(models_dir / "logs_train_fps.npy")
    input_dim = train_fps.shape[1]
    
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
        
        initial_type = [("input", FloatTensorType([None, input_dim]))]
        onnx_model = convert_sklearn(model, initial_types=initial_type, target_opset=12)
        
        with open(models_dir / "logs.onnx", "wb") as f:
            f.write(onnx_model.SerializeToString())
        print(f"Exported logs.onnx (input_dim={input_dim})")
    except Exception as e:
        print(f"ONNX export failed for logs: {e}")
        print("Will use pickle fallback.")

def export_herg():
    models_dir = Path("src/ml/models")
    
    with open(models_dir / "herg_model.pkl", "rb") as f:
        model = pickle.load(f)
    
    train_fps = np.load(models_dir / "herg_train_fps.npy")
    input_dim = train_fps.shape[1]
    
    try:
        from skl2onnx import convert_sklearn
        from skl2onnx.common.data_types import FloatTensorType
        
        initial_type = [("input", FloatTensorType([None, input_dim]))]
        onnx_model = convert_sklearn(model, initial_types=initial_type, target_opset=12)
        
        with open(models_dir / "herg.onnx", "wb") as f:
            f.write(onnx_model.SerializeToString())
        print(f"Exported herg.onnx (input_dim={input_dim})")
    except Exception as e:
        print(f"ONNX export failed for herg: {e}")
        print("Will use pickle fallback.")

if __name__ == "__main__":
    export_logs()
    export_herg()
