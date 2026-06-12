from datetime import datetime


def calculate_bmi(weight_kg: float, height_m: float) -> float:
    if height_m <= 0 or weight_kg <= 0:
        raise ValueError("Weight and height must be positive.")
    return round(weight_kg / (height_m ** 2), 2)


def bmi_category(bmi: float) -> tuple[str, str]:
    if bmi < 18.5:
        return "Underweight", "#3498db"
    if bmi < 25:
        return "Normal", "#2ecc71"
    if bmi < 30:
        return "Overweight", "#f39c12"
    return "Obese", "#e74c3c"


def height_to_meters(feet: float = 0, inches: float = 0, cm: float = 0) -> float:
    if cm > 0:
        return cm / 100
    return (feet * 12 + inches) * 0.0254


def kg_to_lbs(kg: float) -> float:
    return round(kg * 2.20462, 1)


def lbs_to_kg(lbs: float) -> float:
    return round(lbs / 2.20462, 1)


def m_to_cm(height_m: float) -> float:
    return round(height_m * 100, 1)


def parse_datetime(value: str) -> datetime:
    for fmt in ("%Y-%m-%d %H:%M:%S", "%Y-%m-%dT%H:%M:%S", "%Y-%m-%d"):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    raise ValueError(f"Unsupported date format: {value}")