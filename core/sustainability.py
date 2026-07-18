"""Sustainability & Operations engine.

- Simulated real-time energy/water/waste metrics.
- AI-powered recycling / waste routing guidance for fans.
- Carbon-neutral impact tracking & gamified points rewards.
"""
import random

def get_metrics(minute: float, intensity: float) -> dict:
    # Seed based on minute for determinism
    rng = random.Random(int(abs(minute) * 100))
    
    # Energy consumption (kW) scales with crowd intensity
    base_energy = 800  # baseline stadium power (kW)
    energy_usage = base_energy + int(intensity * 1200 + rng.uniform(-50, 50))
    
    # Water usage (liters/min)
    base_water = 300
    water_usage = base_water + int(intensity * 1000 + rng.uniform(-30, 30))
    
    # Waste generated (kg/min)
    waste_rate = intensity * 12.0 + rng.uniform(-1, 1)
    recycling_rate = 0.42 + rng.uniform(-0.02, 0.03)  # ~42-45% diversion rate
    
    # Cumulative stats
    total_minutes = max(1.0, minute + 180)  # assume simulation started 3 hours before kickoff
    cum_waste_kg = int(total_minutes * (intensity * 8 + 4))
    cum_recycled_kg = int(cum_waste_kg * recycling_rate)
    cum_co2_saved_kg = int(cum_recycled_kg * 2.1) # 2.1 kg CO2 saved per kg recycled
    
    return {
        "energy_kw": max(0, energy_usage),
        "water_l_min": max(0, water_usage),
        "waste_rate_kg_min": round(max(0.0, waste_rate), 2),
        "diversion_rate_pct": round(recycling_rate * 100, 1),
        "cumulative": {
            "waste_kg": cum_waste_kg,
            "recycled_kg": cum_recycled_kg,
            "co2_saved_kg": cum_co2_saved_kg
        }
    }

def get_recycling_guidance(item: str) -> dict:
    item = item.strip().lower()
    if any(k in item for k in ["bottle", "cup", "can", "plastic", "aluminum", "tin", "glass"]):
        return {
            "item": item,
            "bin": "Recycling (Blue Bin)",
            "points": 10,
            "tip": "Empty any liquids before depositing. Smart bin scanned items earn FIFA Green Points!",
            "co2_saved_g": 150
        }
    elif any(k in item for k in ["food", "paper plate", "napkin", "hot dog", "burger", "pizza", "compost", "apple", "wrapper"]):
        return {
            "item": item,
            "bin": "Compost (Green Bin)",
            "points": 15,
            "tip": "Food leftovers, napkins, and compostable packaging go here. Helps reduce landfill methane!",
            "co2_saved_g": 200
        }
    else:
        return {
            "item": item,
            "bin": "Landfill (Black Bin)",
            "points": 2,
            "tip": "Non-recyclable wrappers and multi-material waste. Try to minimize landfill waste next time!",
            "co2_saved_g": 0
        }
