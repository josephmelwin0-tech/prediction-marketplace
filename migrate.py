# import os
# from sqlalchemy import create_engine, text

# DATABASE_URL = "postgresql://prediction_db_r7ss_user:F8unbzg4CaIiroURwGpJs1je8FROgOD1@dpg-d7r2mru7r5hc7394op40-a.singapore-postgres.render.com/prediction_db_r7ss"  # paste from Render

# engine = create_engine(DATABASE_URL)

# with engine.connect() as conn:
#     conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS developer_email VARCHAR"))
#     conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS api_key_hash VARCHAR"))
#     conn.execute(text("ALTER TABLE agents ADD COLUMN IF NOT EXISTS is_active BOOLEAN DEFAULT TRUE"))
#     conn.commit()
#     print("Done. Columns added.")
import os
from sqlalchemy import create_engine, text
DATABASE_URL = "postgresql://prediction_db_r7ss_user:F8unbzg4CaIiroURwGpJs1je8FROgOD1@dpg-d7r2mru7r5hc7394op40-a.singapore-postgres.render.com/prediction_db_r7ss"  # paste from Render

engine = create_engine(DATABASE_URL)

with engine.connect() as conn:
    conn.execute(text("ALTER TABLE agents ALTER COLUMN wallet_address DROP NOT NULL"))
    conn.commit()
    print("Done.")