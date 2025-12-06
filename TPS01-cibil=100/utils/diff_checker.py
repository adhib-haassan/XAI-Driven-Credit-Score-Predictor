def compare_profiles(old_profile, new_profile, old_score, new_score):
    """
    Compare two CompanyProfile objects and return differences.
    
    Args:
        old_profile: CompanyProfile object (previous profile)
        new_profile: CompanyProfile object (new profile)
        old_score: int (previous credit score)
        new_score: int (new credit score)
    
    Returns:
        dict: {
            "score_change": int,
            "changed_fields": {
                "field_name": {"old": value, "new": value},
                ...
            }
        }
    """
    score_change = new_score - old_score
    
    # List of financial fields to compare
    financial_fields = [
        'monthly_inflow',
        'monthly_outflow',
        'gst_compliance_score',
        'ecommerce_sales',
        'supplier_payments',
        'invoice_issued',
        'invoice_amount',
        'employee_count',
        'asset_value',
        'business_age',
        'business_size'
    ]
    
    changed_fields = {}
    
    for field in financial_fields:
        old_value = getattr(old_profile, field, None)
        new_value = getattr(new_profile, field, None)
        
        # Compare values (handle None cases)
        if old_value != new_value:
            # Both are None, skip
            if old_value is None and new_value is None:
                continue
            
            # One is None, consider it changed
            if old_value is None or new_value is None:
                changed_fields[field] = {
                    "old": old_value,
                    "new": new_value
                }
            # Both have values, compare
            else:
                # For float/int, allow small floating point differences
                if isinstance(old_value, (int, float)) and isinstance(new_value, (int, float)):
                    if abs(old_value - new_value) > 0.01:  # More than 0.01 difference
                        changed_fields[field] = {
                            "old": old_value,
                            "new": new_value
                        }
                else:
                    # For strings or other types, exact match
                    if old_value != new_value:
                        changed_fields[field] = {
                            "old": old_value,
                            "new": new_value
                        }
    
    return {
        "score_change": score_change,
        "changed_fields": changed_fields
    }

