import csv
import codecs
import uuid
from datetime import datetime, date
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.future import select
from sqlalchemy import insert as sqla_insert
from app.models.climate_observation import ClimateObservation
from app.models.district import District

# In-memory store for tracking asynchronous import task status
import_tasks = {}

class ImportService:
    @staticmethod
    def parse_date(date_str: str) -> date:
        """
        Parses observation dates supporting common ISO and regional date formats.
        """
        for fmt in ('%Y-%m-%d', '%d-%m-%Y', '%Y/%m/%d', '%d/%m/%Y'):
            try:
                return datetime.strptime(date_str.strip(), fmt).date()
            except ValueError:
                continue
        raise ValueError(f"Invalid date format: '{date_str}'. Use YYYY-MM-DD or DD-MM-YYYY.")

    @staticmethod
    async def run_import_task(task_id: str, file_content: bytes, db_session_maker) -> None:
        """
        Runs the CSV validation and bulk insertion in the background.
        """
        import_tasks[task_id] = {
            "status": "processing",
            "progress": "Starting import",
            "result": None
        }
        
        async with db_session_maker() as db:
            try:
                # Read CSV lines
                lines = codecs.iterdecode(file_content.splitlines(), 'utf-8')
                csv_reader = csv.DictReader(lines)
                
                # Check for empty headers
                if not csv_reader.fieldnames:
                    raise ValueError("Uploaded CSV is empty or has invalid format headers.")
                
                # Fetch valid district IDs for constraint checks
                districts_result = await db.execute(select(District.id))
                valid_district_ids = set(districts_result.scalars().all())
                
                # Fetch existing observations to skip duplicates
                existing_obs_result = await db.execute(
                    select(ClimateObservation.district_id, ClimateObservation.observation_date)
                )
                existing_observations = set(existing_obs_result.all())
                
                errors = []
                rows_to_insert = []
                processed_count = 0
                duplicate_count = 0
                
                for idx, row in enumerate(csv_reader, start=1):
                    processed_count += 1
                    try:
                        # Validation checks
                        if not row.get("district_id") or not row.get("observation_date"):
                            raise ValueError("Row is missing 'district_id' or 'observation_date'")
                        
                        dist_id = int(row["district_id"])
                        if dist_id not in valid_district_ids:
                            raise ValueError(f"District ID {dist_id} does not exist in database")
                            
                        obs_date = ImportService.parse_date(row["observation_date"])
                        
                        # Duplicate skip check
                        if (dist_id, obs_date) in existing_observations:
                            duplicate_count += 1
                            continue
                            
                        rainfall = float(row.get("rainfall", 0.0))
                        temperature = float(row.get("temperature", 0.0))
                        humidity = float(row.get("humidity", 0.0))
                        
                        if not (0.0 <= humidity <= 100.0):
                            raise ValueError(f"Humidity value {humidity} must be between 0 and 100")
                            
                        rows_to_insert.append({
                            "district_id": dist_id,
                            "rainfall": rainfall,
                            "temperature": temperature,
                            "humidity": humidity,
                            "observation_date": obs_date
                        })
                        
                        # Cache locally to prevent duplicates within the same batch upload
                        existing_observations.add((dist_id, obs_date))
                        
                    except Exception as e:
                        errors.append({
                            "row": idx,
                            "error": f"{type(e).__name__}: {str(e)}",
                            "raw_data": row
                        })

                # Perform Bulk Insert
                success_count = 0
                if rows_to_insert:
                    stmt = sqla_insert(ClimateObservation).values(rows_to_insert)
                    await db.execute(stmt)
                    await db.commit()
                    success_count = len(rows_to_insert)
                    
                import_tasks[task_id] = {
                    "status": "completed",
                    "progress": "Import completed successfully",
                    "result": {
                        "processed_rows": processed_count,
                        "success_count": success_count,
                        "duplicate_skipped": duplicate_count,
                        "failed_count": len(errors),
                        "errors": errors
                    }
                }
            except Exception as outer_err:
                await db.rollback()
                import_tasks[task_id] = {
                    "status": "failed",
                    "progress": "Aborted due to system error",
                    "result": {
                        "system_error": str(outer_err)
                    }
                }
