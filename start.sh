
echo "Running migrations"

until alembic upgrade head
do
    echo "Retrying in 3 seconds..."
    sleep 2
done

echo "Running tenantHub"
gunicorn app.main:app -k uvicorn.workers.UvicornWorker -w ${WEB_CONCURRENCY:-1} -b 0.0.0.0:8000