# API Documentation

**REST API reference and guides**

## Overview

The Kidney Genetics Database provides a RESTful API following JSON:API conventions. The API supports gene querying, annotation retrieval, and administrative operations.

## Documentation in This Section

- **[Overview](overview.md)** - API design and conventions
- **[Authentication](authentication.md)** - Auth and authorization
- **[WebSockets](websockets.md)** - Real-time progress updates
- **[Endpoints](endpoints/)** - Detailed endpoint documentation
  - [Genes API](endpoints/genes.md)
  - [Annotations API](endpoints/annotations.md)
  - [Admin API](endpoints/admin.md)
  - [Pipeline API](endpoints/pipeline.md)

## Base URL

```
Development: http://localhost:8000/api
Production: TBD
```

## Authentication

Most GET endpoints are public. POST/PUT/DELETE operations require JWT authentication.

```bash
# Login
curl -X POST http://localhost:8000/api/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email": "user@example.com", "password": "password"}'

# Use token
curl http://localhost:8000/api/admin/users \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Interactive Documentation

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Quick Examples

### Get All Genes
```bash
curl http://localhost:8000/api/genes
```

### Get Gene Details
```bash
curl http://localhost:8000/api/genes/PKD1
```

### Filter by Score
```bash
curl "http://localhost:8000/api/genes?min_score=80&max_score=100"
```

### Trigger Pipeline Update
```bash
curl -X POST http://localhost:8000/api/datasources/pubtator/update?mode=smart \
  -H "Authorization: Bearer YOUR_TOKEN"
```

## Response Format

All responses follow JSON:API specification:

```json
{
  "data": [...],
  "meta": {
    "total": 571,
    "page": 1,
    "per_page": 50
  }
}
```

## Rate Limiting

- Public endpoints: 100 requests/minute
- Authenticated endpoints: 1000 requests/minute
- Admin endpoints: No limit

## Error Handling

Standard HTTP status codes:
- `200` - Success
- `400` - Bad Request
- `401` - Unauthorized
- `404` - Not Found
- `500` - Server Error

## WebSocket Support

Real-time progress updates via WebSocket:

```javascript
const ws = new WebSocket('ws://localhost:8000/api/progress/ws');
ws.onmessage = (event) => {
  const progress = JSON.parse(event.data);
  console.log(progress);
};
```

## Related Documentation

- [Architecture](../architecture/backend/) - Backend design
- [Features](../features/) - Feature documentation
- [Authentication](../features/user-authentication.md) - Auth system