import pytest
from sqlalchemy import text


pytestmark = [pytest.mark.anyio, pytest.mark.db]


async def test_test_database_connection(db_session):
    result = await db_session.execute(text("select 1"))

    assert result.scalar() == 1
