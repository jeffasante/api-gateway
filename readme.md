# API Gateway

A Django-based API Gateway service with rate limiting, monitoring, and logging capabilities.

## Project Overview

This API Gateway serves as a central point for handling API requests, implementing:
- Rate limiting with Redis
- Request/Response logging
- Health monitoring
- Prometheus metrics (optional)
- Custom middleware for request processing

## Project Structure
```
api_gateway/
├── api_gateway/
│   ├── __init__.py
│   ├── asgi.py
│   ├── middleware.py
│   ├── settings.py
│   ├── urls.py
│   └── wsgi.py
├── api-endpoints.md
├── manage.py
├── requirements.txt
├── Dockerfile
└── docker-compose.yml
```

## Prerequisites

- Docker and Docker Compose
- Python 3.9+
- Redis (handled by Docker Compose)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/jeffasante/api-gateway.git
cd api_gateway
```

2. Build and start the services:
```bash
docker-compose up --build -d
```

## Available Endpoints

For detailed endpoint documentation, see [api-endpoints.md](api-endpoints.md)

- Health Check: `GET /health/`
- Test Endpoint: `GET /test/`

## Configuration

### Environment Variables

- `DJANGO_SETTINGS_MODULE`: Set to `api_gateway.settings`
- `REDIS_URL`: Redis connection string (default: `redis://redis:6379/1`)

### Rate Limiting

Current rate limits:
- Authenticated users: 100,000 requests/day
- Anonymous users: 1,000 requests/day

Configure in `middleware.py`:
```python
self.rate_limits = {
    'authenticated': {'limit': 100000, 'window': 86400},  # 100K/day
    'anonymous': {'limit': 1000, 'window': 86400},       # 1K/day
}
```

## Development

1. Start services in development mode:
```bash
docker-compose up
```

2. Run tests:
```bash
docker-compose exec api_gateway python manage.py test
```

3. Check logs:
```bash
docker-compose logs -f api_gateway
```

## Production Deployment

For production:

1. Update `settings.py`:
   - Set `DEBUG = False`
   - Configure `ALLOWED_HOSTS`
   - Update `SECRET_KEY`

2. Use proper SSL/TLS termination
3. Configure proper logging
4. Set up monitoring

## Monitoring

The API Gateway includes:
- Request latency metrics
- Rate limit tracking
- Error logging
- Response time headers

## Contributing

1. Fork the repository
2. Create your feature branch
3. Submit a pull request

## License
MIT License

Copyright (c) 2024 Jeff Asante
