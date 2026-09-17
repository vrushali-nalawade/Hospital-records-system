"""
Health Record Locker - P2: OCR Pipeline
Step 1 of the P2 pipeline: image -> cleaned image -> raw text + per-word confidence.

Uses OpenCV preprocessing + EasyOCR for high reliability on real scanned prescriptions.
"""

import os
import cv2
import numpy as np
from PIL import Image

try:
    from embeddings import _get_process_rss_mb
except ImportError:
    try:
        from .embeddings import _get_process_rss_mb
    except ImportError:
        def _get_process_rss_mb() -> float:
            return 0.0

_EASYOCR_READER = None


def get_easyocr_reader():
    global _EASYOCR_READER
    if _EASYOCR_READER is None:
        import torch
        try:
            torch.set_num_threads(1)
        except Exception:
            pass
        rss_pre = _get_process_rss_mb()
        import easyocr
        # Initialize EasyOCR reader for English
        _EASYOCR_READER = easyocr.Reader(['en'], gpu=False, verbose=False)
        rss_post = _get_process_rss_mb()
        print(f"[MEM_DIAGNOSTIC] [Stage 2] RSS after EasyOCR initialization: {rss_post:.1f} MB (Delta: +{rss_post - rss_pre:.1f} MB)")
    return _EASYOCR_READER


def cleanup_ocr_reader():
    """
    Completely releases the EasyOCR reader and PyTorch sub-models to free RAM.
    Allows re-initialization on subsequent calls to get_easyocr_reader().
    """
    global _EASYOCR_READER
    rss_before_cleanup = _get_process_rss_mb()
    print(f"[MEM_DIAGNOSTIC] RSS immediately before EasyOCR cleanup: {rss_before_cleanup:.1f} MB")

    if _EASYOCR_READER is not None:
        try:
            if hasattr(_EASYOCR_READER, "detector"):
                del _EASYOCR_READER.detector
            if hasattr(_EASYOCR_READER, "recognizer"):
                del _EASYOCR_READER.recognizer
        except Exception:
            pass
        _EASYOCR_READER = None

    import gc
    gc.collect()

    try:
        import ctypes
        ctypes.CDLL("libc.so.6").malloc_trim(0)
    except Exception:
        pass

    rss_after_cleanup = _get_process_rss_mb()
    print(f"[MEM_DIAGNOSTIC] RSS immediately after EasyOCR cleanup: {rss_after_cleanup:.1f} MB (Delta: {rss_after_cleanup - rss_before_cleanup:.1f} MB)")
    return rss_after_cleanup


class OCRResult(dict):
    """
    Dictionary return object that supports tuple unpacking for backward compatibility.
    Unpacks as: (full_text, avg_confidence, low_confidence_words)
    Access as dict: result['full_text'], result['avg_confidence'], result['word_confidences'], etc.
    """
    def __iter__(self):
        yield self["full_text"]
        yield self["avg_confidence"]
        yield self.get("low_confidence_words", [])


def preprocess_image(image_path, save_cleaned_path="temp_cleaned.png"):
    """
    Cleans up a scanned/photographed prescription before OCR:
    grayscale -> denoise -> contrast boost (CLAHE) -> adaptive thresholding.
    Saves cleaned image for UI debugging display.
    """
    img = cv2.imread(image_path)

    if img is None or img.size == 0:
        try:
            pil_img = Image.open(image_path).convert("RGB")
            img = cv2.cvtColor(np.array(pil_img), cv2.COLOR_RGB2BGR)
        except Exception as e:
            raise ValueError(
                f"Could not read image (tried OpenCV and PIL): {image_path}. "
                f"The file may be corrupted or not a valid image. ({e})"
            )

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

    # Denoise speckle noise
    denoised = cv2.fastNlMeansDenoising(gray, h=10)

    # Improve contrast via CLAHE
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    contrasted = clahe.apply(denoised)

    # Adaptive thresholding for uneven lighting
    thresh = cv2.adaptiveThreshold(
        contrasted, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, cv2.THRESH_BINARY, 31, 15
    )

    # Downscale images to max dimension 1000px for 5x faster CPU OCR
    h, w = thresh.shape[:2]
    if max(h, w) > 1000:
        scale = 1000.0 / max(h, w)
        thresh = cv2.resize(thresh, (int(w * scale), int(h * scale)), interpolation=cv2.INTER_AREA)

    if save_cleaned_path:
        try:
            cv2.imwrite(save_cleaned_path, thresh)
        except Exception:
            pass

    return thresh, save_cleaned_path if save_cleaned_path else image_path


def run_ocr(image_path, preprocess=True):
    """
    Runs OCR on a prescription document image using EasyOCR.
    Returns: OCRResult dict object containing full_text, avg_confidence, word_confidences, cleaned_image_path, engine.
    """
    rss1 = _get_process_rss_mb()
    print(f"[MEM_DIAGNOSTIC] [Stage 1] RSS immediately before OCR starts: {rss1:.1f} MB")

    cleaned_path = "temp_cleaned.png"
    if preprocess:
        thresh, cleaned_path = preprocess_image(image_path, save_cleaned_path="temp_cleaned.png")
        target_input = thresh
    else:
        target_input = cv2.imread(image_path)
        if target_input is None:
            target_input = image_path
        cleaned_path = image_path

    reader = get_easyocr_reader()
    
    # Read text using EasyOCR with speed optimization params
    results = reader.readtext(target_input, canvas_size=1000, mag_ratio=1.0)

    lines = []
    word_confidences = []
    confidences = []
    low_confidence_words = []

    for bbox, text, conf in results:
        text_str = text.strip()
        if not text_str:
            continue
        conf_pct = round(float(conf) * 100, 1)
        lines.append(text_str)
        confidences.append(conf_pct)
        word_confidences.append((text_str, conf_pct))

        if conf_pct < 60.0:
            low_confidence_words.append((text_str, conf_pct))

    full_text = "\n".join(lines)
    avg_confidence = round(sum(confidences) / len(confidences), 1) if confidences else 0.0

    # Explicit memory cleanup of temporary OpenCV/image arrays
    del results, target_input
    if thresh is not None:
        del thresh
    import gc
    gc.collect()

    rss3 = _get_process_rss_mb()
    print(f"[MEM_DIAGNOSTIC] [Stage 3] RSS after OCR finishes: {rss3:.1f} MB")

    res = OCRResult({
        "full_text": full_text,
        "avg_confidence": avg_confidence,
        "word_confidences": word_confidences,
        "low_confidence_words": low_confidence_words,
        "cleaned_image_path": cleaned_path if os.path.exists(cleaned_path) else image_path,
        "original_image_path": image_path,
        "engine": "EasyOCR Engine (PyTorch)",
    })
    return res


if __name__ == "__main__":
    import sys
    test_img = sys.argv[1] if len(sys.argv) > 1 else "dataset/10.jpg"
    if os.path.exists(test_img):
        res = run_ocr(test_img)
        print("=== OCR OUTPUT ===")
        print(res["full_text"])
        print(f"=== Average confidence: {res['avg_confidence']}% ===")
    else:
        print(f"File not found: {test_img}")