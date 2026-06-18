import uuid
from fastapi import APIRouter, UploadFile, File, BackgroundTasks, HTTPException, status
from app.services.import_service import ImportService, import_tasks
from app.core.database import AsyncSessionLocal

router = APIRouter(prefix="/climate", tags=["Climate Import"])

@router.post("/import", status_code=status.HTTP_202_ACCEPTED)
async def import_climate_data_csv(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...)
):
    """
    Upload a CSV file containing climate observations to be parsed and imported in the background.
    Expected CSV columns: district_id, rainfall, temperature, humidity, observation_date
    """
    if not file.filename.endswith('.csv'):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid file format. Only CSV files (.csv) are supported."
        )
        
    try:
        content = await file.read()
        task_id = str(uuid.uuid4())
        
        # Dispatch validation and insertion task to background worker thread
        background_tasks.add_task(
            ImportService.run_import_task,
            task_id=task_id,
            file_content=content,
            db_session_maker=AsyncSessionLocal
        )
        
        return {
            "task_id": task_id,
            "status": "processing",
            "message": "CSV upload accepted. Observations are being processed in the background.",
            "status_check_url": f"/api/v1/climate/import/{task_id}"
        }
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to initialize import task: {str(e)}"
        )

@router.get("/import/{task_id}")
async def get_import_task_status(task_id: str):
    """
    Check the status and get error/skip reports of a background CSV import task.
    """
    task = import_tasks.get(task_id)
    if not task:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Import task with ID {task_id} not found."
        )
    return task
