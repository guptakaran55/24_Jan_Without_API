# services/validation_service.py - SIMPLIFIED WITH PYDANTIC
# Replace your current validation_service.py

from pydantic import ValidationError

try:
    from models.appliance import ApplianceExtracted
    USE_PYDANTIC = True
except ImportError:
    USE_PYDANTIC = False

def validate_appliance(data):
    """
    Validate appliance data
    
    With Pydantic: Uses Pydantic validation (automatic!)
    Without Pydantic: Uses manual validation (old way)
    """
    
    if USE_PYDANTIC:
        # Pydantic does ALL the validation!
        try:
            validated = ApplianceExtracted(**data)
            return {
                'valid': True,
                'errors': [],
                'data': validated.model_dump()
            }
        except ValidationError as e:
            errors = []
            for error in e.errors():
                field = '.'.join(str(x) for x in error['loc'])
                msg = error['msg']
                errors.append(f"{field}: {msg}")
            
            return {
                'valid': False,
                'errors': errors,
                'data': None
            }
    
    else:
        # Manual validation (fallback)
        errors = []
        
        # Required fields
        if not data.get('name'):
            errors.append('name: field required')
        
        # Type validation
        try:
            power = int(data.get('power', 0))
            if power <= 0:
                errors.append('power: must be greater than 0')
        except (ValueError, TypeError):
            errors.append('power: must be a valid integer')
        
        try:
            func_time = int(data.get('func_time', 0))
            if func_time <= 0:
                errors.append('func_time: must be greater than 0')
        except (ValueError, TypeError):
            errors.append('func_time: must be a valid integer')
        
        # Thumb rule: func_cycle <= func_time
        try:
            func_cycle = int(data.get('func_cycle', 1))
            func_time = int(data.get('func_time', 0))
            if func_cycle > func_time:
                errors.append(f'func_cycle ({func_cycle}) cannot exceed func_time ({func_time})')
        except (ValueError, TypeError):
            pass
        
        # Window validation
        window_1 = data.get('window_1')
        if window_1:
            if not isinstance(window_1, list) or len(window_1) != 2:
                errors.append('window_1: must be a list of 2 integers [start, end]')
            else:
                if window_1[1] <= window_1[0]:
                    errors.append(f'window_1: end ({window_1[1]}) must be after start ({window_1[0]})')
        
        return {
            'valid': len(errors) == 0,
            'errors': errors,
            'data': data if len(errors) == 0 else None
        }