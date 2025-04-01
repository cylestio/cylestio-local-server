# Getting Started with Cylestio Local Server

This guide will help you set up and run the Cylestio Local Server for collecting telemetry data from your AI agents.

## Prerequisites

- Python 3.9 or higher
- pip (Python package manager)
- git (for cloning the repository)

## Installation

### 1. Clone the Repository

```bash
git clone https://github.com/cylestio/cylestio-local-server.git
cd cylestio-local-server
```

### 2. Create a Virtual Environment (Recommended)

```bash
# Create a virtual environment
python -m venv venv

# Activate the virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

## Configuration

The Cylestio Local Server can be configured using environment variables or a `.env` file in the root directory.

### Create a .env File (Optional)

```bash
# Create a .env file in the root directory
touch .env
```

Edit the `.env` file with your preferred settings:

```
# Server settings
HOST=0.0.0.0
PORT=8000
DEBUG=false

# Database settings
DATABASE_URL=sqlite:///cylestio_telemetry.db

# API settings
API_PREFIX=/api
RATE_LIMIT_PER_MINUTE=100

# Logging settings
LOG_LEVEL=INFO
```

### Configuration Options

| Option | Description | Default |
|--------|-------------|---------|
| `HOST` | Server host address | `0.0.0.0` |
| `PORT` | Server port | `8000` |
| `DEBUG` | Enable debug mode | `false` |
| `DATABASE_URL` | Database connection string | `sqlite:///cylestio_telemetry.db` |
| `API_PREFIX` | Prefix for API routes | `/api` |
| `RATE_LIMIT_PER_MINUTE` | API rate limit per client | `100` |
| `LOG_LEVEL` | Logging level | `INFO` |

## Running the Server

Start the server using uvicorn:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000
```

If you want to enable hot reloading during development:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8000 --reload
```

## Verifying the Installation

1. Open your browser and navigate to:
   ```
   http://localhost:8000/docs
   ```

   This will open the Swagger UI documentation where you can explore and test the API.

2. Test the health endpoint:
   ```bash
   curl http://localhost:8000/v1/health
   ```

   You should see a response like:
   ```json
   {"status":"ok"}
   ```

## Database Initialization

The database is automatically created and initialized on first run. By default, a SQLite database file (`cylestio_telemetry.db`) will be created in the root directory.

If you want to use a different database, update the `DATABASE_URL` in your `.env` file. The server supports SQLite, PostgreSQL, and MySQL.

Examples:
```
# PostgreSQL
DATABASE_URL=postgresql://username:password@localhost:5432/cylestio

# MySQL
DATABASE_URL=mysql://username:password@localhost:3306/cylestio
```

## Next Steps

Now that you have the Cylestio Local Server up and running, you can:

1. [Submit telemetry events](../api/telemetry-submit.md) from your applications
2. [Query metrics](../api/metrics-dashboard.md) to analyze agent performance
3. Explore [usage examples](../examples/README.md) to integrate with your AI agents

## Troubleshooting

### Common Issues

#### Import Error

If you see an error like `ModuleNotFoundError: No module named 'src'`, make sure you're running the server from the project root directory.

#### Database Connection Error

If you experience database connection issues, verify that:
- The database URL is correct
- You have the necessary permissions to create/access the database
- Required database drivers are installed (e.g., `psycopg2` for PostgreSQL)

#### Port Already in Use

If port 8000 is already in use, you can specify a different port:

```bash
uvicorn src.main:app --host 0.0.0.0 --port 8001
```

### Getting Help

If you encounter any issues that aren't covered here, please:

1. Check the [GitHub issues](https://github.com/cylestio/cylestio-local-server/issues) to see if it's a known problem
2. Open a new issue if needed, providing details about your environment and the error you're experiencing 