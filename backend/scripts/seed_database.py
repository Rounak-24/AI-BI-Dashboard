#!/usr/bin/env python3
"""
Seed the database with mock customer_behaviour data.
Supports Neon PostgreSQL. Run: uv run python scripts/seed_database.py
"""
import os
import sys
from pathlib import Path

# Add backend to path and load .env
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

import pandas as pd
from sqlalchemy import create_engine, text

from app.config import DATABASE_URL

_IS_POSTGRES = "postgresql" in DATABASE_URL

# PostgreSQL DDL (Neon)
CREATE_TABLE_SQL_POSTGRES = """
CREATE TABLE IF NOT EXISTS customer_behaviour (
    id SERIAL PRIMARY KEY,
    age INTEGER,
    monthly_income INTEGER,
    daily_internet_hours REAL,
    smartphone_usage_years INTEGER,
    social_media_hours REAL,
    online_payment_trust_score INTEGER,
    tech_savvy_score INTEGER,
    monthly_online_orders INTEGER,
    monthly_store_visits INTEGER,
    avg_online_spend INTEGER,
    avg_store_spend INTEGER,
    discount_sensitivity INTEGER,
    return_frequency INTEGER,
    avg_delivery_days INTEGER,
    delivery_fee_sensitivity INTEGER,
    free_return_importance INTEGER,
    product_availability_online INTEGER,
    impulse_buying_score INTEGER,
    need_touch_feel_score INTEGER,
    brand_loyalty_score INTEGER,
    environmental_awareness INTEGER,
    time_pressure_level REAL,
    gender TEXT,
    city_tier TEXT,
    shopping_preference TEXT
);
"""

# SQLite DDL (legacy / local)
CREATE_TABLE_SQL_SQLITE = """
CREATE TABLE IF NOT EXISTS customer_behaviour (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    age INTEGER,
    monthly_income INTEGER,
    daily_internet_hours REAL,
    smartphone_usage_years INTEGER,
    social_media_hours REAL,
    online_payment_trust_score INTEGER,
    tech_savvy_score INTEGER,
    monthly_online_orders INTEGER,
    monthly_store_visits INTEGER,
    avg_online_spend INTEGER,
    avg_store_spend INTEGER,
    discount_sensitivity INTEGER,
    return_frequency INTEGER,
    avg_delivery_days INTEGER,
    delivery_fee_sensitivity INTEGER,
    free_return_importance INTEGER,
    product_availability_online INTEGER,
    impulse_buying_score INTEGER,
    need_touch_feel_score INTEGER,
    brand_loyalty_score INTEGER,
    environmental_awareness INTEGER,
    time_pressure_level REAL,
    gender TEXT,
    city_tier TEXT,
    shopping_preference TEXT
);
"""

CREATE_TABLE_SQL = CREATE_TABLE_SQL_POSTGRES if _IS_POSTGRES else CREATE_TABLE_SQL_SQLITE


def generate_mock_data(n_rows: int = 500) -> pd.DataFrame:
    """Generate realistic mock customer behaviour data."""
    import random

    random.seed(42)

    genders = ["Male", "Female", "Other"]
    city_tiers = ["Tier 1", "Tier 2", "Tier 3"]
    shopping_prefs = ["Online", "Offline", "Both"]

    data = []
    for _ in range(n_rows):
        age = random.randint(22, 65)
        monthly_income = random.randint(25000, 250000)
        daily_internet_hours = round(random.uniform(1.0, 12.0), 1)
        smartphone_years = random.randint(1, 15)
        social_media_hours = round(random.uniform(0.5, 6.0), 1)
        online_trust = random.randint(1, 10)
        tech_savvy = random.randint(1, 10)
        monthly_online = random.randint(0, 15)
        monthly_store = random.randint(0, 12)
        avg_online = random.randint(500, 25000)
        avg_store = random.randint(500, 20000)
        discount_sens = random.randint(1, 10)
        return_freq = random.randint(0, 5)
        avg_delivery = random.randint(2, 10)
        delivery_fee_sens = random.randint(1, 10)
        free_return_imp = random.randint(1, 10)
        product_avail = random.randint(1, 10)
        impulse_buy = random.randint(1, 10)
        need_touch = random.randint(1, 10)
        brand_loyalty = random.randint(1, 10)
        env_aware = random.randint(1, 10)
        time_pressure = round(random.uniform(1.0, 5.0), 1)
        gender = random.choice(genders)
        city_tier = random.choice(city_tiers)
        shopping_pref = random.choice(shopping_prefs)

        data.append({
            "age": age,
            "monthly_income": monthly_income,
            "daily_internet_hours": daily_internet_hours,
            "smartphone_usage_years": smartphone_years,
            "social_media_hours": social_media_hours,
            "online_payment_trust_score": online_trust,
            "tech_savvy_score": tech_savvy,
            "monthly_online_orders": monthly_online,
            "monthly_store_visits": monthly_store,
            "avg_online_spend": avg_online,
            "avg_store_spend": avg_store,
            "discount_sensitivity": discount_sens,
            "return_frequency": return_freq,
            "avg_delivery_days": avg_delivery,
            "delivery_fee_sensitivity": delivery_fee_sens,
            "free_return_importance": free_return_imp,
            "product_availability_online": product_avail,
            "impulse_buying_score": impulse_buy,
            "need_touch_feel_score": need_touch,
            "brand_loyalty_score": brand_loyalty,
            "environmental_awareness": env_aware,
            "time_pressure_level": time_pressure,
            "gender": gender,
            "city_tier": city_tier,
            "shopping_preference": shopping_pref,
        })

    return pd.DataFrame(data)


def seed_database():
    """Create table and seed with mock data."""
    engine = create_engine(DATABASE_URL)

    with engine.connect() as conn:
        conn.execute(text("DROP TABLE IF EXISTS customer_behaviour"))
        conn.execute(text(CREATE_TABLE_SQL))
        conn.commit()

    df = generate_mock_data(500)
    df.to_sql("customer_behaviour", engine, if_exists="append", index=False)

    db_display = DATABASE_URL.split("@")[-1].split("?")[0] if _IS_POSTGRES else DATABASE_URL
    print(f"[OK] Seeded {len(df)} rows into customer_behaviour")
    print(f"  Database: {db_display}")
    print(f"  Table schema: {list(df.columns)}")


if __name__ == "__main__":
    seed_database()


#uv run python -m uvicorn app.main:app --reload
