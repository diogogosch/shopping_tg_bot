import pytest
from unittest.mock import patch, MagicMock
from src.ocr_processor import OCRProcessor

@pytest.fixture
def ocr_processor():
    return OCRProcessor()

def test_clean_item_name(ocr_processor):
    """Test item name cleaning"""
    assert ocr_processor._clean_item_name("  organic apples  ") == "Apples"
    assert ocr_processor._clean_item_name("fresh milk each") == "Fresh Milk"

def test_is_valid_item(ocr_processor):
    """Test item validation"""
    valid_item = {'name': 'Apples', 'quantity': '2kg'}
    invalid_item = {'name': 'total', 'quantity': '10.50'}
    
    assert ocr_processor._is_valid_item(valid_item) == True
    assert ocr_processor._is_valid_item(invalid_item) == False

@patch('pytesseract.image_to_string')
def test_parse_receipt_text(mock_ocr, ocr_processor):
    """Test receipt text parsing"""
    mock_text = """
    Store Receipt
    Apples 2.50 kg  5.00
    Milk 1L         3.50
    Bread           2.00
    Total          10.50
    """
    
    items = ocr_processor._parse_receipt_text(mock_text)
    
    assert len(items) >= 2  # Should extract at least apples and milk
    assert any('apple' in item['name'].lower() for item in items)
