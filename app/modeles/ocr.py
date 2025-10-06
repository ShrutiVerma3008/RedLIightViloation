import logging
import os
from typing import Tuple, Optional
import numpy as np
import cv2
from app.config import Config

logger = logging.getLogger(__name__)

# Try to import OCR backends
try:
    import easyocr
    EASYOCR_AVAILABLE = True
    # Initialize EasyOCR reader (can be slow, do it once)
    # Using 'en' (English) and 'ch_sim' (Simplified Chinese) as a common general purpose setup.
    READER = easyocr.Reader(['en'], gpu=False)
    logger.info("EasyOCR initialized and available.")
except ImportError:
    EASYOCR_AVAILABLE = False
    READER = None
    logger.warning("EasyOCR not found. Will rely on PyTesseract fallback.")

try:
    import pytesseract
    TESSERACT_AVAILABLE = True
    # Set Tesseract path if necessary (Windows/custom installs)
    # e.g., pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    logger.info("PyTesseract initialized and available.")
except ImportError:
    TESSERACT_AVAILABLE = False
    logger.warning("PyTesseract not found. No OCR fallback available.")
except Exception as e:
    TESSERACT_AVAILABLE = False
    logger.warning(f"PyTesseract error: {e}. No OCR fallback available.")


class LicensePlateOCR:
    """
    Handles license plate recognition with EasyOCR as primary and Tesseract as fallback.
    """
    def __init__(self, backend: str = Config.OCR_BACKEND):
        """Initializes the OCR service based on configuration."""
        self.backend = backend
        if self.backend == 'easyocr' and not EASYOCR_AVAILABLE:
            self.backend = 'tesseract'
            logger.warning("Configured EasyOCR not available, switching to Tesseract.")
        if self.backend == 'tesseract' and not TESSERACT_AVAILABLE:
            self.backend = 'none'
            logger.error("Neither EasyOCR nor PyTesseract are available. OCR will fail.")

    def _preprocess_roi(self, plate_roi: np.ndarray) -> np.ndarray:
        """
        Preprocesses the cropped license plate image for better OCR results.
        
        Args:
            plate_roi: The Region of Interest (ROI) numpy array (BGR).
            
        Returns:
            The preprocessed image (grayscale).
        """
        if plate_roi is None or plate_roi.size == 0:
            return np.array([])
        
        # Convert to grayscale
        gray = cv2.cvtColor(plate_roi, cv2.COLOR_BGR2GRAY)
        
        # Apply Gaussian Blur to remove noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Adaptive Thresholding (better for varying illumination)
        thresh = cv2.adaptiveThreshold(
            blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
            cv2.THRESH_BINARY_INV, 11, 2
        )
        
        # Simple morphological operation to connect characters (Optional, can be tricky)
        # kernel = cv2.getStructuringElement(cv2.MORPH_RECT, (3, 3))
        # processed_img = cv2.dilate(thresh, kernel, iterations=1)
        
        return thresh

    def _normalize_plate(self, text: str) -> str:
        """
        Cleans and normalizes the OCR output.
        Removes non-alphanumeric characters and converts to uppercase.
        """
        if not text:
            return ""
        
        # Remove common OCR noise characters and spaces
        normalized = ''.join(filter(str.isalnum, text)).upper()
        
        # Simple post-processing rules (e.g., replace 'O' with '0', 'I' with '1')
        normalized = normalized.replace('O', '0').replace('I', '1').replace('Z', '2')
        
        return normalized

    def run_ocr(self, roi_image: np.ndarray) -> Tuple[str, float]:
        """
        Performs OCR on the image ROI using the configured backend.
        
        Args:
            roi_image: The numpy array of the vehicle/plate ROI.
            
        Returns:
            A tuple of (normalized_plate_string, confidence_score).
        """
        if self.backend == 'none' or roi_image is None or roi_image.size == 0:
            logger.warning("OCR backend is not available or input image is empty.")
            return "UNKNOWN", 0.0

        processed_img = self._preprocess_roi(roi_image)
        
        plate_text = "UNKNOWN"
        confidence = 0.0

        # --- Primary: EasyOCR ---
        if self.backend == 'easyocr':
            try:
                # EasyOCR runs detection and recognition
                results = READER.readtext(processed_img, detail=1, allowlist='0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ')
                
                if results:
                    # Take the result with the highest confidence
                    best_result = max(results, key=lambda x: x[2])
                    plate_text = best_result[1]
                    confidence = best_result[2]
                    logger.debug(f"EasyOCR Result: {plate_text} (Conf: {confidence:.2f})")
            except Exception as e:
                logger.error(f"EasyOCR failed: {e}. Falling back to PyTesseract (if available).")
                self.backend = 'tesseract' # Switch backend for fallback
        
        # --- Fallback: PyTesseract ---
        if self.backend == 'tesseract' and TESSERACT_AVAILABLE:
            try:
                # Use Plate configuration for Tesseract
                tess_config = r'--psm 7 -c tessedit_char_whitelist=0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ'
                text = pytesseract.image_to_string(processed_img, config=tess_config).strip()
                
                if text:
                    plate_text = text
                    # Tesseract does not provide a character confidence score directly in this mode, 
                    # so we use a placeholder or assume a lower confidence for the fallback.
                    confidence = 0.7 # Placeholder confidence
                    logger.debug(f"Tesseract Fallback Result: {plate_text} (Conf: {confidence:.2f})")
                
            except Exception as e:
                logger.error(f"PyTesseract fallback failed: {e}")
                
        # Final normalization
        normalized_plate = self._normalize_plate(plate_text)
        
        # Small penalty to confidence if normalization changes text significantly
        if plate_text and normalized_plate != self._normalize_plate(plate_text):
             confidence = max(0.0, confidence - 0.1)

        return normalized_plate, round(confidence, 3)