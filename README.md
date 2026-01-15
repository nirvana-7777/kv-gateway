# If you're in the terminal where you got this response, you can:
echo "# Hex Key-Value Store API

A lightweight REST API for storing and retrieving hex-encoded key-value pairs using Redis as the backend storage.

## Features

- **Simple Key-Value Operations**: PUT and GET endpoints for individual key-value pairs
- **Bulk Operations**: Efficient bulk insertion of multiple key-value pairs
- **Health Monitoring**: Built-in health check endpoint
- **Redis Integration**: Robust connection handling with Redis as persistent storage
- **Docker Compose**: Easy deployment with containerized services
- **Input Validation**: Strict validation for 32-character hexadecimal keys and values

## API Endpoints

### \`PUT /{key}\`
Store a single key-value pair.

**Request:**
- Path parameter: \`key\` (32-character hex string)
- Body: \`value\` (32-character hex string)

**Response:**
- \`201 Created\`: Successfully stored

**Example:**
\`\`\`bash
curl -X PUT http://localhost:7776/abc123def456abc123def456abc123de \\
  -d \"fedcba9876543210fedcba9876543210\"
\`\`\`

### \`GET /{key}\`
Retrieve a value by its key.

**Request:**
- Path parameter: \`key\` (32-character hex string)

**Response:**
- \`200 OK\`: Returns the hex value
- \`404 Not Found\`: Key doesn't exist

**Example:**
\`\`\`bash
curl http://localhost:7776/abc123def456abc123def456abc123de
\`\`\`

### \`POST /bulk\`
Store multiple key-value pairs in a single operation.

**Request:**
- Body: JSON object with key-value pairs (both must be 32-character hex strings)

**Response:**
- \`200 OK\`: Returns count of stored items

**Example:**
\`\`\`bash
curl -X POST http://localhost:7776/bulk \\
  -H \"Content-Type: application/json\" \\
  -d '{
    \"key1abc123def456abc123def456abc12\": \"val1fedcba9876543210fedcba98765432\",
    \"key2abc123def456abc123def456abc12\": \"val2fedcba9876543210fedcba98765432\"
  }'
\`\`\`

### \`GET /health\`
Check API and Redis connection status.

**Response:**
- \`200 OK\`: Returns \`{\"status\": \"ok\"}\` if Redis is available
- \`503 Service Unavailable\`: Redis is not reachable

## Deployment

### Prerequisites
- Docker and Docker Compose

### Configuration
Environment variables (set in \`docker-compose.yml\` or \`.env\` file):

| Variable | Description | Default |
|----------|-------------|---------|
| \`REDIS_HOST\` | Redis server hostname | \`redis\` |
| \`REDIS_PORT\` | Redis server port | \`6379\` |
| \`REDIS_PASSWORD\` | Redis authentication password | (empty) |
| \`APP_PORT\` | API server port | \`7776\` |

### Quick Start
1. Clone the repository
2. Navigate to the project directory
3. Start the services:
\`\`\`bash
docker-compose up -d
\`\`\`

The API will be available at \`http://localhost:7776\`.

### Redis Configuration
The Redis instance is configured with:
- 2GB memory limit with LRU eviction policy
- Append-only file persistence
- Optional password authentication
- Data persistence via Docker volume

## Data Format

Both keys and values must be:
- 32-character hexadecimal strings (128-bit equivalent)
- Case-insensitive (stored as lowercase)
- Validated using regex pattern: \`^[A-Fa-f0-9]{32}$\`

**Examples of valid input:**
- \`abc123def456abc123def456abc123de\`
- \`ABCDEF1234567890ABCDEF1234567890\`
- \`00000000000000000000000000000000\`

## Error Handling

| HTTP Status | Description |
|-------------|-------------|
| 400 Bad Request | Invalid hex format or empty payload |
| 404 Not Found | Key doesn't exist in Redis |
| 503 Service Unavailable | Redis connection failed |

## Development

### Project Structure
\`\`\`
├── main.py              # FastAPI application
├── docker-compose.yml   # Service orchestration
├── Dockerfile           # API container definition
└── requirements.txt     # Python dependencies
\`\`\`

### Building Locally
\`\`\`bash
# Build and run with Docker Compose
docker-compose up --build

# Run tests (example with curl)
curl http://localhost:7776/health
\`\`\`

## Security Considerations

1. **Redis Authentication**: Set \`REDIS_PASSWORD\` environment variable for production
2. **Input Validation**: All keys and values are strictly validated
3. **Network Isolation**: Services communicate through internal Docker network
4. **Resource Limits**: Redis memory is limited to prevent exhaustion

## Monitoring

- Health endpoint at \`/health\`
- Docker Compose health check integration
- Logs mounted to \`../logs\` directory

## Limitations

- Single Redis instance (no clustering)
- No built-in authentication for API endpoints
- 2GB memory limit on Redis (configurable)
- Values limited to 32-character hex strings

## License

[Specify your license here]" > README.md