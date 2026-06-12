# Creator Discovery API

Base URL: `http://localhost:8000`

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/search` | Discovery search (database-first) |
| POST | `/accounts/ingest` | Ingest account records |
| POST | `/accounts/classify` | LLM classification |
| POST | `/identity/resolve` | Identity resolution |
| GET | `/creators` | List creators |
| GET | `/creators/{id}` | Creator detail with accounts |
| GET | `/accounts` | List accounts with filters |
| POST | `/imports/csv` | Upload CSV |
| GET | `/exports/csv` | Download CSV export |

## CSV Import Example

```bash
curl -X POST http://localhost:8000/imports/csv \
  -F "file=@data/sample_creators.csv"
```

## Search Example

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -d '{"query": "Los Angeles fitness creators", "limit": 20}'
```
