# models/appliance.py - NEW FILE
# Pydantic models for type safety and validation

from pydantic import BaseModel, Field, field_validator
from typing import Optional, List
from datetime import datetime

class TimeWindow(BaseModel):
    """Represents a time window in minutes from midnight"""
    start: int = Field(..., ge=0, le=1440, description="Start time in minutes (0-1440)")
    end: int = Field(..., ge=0, le=1440, description="End time in minutes (0-1440)")
    
    @field_validator('end')
    @classmethod
    def end_after_start(cls, v, info):
        """Ensure end time is after start time"""
        if 'start' in info.data and v <= info.data['start']:
            raise ValueError('end time must be after start time')
        return v

class ApplianceExtracted(BaseModel):
    """Data extracted from LLM response"""
    name: str = Field(..., min_length=1, max_length=100, description="Appliance name")
    number: int = Field(1, ge=1, le=100, description="Quantity of appliances")
    power: int = Field(..., ge=1, le=10000, description="Power consumption in watts")
    func_time: int = Field(..., ge=1, le=1440, description="Total minutes used per day")
    
    num_windows: int = Field(1, ge=1, le=3, description="Number of usage windows")
    window_1: List[int] = Field(..., min_length=2, max_length=2, description="First time window [start, end]")
    window_2: Optional[List[int]] = Field(None, min_length=2, max_length=2, description="Second time window")
    window_3: Optional[List[int]] = Field(None, min_length=2, max_length=2, description="Third time window")
    
    func_cycle: int = Field(1, ge=1, description="Cycle time in minutes")
    fixed: str = Field("no", pattern="^(yes|no)$", description="Fixed schedule (yes/no)")
    occasional_use: float = Field(1.0, ge=0.0, le=1.0, description="Usage frequency (0.0-1.0)")
    wd_we_type: int = Field(2, ge=0, le=2, description="0=weekday, 1=weekend, 2=both")
    data_complete: bool = Field(True, description="Is data complete?")
    
    @field_validator('func_cycle')
    @classmethod
    def validate_cycle_vs_time(cls, v, info):
        """Thumb rule: func_cycle cannot exceed func_time"""
        if 'func_time' in info.data and v > info.data['func_time']:
            raise ValueError(f'func_cycle ({v}) cannot exceed func_time ({info.data["func_time"]})')
        return v
    
    @field_validator('window_1', 'window_2', 'window_3')
    @classmethod
    def validate_window_range(cls, v):
        """Ensure window times are in valid range"""
        if v is not None:
            if len(v) != 2:
                raise ValueError('Window must have exactly 2 values [start, end]')
            if v[0] < 0 or v[0] > 1440:
                raise ValueError(f'Window start ({v[0]}) must be 0-1440')
            if v[1] < 0 or v[1] > 1440:
                raise ValueError(f'Window end ({v[1]}) must be 0-1440')
            if v[1] <= v[0]:
                raise ValueError(f'Window end ({v[1]}) must be after start ({v[0]})')
        return v

class ApplianceDB(BaseModel):
    """Complete appliance record in database"""
    appliance_id: Optional[int] = None
    session_id: str
    user_id: str
    family_id: str
    
    name: str
    number: int
    power: int
    func_time: int
    
    num_windows: int
    window_1_start: Optional[int] = None
    window_1_end: Optional[int] = None
    window_2_start: Optional[int] = None
    window_2_end: Optional[int] = None
    window_3_start: Optional[int] = None
    window_3_end: Optional[int] = None
    
    func_cycle: int
    fixed: str
    occasional_use: float
    wd_we_type: int
    
    created_at: Optional[datetime] = None
    
    @classmethod
    def from_extracted(cls, extracted: ApplianceExtracted, session_id: str, user_id: str, family_id: str):
        """Convert extracted data to DB format"""
        return cls(
            session_id=session_id,
            user_id=user_id,
            family_id=family_id,
            name=extracted.name,
            number=extracted.number,
            power=extracted.power,
            func_time=extracted.func_time,
            num_windows=extracted.num_windows,
            window_1_start=extracted.window_1[0] if extracted.window_1 else None,
            window_1_end=extracted.window_1[1] if extracted.window_1 else None,
            window_2_start=extracted.window_2[0] if extracted.window_2 else None,
            window_2_end=extracted.window_2[1] if extracted.window_2 else None,
            window_3_start=extracted.window_3[0] if extracted.window_3 else None,
            window_3_end=extracted.window_3[1] if extracted.window_3 else None,
            func_cycle=extracted.func_cycle,
            fixed=extracted.fixed,
            occasional_use=extracted.occasional_use,
            wd_we_type=extracted.wd_we_type
        )
    
    class Config:
        from_attributes = True  # Allow creation from ORM objects

class ApplianceDefault(BaseModel):
    """Default appliance reference data"""
    appliance_type: str
    typical_power_watts: int
    category: Optional[str] = None

# Usage Examples:
def example_usage():
    # Parse LLM output with automatic validation
    llm_output = {
        "name": "LED Light",
        "number": "2",  # String will be coerced to int!
        "power": 10,
        "func_time": 240,
        "num_windows": 1,
        "window_1": [1080, 1320],
        "func_cycle": 1,
        "fixed": "no",
        "occasional_use": 1.0,
        "wd_we_type": 2,
        "data_complete": True
    }
    
    try:
        # Pydantic automatically validates and converts types!
        appliance = ApplianceExtracted(**llm_output)
        print(f"✓ Valid: {appliance.name}, {appliance.power}W")
        print(f"  Type of power: {type(appliance.power)}")  # int (auto-converted!)
        
    except Exception as e:
        print(f"✗ Invalid: {e}")