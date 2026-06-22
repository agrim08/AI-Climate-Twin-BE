import os
import sys
import asyncio
import pandas as pd
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import create_async_engine

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.core.config import settings
from app.core.database import Base, AsyncSessionLocal
from app.models.district import District
from app.models.user import User
from app.models.climate_observation import ClimateObservation
from app.models.simulation import SimulationResult
from app.models.forecast import Forecast

CITY_STATE_MAP = {
    'Agartala': 'Tripura',
    'Aizawl': 'Mizoram',
    'Amritsar': 'Punjab',
    'Bangalore': 'Karnataka',
    'Barmer': 'Rajasthan',
    'Bhopal': 'Madhya Pradesh',
    'Bhubaneswar': 'Odisha',
    'Bikaner': 'Rajasthan',
    'Chandigarh': 'Chandigarh',
    'Coimbatore': 'Tamil Nadu',
    'Dehradun': 'Uttarakhand',
    'Delhi': 'Delhi',
    'Gangtok': 'Sikkim',
    'Guwahati': 'Assam',
    'Gwalior': 'Madhya Pradesh',
    'Hyderabad': 'Telangana',
    'Imphal': 'Manipur',
    'Indore': 'Madhya Pradesh',
    'Itanagar': 'Arunachal Pradesh',
    'Jabalpur': 'Madhya Pradesh',
    'Jaipur': 'Rajasthan',
    'Jaisalmer': 'Rajasthan',
    'Jodhpur': 'Rajasthan',
    'Kanpur': 'Uttar Pradesh',
    'Kolkata': 'West Bengal',
    'Kozhikode': 'Kerala',
    'Leh': 'Ladakh',
    'Lucknow': 'Uttar Pradesh',
    'Madurai': 'Tamil Nadu',
    'Mahabaleshwar': 'Maharashtra',
    'Mangalore': 'Karnataka',
    'Mumbai': 'Maharashtra',
    'Munnar': 'Kerala',
    'Mysore': 'Karnataka',
    'Nagpur': 'Maharashtra',
    'Patna': 'Bihar',
    'Pune': 'Maharashtra',
    'Raipur': 'Chhattisgarh',
    'Shillong': 'Meghalaya',
    'Shimla': 'Himachal Pradesh',
    'Srinagar': 'Jammu and Kashmir',
    'Surat': 'Gujarat',
    'Thiruvananthapuram': 'Kerala',
    'Tiruchirappalli': 'Tamil Nadu',
    'Varanasi': 'Uttar Pradesh',
    'Visakhapatnam': 'Andhra Pradesh',
    'Wayanad': 'Kerala'
}

async def seed_db():
    print("Database Bootstrapper: Initializing engine...")
    engine = create_async_engine(settings.ASYNC_DATABASE_URL)
    
    print("Database Bootstrapper: Creating all tables if they don't exist...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database Bootstrapper: Checking if districts are already seeded...")
    async with AsyncSessionLocal() as db:
        result = await db.execute(select(func.count()).select_from(District))
        count = result.scalar()
        
        if count > 0:
            print(f"Database Bootstrapper: Districts table already has {count} records. Seeding skipped.")
            return
            
        print("Database Bootstrapper: Seeding districts from climate_master.csv...")
        csv_path = os.path.join(
            os.path.dirname(os.path.abspath(__file__)),
            "ml_research", "data", "processed", "climate_master.csv"
        )
        
        if not os.path.exists(csv_path):
            print(f"Database Bootstrapper: ERROR! Historical dataset not found at {csv_path}")
            sys.exit(1)
            
        df = pd.read_csv(csv_path)
        unique_cities = df.groupby("city")[["latitude", "longitude"]].first().reset_index()
        
        districts_to_add = []
        for idx, row in unique_cities.iterrows():
            city_name = row["city"]
            lat = float(row["latitude"])
            lon = float(row["longitude"])
            state = CITY_STATE_MAP.get(city_name, "India")
            
            district = District(
                district_name=city_name,
                state=state,
                latitude=lat,
                longitude=lon
            )
            districts_to_add.append(district)
            
        db.add_all(districts_to_add)
        await db.commit()
        print(f"Database Bootstrapper: Successfully seeded {len(districts_to_add)} districts.")

if __name__ == "__main__":
    asyncio.run(seed_db())
