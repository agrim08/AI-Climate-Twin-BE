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
    'Wayanad': 'Kerala',
    # --- Extended map covering all 198 cities in climate_master.csv ---
    'Abohar': 'Punjab',
    'Agra': 'Uttar Pradesh',
    'Ahmedabad': 'Gujarat',
    'Ajmer': 'Rajasthan',
    'Akola': 'Maharashtra',
    'Alappuzha': 'Kerala',
    'Aligarh': 'Uttar Pradesh',
    'Allahabad': 'Uttar Pradesh',
    'Alwar': 'Rajasthan',
    'Amravati': 'Maharashtra',
    'Asansol': 'West Bengal',
    'Aurangabad': 'Maharashtra',
    'Balasore': 'Odisha',
    'Ballari': 'Karnataka',
    'Bareilly': 'Uttar Pradesh',
    'Baripada': 'Odisha',
    'Bathinda': 'Punjab',
    'Beawar': 'Rajasthan',
    'Belgaum': 'Karnataka',
    'Bellary': 'Karnataka',
    'Berhampur': 'Odisha',
    'Bhadrak': 'Odisha',
    'Bhagalpur': 'Bihar',
    'Bhavnagar': 'Gujarat',
    'Bhilai': 'Chhattisgarh',
    'Bhilwara': 'Rajasthan',
    'Bhuj': 'Gujarat',
    'Bijapur': 'Karnataka',
    'Bilaspur': 'Chhattisgarh',
    'Bokaro': 'Jharkhand',
    'Brahmapur': 'Odisha',
    'Burdwan': 'West Bengal',
    'Chennai': 'Tamil Nadu',
    'Churu': 'Rajasthan',
    'Cuddalore': 'Tamil Nadu',
    'Cuttack': 'Odisha',
    'Darjeeling': 'West Bengal',
    'Davanagere': 'Karnataka',
    'Davangere': 'Karnataka',
    'Deoghar': 'Jharkhand',
    'Dhanbad': 'Jharkhand',
    'Dharamshala': 'Himachal Pradesh',
    'Dhule': 'Maharashtra',
    'Dibrugarh': 'Assam',
    'Dimapur': 'Nagaland',
    'Dindigul': 'Tamil Nadu',
    'Durg': 'Chhattisgarh',
    'Durgapur': 'West Bengal',
    'Erode': 'Tamil Nadu',
    'Ernakulam': 'Kerala',
    'Faridabad': 'Haryana',
    'Gandhinagar': 'Gujarat',
    'Ganganagar': 'Rajasthan',
    'Gaya': 'Bihar',
    'Ghaziabad': 'Uttar Pradesh',
    'Giridih': 'Jharkhand',
    'Gokarna': 'Karnataka',
    'Gorakhpur': 'Uttar Pradesh',
    'Gulbarga': 'Karnataka',
    'Gulmarg': 'Jammu and Kashmir',
    'Guntur': 'Andhra Pradesh',
    'Gurugram': 'Haryana',
    'Haldia': 'West Bengal',
    'Hazaribagh': 'Jharkhand',
    'Hoshiarpur': 'Punjab',
    'Howrah': 'West Bengal',
    'Hubballi': 'Karnataka',
    'Hubli': 'Karnataka',
    'Idukki': 'Kerala',
    'Jalandhar': 'Punjab',
    'Jalgaon': 'Maharashtra',
    'Jalpaiguri': 'West Bengal',
    'Jamnagar': 'Gujarat',
    'Jamshedpur': 'Jharkhand',
    'Jhansi': 'Uttar Pradesh',
    'Jorhat': 'Assam',
    'Kakinada': 'Andhra Pradesh',
    'Kalaburagi': 'Karnataka',
    'Kalyan': 'Maharashtra',
    'Kanchipuram': 'Tamil Nadu',
    'Kannur': 'Kerala',
    'Karimnagar': 'Telangana',
    'Karwar': 'Karnataka',
    'Kasargod': 'Kerala',
    'Kharagpur': 'West Bengal',
    'Kishangarh': 'Rajasthan',
    'Kochi': 'Kerala',
    'Kohima': 'Nagaland',
    'Kolhapur': 'Maharashtra',
    'Kollam': 'Kerala',
    'Korba': 'Chhattisgarh',
    'Kota': 'Rajasthan',
    'Kottayam': 'Kerala',
    'Kumbakonam': 'Tamil Nadu',
    'Kullu': 'Himachal Pradesh',
    'Kurnool': 'Andhra Pradesh',
    'Latur': 'Maharashtra',
    'Ludhiana': 'Punjab',
    'Malda': 'West Bengal',
    'Manali': 'Himachal Pradesh',
    'Meerut': 'Uttar Pradesh',
    'Moga': 'Punjab',
    'Moradabad': 'Uttar Pradesh',
    'Muzaffarpur': 'Bihar',
    'Nagaon': 'Assam',
    'Nainital': 'Uttarakhand',
    'Nanded': 'Maharashtra',
    'Nashik': 'Maharashtra',
    'Navi Mumbai': 'Maharashtra',
    'Nellore': 'Andhra Pradesh',
    'New Delhi': 'Delhi',
    'Nizamabad': 'Telangana',
    'Palakkad': 'Kerala',
    'Pali': 'Rajasthan',
    'Panaji': 'Goa',
    'Pathanamthitta': 'Kerala',
    'Pathankot': 'Punjab',
    'Patiala': 'Punjab',
    'Phagwara': 'Punjab',
    'Puri': 'Odisha',
    'Rajahmundry': 'Andhra Pradesh',
    'Rajkot': 'Gujarat',
    'Ranchi': 'Jharkhand',
    'Ratnagiri': 'Maharashtra',
    'Rourkela': 'Odisha',
    'Sagar': 'Madhya Pradesh',
    'Saharanpur': 'Uttar Pradesh',
    'Salem': 'Tamil Nadu',
    'Sambalpur': 'Odisha',
    'Sangli': 'Maharashtra',
    'Satna': 'Madhya Pradesh',
    'Shivamogga': 'Karnataka',
    'Sikar': 'Rajasthan',
    'Silchar': 'Assam',
    'Siliguri': 'West Bengal',
    'Sindhudurg': 'Maharashtra',
    'Solapur': 'Maharashtra',
    'Sriganganagar': 'Rajasthan',
    'Tezpur': 'Assam',
    'Thane': 'Maharashtra',
    'Thanjavur': 'Tamil Nadu',
    'Thoothukudi': 'Tamil Nadu',
    'Thrissur': 'Kerala',
    'Tinsukia': 'Assam',
    'Tirunelveli': 'Tamil Nadu',
    'Tumakuru': 'Karnataka',
    'Udaipur': 'Rajasthan',
    'Udupi': 'Karnataka',
    'Ujjain': 'Madhya Pradesh',
    'Vadodara': 'Gujarat',
    'Vasai': 'Maharashtra',
    'Vellore': 'Tamil Nadu',
    'Vijayawada': 'Andhra Pradesh',
    'Warangal': 'Telangana',
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
