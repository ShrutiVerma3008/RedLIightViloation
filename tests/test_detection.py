import pytest
from unittest.mock import MagicMock
from app.models.detection import RedLightDetector, VEHICLE_CLASS_IDS
import numpy as np

# Mocking YOLO model is necessary as it has complex external dependencies (PyTorch, GPU)
@pytest.fixture
def mock_detector():
    """Fixture to create a RedLightDetector instance with a mocked YOLO model."""
    detector = RedLightDetector()
    detector.model = MagicMock()
    # Clear tracking history for isolated tests
    detector.tracking_history = {}
    return detector

def test_detector_initialization(mock_detector):
    """Test that the detector initializes correctly (even with mock)."""
    assert isinstance(mock_detector.tracking_history, dict)
    assert mock_detector.model is not None

def test_violation_crossing_logic(mock_detector):
    """
    Test the stop-line crossing logic.
    Assumes stop line at Y=500. Crossing is Y_prev <= 500 and Y_current > 500.
    """
    stop_line = (0, 500, 1000, 500) # Stop line at y=500

    track_id = 99
    
    # Frame 1: Before the line (y=490)
    mock_detector.tracking_history[track_id] = [{'frame_idx': 1, 'centroid': (500, 490)}]
    assert not mock_detector._check_violation(track_id, (500, 490), stop_line)
    
    # Frame 2: On the line (y=500)
    mock_detector.tracking_history[track_id].append({'frame_idx': 2, 'centroid': (500, 500)})
    assert not mock_detector._check_violation(track_id, (500, 500), stop_line)
    
    # Frame 3: Crossing the line (y=501) - VIOLATION!
    mock_detector.tracking_history[track_id].append({'frame_idx': 3, 'centroid': (500, 501)})
    assert mock_detector._check_violation(track_id, (500, 501), stop_line)
    
    # Frame 4: Past the line (y=550) - NOT a *new* violation (already crossed)
    mock_detector.tracking_history[track_id].append({'frame_idx': 4, 'centroid': (500, 550)})
    # Previous (y=501) was already past (501 > 500), so the condition `was_before_or_on` fails.
    assert not mock_detector._check_violation(track_id, (500, 550), stop_line)

def test_process_frame_no_violation(mock_detector):
    """Test process_frame when no violation occurs."""
    frame = np.zeros((640, 480, 3), dtype=np.uint8)
    stop_line = (0, 500, 480, 500)
    
    # Mock YOLO result: one tracked vehicle *before* the line
    mock_results = MagicMock()
    mock_results[0].boxes.id.cpu.return_value.numpy.return_value = np.array([1])
    mock_results[0].boxes.xyxy.cpu.return_value.numpy.return_value = np.array([[100, 100, 200, 400]]) # Centroid y=400 (before line)
    
    mock_detector.model.track.return_value = mock_results
    
    annotated_frame, violation_data = mock_detector.process_frame(frame, 1, stop_line, is_red_light=True)
    
    assert violation_data is None
    assert mock_detector.tracking_history[1][0]['centroid'] == (150, 400)
    
def test_process_frame_violation(mock_detector):
    """Test process_frame when a violation is detected."""
    frame = np.zeros((640, 480, 3), dtype=np.uint8)
    stop_line = (0, 500, 480, 500)
    track_id = 2

    # Pre-populate history for the crossing check
    mock_detector.tracking_history[track_id] = [{'frame_idx': 1, 'centroid': (150, 490)}]

    # Mock YOLO result: one tracked vehicle *crossing* the line
    mock_results = MagicMock()
    mock_results[0].boxes.id.cpu.return_value.numpy.return_value = np.array([track_id])
    mock_results[0].boxes.xyxy.cpu.return_value.numpy.return_value = np.array([[100, 100, 200, 505]]) # Centroid y=505 (past line)
    mock_detector.model.track.return_value = mock_results

    annotated_frame, violation_data = mock_detector.process_frame(frame, 2, stop_line, is_red_light=True)
    
    assert violation_data is not None
    assert violation_data['track_id'] == track_id
    assert violation_data['centroid'] == (150, 505)