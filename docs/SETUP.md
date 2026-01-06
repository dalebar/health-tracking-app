# Detailed Setup Guide

## Export Apple Health Data

1. Open Health app on iPhone
2. Tap your profile picture (top right)
3. Scroll to bottom → "Export All Health Data"
4. Wait 5-10 minutes for export to complete
5. AirDrop or email the ZIP file to your Mac
6. Extract `export.xml` (will be ~1-2GB)
7. Note the file path for configuration

## Database Setup (Neon)

1. Create account at [neon.tech](https://neon.tech)
2. Create new project
3. Copy connection string (format: `postgresql://user:password@host/db`)
4. Add to `.env` file

## Environment Variables

Required in `.env`:

```bash
DATABASE_URL=postgresql://...
ENVIRONMENT=development
```

Optional:

```bash
API_HOST=0.0.0.0
API_PORT=8000
LOG_LEVEL=INFO
```

## Troubleshooting

### Import Fails with "File Not Found"

Update file path in import scripts to match your export location.

### Database Connection Errors

- Verify `DATABASE_URL` in `.env`
- Check Neon dashboard for connection string
- Ensure `?sslmode=require` at end of URL

### Migration Conflicts

```bash
# Reset to clean state
alembic downgrade base
alembic upgrade head
```
