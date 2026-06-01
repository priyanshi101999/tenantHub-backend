from app.models.task import Task
from fastapi import status, HTTPException
from app.schemas.task_schema import TaskOut
from app.schemas.response_schema import APIResponse

async def create_task_service(data, db, current_user):
    data=data.model_dump()
    data.created_by=current_user.id
    data.workspace_id=current_user.workspace_id
    
    try:
        task = Task(**data)
        db.add(task)
        await db.commit()
        await db.refresh(task)

        return APIResponse(
            status=status.HTTP_201_CREATED,
            data=TaskOut.model_validate(task, exclude_unset=True),
            message="Task created successfully"
        )

    except Exception as e:
        await db.rollback()
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR, detail="Failed to create task")

