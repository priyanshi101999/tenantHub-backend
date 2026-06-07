
echo "waiting for DB"
sleep 5

echo "Running migration"
alembic uprade head

echo "Running tenantHub"
uvicorn app.main:app --host 0.0.0.0 --port 8000