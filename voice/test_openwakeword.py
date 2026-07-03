from pathlib import Path

import numpy as np
from openwakeword.model import Model


ROOT = Path("D:/Friday/voice/wakewords/openwakeword")
PREFERRED = Path("D:/Friday/voice/wakewords/hey_friday.onnx")
FALLBACK = ROOT / "hey_jarvis_v0.1.onnx"
MODEL_PATH = PREFERRED if PREFERRED.exists() else FALLBACK

model = Model(
    wakeword_models=[str(MODEL_PATH)],
    inference_framework="onnx",
    melspec_model_path=str(ROOT / "melspectrogram.onnx"),
    embedding_model_path=str(ROOT / "embedding_model.onnx"),
)

predictions = model.predict(np.zeros(1280, dtype=np.int16))
print({"model": str(MODEL_PATH), "predictions": predictions, "status": bool(predictions)})
