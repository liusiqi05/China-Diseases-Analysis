from sqlalchemy import create_engine, text
import os
DB_URL = os.environ.get("DB_URL")
engine = create_engine(DB_URL)
with engine.connect() as conn:
    r = conn.execute(text("SELECT Province, SUM(Reported_Cases) AS cases FROM china_disease_data GROUP BY Province LIMIT 5"))
    for row in r:
        print(row)
print("OK")
