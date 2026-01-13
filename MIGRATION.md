# Database Migration Guide

This guide outlines the offline workflow to migrate your `meal_planner` data from SQLite to PostgreSQL.

## Prerequisites
- Docker Compose installed.
- The application running (or capable of running) via `docker-compose`.

## Migration Steps

### 1. Backup your SQLite Database
First, create a safety copy of your current database.
```bash
cp data/meal_planner.db meal_planner_backup.db
```

### 2. Stop the Application
Stop the running application container to ensure no new data is written.
```bash
docker-compose stop foodtracker
```

### 3. Start PostgreSQL
Ensure the new PostgreSQL service is running.
```bash
docker-compose up -d postgres
```

### 4. Run the Migration
Use a temporary container to run the migration script. We mount your backup file and connect to the postgres service.
```bash
# Syntax: python migrate_to_postgres.py --sqlite-path <path_to_db> --pg-url <postgres_url>

docker-compose run --rm \
  -v $(pwd)/meal_planner_backup.db:/backup.db \
  -v $(pwd)/migrate_to_postgres.py:/app/migrate_to_postgres.py \
  foodtracker \
  python migrate_to_postgres.py \
  --sqlite-path /backup.db \
  --pg-url postgresql://user:password@postgres/meal_planner
```

### 5. Update Configuration
Edit `docker-compose.yml` to switch the active database.
1. Comment out the SQLite `DATABASE_URL`.
2. Uncomment the PostgreSQL `DATABASE_URL`.

```yaml
    environment:
      # - DATABASE_URL=sqlite:////app/data/meal_planner.db
      - DATABASE_URL=postgresql://user:password@postgres/meal_planner
```

### 6. Restart the Application
Rebuild and start the application to use the new database.
```bash
docker-compose up -d --build foodtracker
```

## Verification
1. Log in to the application.
2. Verify your Foods, Meals, and Plans are present.
3. Check `docker logs foodplanner-foodtracker-1` to ensure no database connection errors.
