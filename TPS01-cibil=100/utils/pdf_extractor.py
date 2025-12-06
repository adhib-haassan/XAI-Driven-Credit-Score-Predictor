import re
import os
import pdfplumber
try:
    import fitz  # PyMuPDF
    PYMUPDF_AVAILABLE = True
except ImportError:
    PYMUPDF_AVAILABLE = False

def normalize_value(value_str):
    """Normalize extracted values: remove currency symbols, commas, convert to number"""
    if not value_str:
        return None
    
    # Remove currency symbols (₹, $, etc.)
    value_str = re.sub(r'[₹$€£]', '', value_str)
    # Remove commas and whitespace
    value_str = re.sub(r'[, ]', '', value_str)
    # Extract number (including decimals)
    match = re.search(r'(\d+\.?\d*)', value_str)
    if match:
        num_str = match.group(1)
        # Try float first, then int
        try:
            if '.' in num_str:
                return float(num_str)
            else:
                return int(num_str)
        except ValueError:
            return None
    return None

def extract_text_from_pdf(pdf_path):
    """Extract text from PDF using pdfplumber (primary) or PyMuPDF (fallback)"""
    text = ""
    
    # Try pdfplumber first
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        if text.strip():
            return text
    except Exception as e:
        print(f"pdfplumber extraction failed: {e}")
    
    # Fallback to PyMuPDF
    if PYMUPDF_AVAILABLE:
        try:
            doc = fitz.open(pdf_path)
            for page in doc:
                text += page.get_text() + "\n"
            doc.close()
            if text.strip():
                return text
        except Exception as e:
            print(f"PyMuPDF extraction failed: {e}")
    
    return None

def extract_from_pdf(pdf_path):
    """
    Extract all required fields from a structured PDF financial report.
    Returns dictionary with extracted fields or None if extraction fails.
    """
    if not os.path.exists(pdf_path):
        return None
    
    # Extract text from PDF
    text = extract_text_from_pdf(pdf_path)
    if not text:
        return None
    
    # Convert to lowercase for case-insensitive matching
    text_lower = text.lower()
    
    # Dictionary to store extracted values
    extracted = {}
    
    # Identity fields patterns
    patterns = {
        # Identity fields
        'company_name': [
            r'company\s*name[:\s]+([^\n]+)',
            r'business\s*name[:\s]+([^\n]+)',
            r'firm\s*name[:\s]+([^\n]+)',
            r'organization\s*name[:\s]+([^\n]+)'
        ],
        'owner_name': [
            r'owner\s*name[:\s]+([^\n]+)',
            r'proprietor\s*name[:\s]+([^\n]+)',
            r'director\s*name[:\s]+([^\n]+)',
            r'founder\s*name[:\s]+([^\n]+)',
            r'name\s*of\s*owner[:\s]+([^\n]+)',
            r'name\s*of\s*proprietor[:\s]+([^\n]+)',
            r'name\s*of\s*director[:\s]+([^\n]+)',
            r'name\s*of\s*managing\s*director[:\s]+([^\n]+)',
            r'managing\s*director[:\s]+([^\n]+)',
            r'ceo[:\s]+([^\n]+)',
            r'chief\s*executive\s*officer[:\s]+([^\n]+)',
            r'proprietor[:\s]+([^\n]+)',
            r'director[:\s]+([^\n]+)',
            r'owner[:\s]+([^\n]+)',
            r'name[:\s]+([^\n]+)\s*(?:director|proprietor|owner|ceo|managing\s*director)',
            r'(?:director|proprietor|owner|ceo|managing\s*director)[:\s]+([^\n]+)',
            r'name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)\s*(?:director|proprietor|owner)',
            r'(?:director|proprietor|owner)\s*name[:\s]+([A-Z][a-z]+(?:\s+[A-Z][a-z]+)+)'
        ],
        'business_size': [
            r'business\s*size[:\s]+(micro|small|medium|large)',
            r'size[:\s]+(micro|small|medium|large)',
            r'category[:\s]+(micro|small|medium|large)'
        ],
        
        # Financial parameters
        'monthly_inflow': [
            r'monthly\s*inflow[:\s]+([^\n]+)',
            r'inflow[:\s]+([^\n]+)',
            r'monthly\s*income[:\s]+([^\n]+)',
            r'monthly\s*revenue[:\s]+([^\n]+)'
        ],
        'monthly_outflow': [
            r'monthly\s*outflow[:\s]+([^\n]+)',
            r'outflow[:\s]+([^\n]+)',
            r'monthly\s*expenses[:\s]+([^\n]+)',
            r'monthly\s*expenditure[:\s]+([^\n]+)'
        ],
        'gst_compliance_score': [
            r'gst\s*compliance\s*score[:\s]+([^\n]+)',
            r'gst\s*score[:\s]+([^\n]+)',
            r'compliance\s*score[:\s]+([^\n]+)'
        ],
        'ecommerce_sales': [
            r'ecommerce\s*sales[:\s]+([^\n]+)',
            r'e-commerce\s*sales[:\s]+([^\n]+)',
            r'online\s*sales[:\s]+([^\n]+)',
            r'digital\s*sales[:\s]+([^\n]+)'
        ],
        'supplier_payments': [
            r'supplier\s*payments[:\s]+([^\n]+)',
            r'vendor\s*payments[:\s]+([^\n]+)',
            r'payments\s*to\s*suppliers[:\s]+([^\n]+)'
        ],
        'invoice_issued': [
            r'invoice\s*issued[:\s]+([^\n]+)',
            r'invoices\s*issued[:\s]+([^\n]+)',
            r'number\s*of\s*invoices[:\s]+([^\n]+)',
            r'total\s*invoices[:\s]+([^\n]+)'
        ],
        'invoice_amount': [
            r'invoice\s*amount[:\s]+([^\n]+)',
            r'average\s*invoice\s*amount[:\s]+([^\n]+)',
            r'total\s*invoice\s*amount[:\s]+([^\n]+)'
        ],
        'employee_count': [
            r'employee\s*count[:\s]+([^\n]+)',
            r'number\s*of\s*employees[:\s]+([^\n]+)',
            r'employees[:\s]+([^\n]+)',
            r'staff\s*count[:\s]+([^\n]+)'
        ],
        'asset_value': [
            r'asset\s*value[:\s]+([^\n]+)',
            r'total\s*assets[:\s]+([^\n]+)',
            r'asset\s*worth[:\s]+([^\n]+)',
            r'assets[:\s]+([^\n]+)'
        ],
        'business_age': [
            r'business\s*age[:\s]+([^\n]+)',
            r'age\s*of\s*business[:\s]+([^\n]+)',
            r'years\s*in\s*business[:\s]+([^\n]+)',
            r'operating\s*since[:\s]+([^\n]+)'
        ]
    }
    
    # Extract each field using patterns
    for field_name, field_patterns in patterns.items():
        value = None
        for pattern in field_patterns:
            # Try case-insensitive match
            match = re.search(pattern, text_lower, re.IGNORECASE)
            if not match:
                # Try case-sensitive match on original text
                match = re.search(pattern, text, re.IGNORECASE)
            
            if match:
                value_str = match.group(1).strip()
                
                # For business_size, keep as string
                if field_name == 'business_size':
                    value = value_str.lower()
                    # Normalize to micro/small/medium
                    if 'micro' in value:
                        value = 'micro'
                    elif 'small' in value:
                        value = 'small'
                    elif 'medium' in value:
                        value = 'medium'
                    else:
                        value = value_str
                    break
                # For company_name and owner_name, keep as string
                elif field_name in ['company_name', 'owner_name']:
                    value = value_str
                    break
                # For numeric fields, normalize
                else:
                    normalized = normalize_value(value_str)
                    if normalized is not None:
                        value = normalized
                        break
        
        extracted[field_name] = value
    
    # Also try to extract email and other identity fields that might be in PDF
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    email_match = re.search(email_pattern, text)
    if email_match:
        extracted['email'] = email_match.group(0)
    
    # Try to extract company_type
    company_type_patterns = [
        r'company\s*type[:\s]+([^\n]+)',
        r'business\s*type[:\s]+([^\n]+)',
        r'type[:\s]+(sole\s*proprietorship|partnership|llp|private\s*limited|public\s*limited)'
    ]
    for pattern in company_type_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            extracted['company_type'] = match.group(1).strip()
            break
    
    # Try to extract country
    country_patterns = [
        r'country[:\s]+([^\n]+)',
        r'location[:\s]+([^\n]+)'
    ]
    for pattern in country_patterns:
        match = re.search(pattern, text_lower, re.IGNORECASE)
        if match:
            extracted['country'] = match.group(1).strip()
            break
    
    return extracted

