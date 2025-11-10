# webapi

Minimal FastAPI example to serve `china_disease_data` from a MySQL database.

Prereqs:
- Python 3.8+
- Install dependencies: `pip install -r requirements.txt`
- Set environment variable `DB_URL`, e.g.

```
DB_URL="mysql+pymysql://root:123456@127.0.0.1:3306/chapter02?charset=utf8mb4"
```

Run:

```
uvicorn app:app --reload --host 127.0.0.1 --port 3000
```

This exposes `/api/china_disease` which returns JSON array of objects:

```
[{
  "name": "北京",
  "value": [116.24, 39.55],
  "cases": 123
}, ...]
```
