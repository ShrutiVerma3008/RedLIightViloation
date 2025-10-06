import pytest
from unittest.mock import MagicMock, patch
import numpy as np
import cv2

# Import the class under test
from app.models.ocr import LicensePlateOCR

@pytest.fixture
def mock_roi_image():
    """Fixture for a simple mock image (a white square)."""
    return np.ones((100, 200, 3), dtype=np.uint8) * 255

def test_ocr_init_easyocr(mocker):
    """Test initialization when EasyOCR is available."""
    mocker.patch('app.models.ocr.EASYOCR_AVAILABLE', True)
    ocr = LicensePlateOCR(backend='easyocr')
    assert ocr.backend == 'easyocr'

@patch('app.models.ocr.TESSERACT_AVAILABLE', False)
@patch('app.models.ocr.EASYOCR_AVAILABLE', False)
def test_ocr_init_no_backend(mocker):
    """Test initialization when no OCR backend is available."""
    # Ensure no OCR is selected if none are available
    ocr = LicensePlateOCR(backend='easyocr') # Tries easyocr first
    assert ocr.backend == 'none'
    
@patch('app.models.ocr.EASYOCR_AVAILABLE', False)
@patch('app.models.ocr.TESSERACT_AVAILABLE', True)
def test_ocr_init_fallback(mocker):
    """Test initialization when EasyOCR fails and falls back to Tesseract."""
    ocr = LicensePlateOCR(backend='easyocr')
    # Should switch to tesseract because easyocr is mocked as unavailable
    assert ocr.backend == 'tesseract'

def test_normalize_plate(mock_roi_image):
    """Test the license plate normalization function."""
    ocr = LicensePlateOCR(backend='none') # Backend doesn't matter for this test
    
    # Standard normalization
    assert ocr._normalize_plate("aBC-12.34-d") == "ABC1234D"
    
    # OCR errors (O->0, I->1)
    assert ocr._normalize_plate("0CR1Z3I") == "0CR1231"
    
    # Empty/None handling
    assert ocr._normalize_plate("") == ""
    assert ocr._normalize_plate(None) == ""

@patch('app.models.ocr.READER')
def test_easyocr_run(mock_reader, mock_roi_image):
    """Test the EasyOCR code path with a mock result."""
    ocr = LicensePlateOCR(backend='easyocr')
    
    # Mock the readtext function to return a plate result
    mock_reader.readtext.return_value = [
        ([[0, 0], [10, 0], [10, 10], [0, 10]], 'ABC 123', 0.85),
        ([[10, 10], [20, 10], [20, 20], [10, 20]], 'XYZ 999', 0.92) # Highest confidence
    ]
    
    plate, confidence = ocr.run_ocr(mock_roi_image)
    
    # Should return the highest confidence result, normalized
    assert plate == "XYZ999"
    assert confidence == pytest.approx(0.92)

@patch('app.models.ocr.pytesseract.image_to_string')
@patch('app.models.ocr.EASYOCR_AVAILABLE', False)
@patch('app.models.ocr.TESSERACT_AVAILABLE', True)
def test_tesseract_fallback_run(mock_tesseract_string, mock_roi_image):
    """Test the Tesseract fallback code path."""
    ocr = LicensePlateOCR(backend='tesseract')
    
    # Mock Tesseract to return a plate string
    mock_tesseract_string.return_value = "P QR 789"
    
    plate, confidence = ocr.run_ocr(mock_roi_image)
    
    # Should return Tesseract result, normalized. Confidence is the placeholder 0.7.
    assert plate == "PQR789"
    assert confidence == pytest.approx(0.7)
    
    # Check that Tesseract was called with the correct config (containing the whitelist)
    args, kwargs = mock_tesseract_string.call_args
    assert '--psm 7 -c tessedit_char_whitelist=' in kwargs['config']