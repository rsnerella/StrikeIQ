# Upstash Redis Integration Guide

This guide explains how to integrate Upstash Redis with StrikeIQ for improved scalability and reliability.

## Overview

StrikeIQ now supports both local Redis and Upstash Redis through a unified client interface. The system automatically detects which Redis provider to use based on configuration and provides seamless fallback between providers.

## Architecture

### Unified Redis Client
- **Location**: `app/core/unified_redis_client.py`
- **Purpose**: Provides a single interface for both local Redis and Upstash Redis
- **Features**: Automatic provider selection, fallback mechanisms, comprehensive error handling

### Provider Selection
The system supports three provider modes:
- **`local`**: Force use of local Redis instance
- **`upstash`**: Force use of Upstash Redis
- **`auto`**: Automatically prefer Upstash if configured, otherwise use local Redis

## Configuration

### Environment Variables

Add these variables to your `.env` file:

```bash
# Redis Provider Selection
REDIS_PROVIDER=auto  # Options: 'local', 'upstash', 'auto'

# Upstash Redis Configuration (Optional)
UPSTASH_REDIS_URL=redis://your-upstash-redis-url:port
UPSTASH_REDIS_TOKEN=your-upstash-redis-token
UPSTASH_REDIS_REST_URL=https://your-upstash-rest-url

# Local Redis Configuration (Fallback)
REDIS_URL=redis://localhost:6379
REDIS_HOST=localhost
REDIS_PORT=6379
REDIS_DB=0
```

### Upstash Setup

1. **Create Upstash Redis Database**:
   - Go to [Upstash Console](https://console.upstash.com/)
   - Create a new Redis database
   - Note the REST URL and connection token

2. **Get Connection Details**:
   - REST URL: `https://your-db-name.upstash.io`
   - Token: Found in the database details
   - Redis URL: `redis://your-db-name.upstash.io:6379`

3. **Update Environment**:
   ```bash
   UPSTASH_REDIS_URL=redis://your-db-name.upstash.io:6379
   UPSTASH_REDIS_TOKEN=your-upstash-redis-token
   UPSTASH_REDIS_REST_URL=https://your-db-name.upstash.io
   ```

## Usage

### Basic Operations

The unified client provides the same interface as standard Redis:

```python
from app.core.unified_redis_client import unified_redis_client

# Basic operations
await unified_redis_client.set("key", "value", ex=3600)
value = await unified_redis_client.get("key")
await unified_redis_client.delete("key")

# JSON operations
await unified_redis_client.set_json("data", {"key": "value"})
data = await unified_redis_client.get_json("data")

# Hash operations
await unified_redis_client.hset("hash", "field", "value")
field_value = await unified_redis_client.hget("hash", "field")
hash_data = await unified_redis_client.hgetall("hash")

# List operations
await unified_redis_client.lpush("list", "item1", "item2")
items = await unified_redis_client.lrange("list", 0, -1)
item = await unified_redis_client.rpop("list")
```

### Provider Information

Get information about the active Redis provider:

```python
provider_info = await unified_redis_client.get_provider_info()
print(f"Active provider: {provider_info['active_provider']}")
print(f"Local available: {provider_info['local_available']}")
print(f"Upstash available: {provider_info['upstash_available']}")
```

### Health Monitoring

Use the health check endpoint to monitor Redis status:

```bash
curl http://localhost:8000/api/v1/redis/health
```

Response:
```json
{
  "status": "healthy",
  "provider": {
    "active_provider": "upstash",
    "local_available": true,
    "upstash_available": true
  },
  "connection_test": {
    "ping": true,
    "set_get_operations": true
  },
  "configuration": {
    "redis_provider": "auto",
    "upstash_enabled": true,
    "effective_redis_url": "redis://your-db.upstash.io:6379"
  }
}
```

## Migration Guide

### From Local Redis to Upstash

1. **Set Up Upstash**: Create your Upstash Redis database
2. **Update Configuration**: Add Upstash credentials to `.env`
3. **Test Integration**: Run the test script
4. **Deploy**: Update production environment variables

### Migration Steps

```bash
# 1. Test locally with Upstash
REDIS_PROVIDER=upstash
UPSTASH_REDIS_URL=redis://your-db.upstash.io:6379
UPSTASH_REDIS_TOKEN=your-token
UPSTASH_REDIS_REST_URL=https://your-db.upstash.io

# 2. Run integration tests
python test_upstash_redis_integration.py

# 3. Verify all tests pass
# 4. Update production environment
# 5. Deploy with REDIS_PROVIDER=auto for seamless fallback
```

## Testing

### Run Integration Tests

```bash
cd backend
python test_upstash_redis_integration.py
```

### Test Coverage

The test suite covers:
- ✅ Configuration validation
- ✅ Client initialization
- ✅ Basic Redis operations (SET, GET, DELETE, EXISTS)
- ✅ JSON operations
- ✅ Hash operations (HSET, HGET, HGETALL)
- ✅ List operations (LPUSH, LRANGE, RPOP)
- ✅ Provider fallback mechanisms
- ✅ Legacy compatibility

### Expected Results

- **With Local Redis Only**: 23/25 tests pass (Upstash tests expected to fail)
- **With Upstash Configured**: 25/25 tests pass
- **Legacy Code**: Continues to work without modification

## Monitoring and Debugging

### Logging

The unified client provides comprehensive logging:

```python
import logging
logging.basicConfig(level=logging.INFO)

# Logs include:
# - Provider selection
# - Connection status
# - Fallback events
# - Operation errors
```

### Health Check Endpoints

- **Redis Health**: `/api/v1/redis/health`
- **Provider Info**: `/api/v1/redis/provider`

### Diagnostics

Use the diagnostic tools to troubleshoot:

```python
from app.core.unified_redis_client import unified_redis_client

# Check provider status
info = await unified_redis_client.get_provider_info()

# Test connection
is_healthy = await unified_redis_client.ping()

# Test operations
await unified_redis_client.set("test", "value")
result = await unified_redis_client.get("test")
```

## Performance Considerations

### Upstash vs Local Redis

| Aspect | Upstash Redis | Local Redis |
|--------|---------------|-------------|
| Latency | ~10-50ms | ~1-5ms |
| Scalability | Unlimited | Limited by server |
| Reliability | 99.9% SLA | Depends on infrastructure |
| Maintenance | Managed | Self-managed |
| Cost | Pay-as-you-go | Infrastructure cost |

### Optimization Tips

1. **Use Appropriate TTL**: Set expiration for cached data
2. **Batch Operations**: Use pipelines for multiple operations
3. **Connection Pooling**: Unified client handles this automatically
4. **Monitor Usage**: Use health endpoints to track performance

## Troubleshooting

### Common Issues

1. **Upstash Connection Failed**:
   - Check REST URL and token
   - Verify network connectivity
   - Ensure correct region selection

2. **Fallback Not Working**:
   - Verify local Redis is running
   - Check configuration settings
   - Review logs for provider selection

3. **Performance Issues**:
   - Monitor latency with health checks
   - Consider data partitioning
   - Optimize key patterns

### Debug Commands

```bash
# Check configuration
python -c "from app.core.config import settings; print(f'Provider: {settings.REDIS_PROVIDER}, Upstash enabled: {settings.is_upstash_enabled}')"

# Test connection
python -c "import asyncio; from app.core.unified_redis_client import unified_redis_client; asyncio.run(unified_redis_client.initialize()); print(asyncio.run(unified_redis_client.ping()))"

# Run health check
curl http://localhost:8000/api/v1/redis/health
```

## Security

### Upstash Security

1. **Token Management**: Store tokens securely in environment variables
2. **Network Security**: Use TLS connections (handled automatically)
3. **Access Control**: Limit token permissions
4. **Monitoring**: Monitor for unusual access patterns

### Best Practices

- Never commit tokens to version control
- Rotate tokens regularly
- Use read-only tokens where possible
- Monitor Redis usage and costs

## Production Deployment

### Environment Setup

```bash
# Production environment variables
REDIS_PROVIDER=auto
UPSTASH_REDIS_URL=redis://prod-db.upstash.io:6379
UPSTASH_REDIS_TOKEN=prod-token
UPSTASH_REDIS_REST_URL=https://prod-db.upstash.io
REDIS_URL=redis://localhost:6379  # Fallback
```

### Deployment Checklist

- [ ] Upstash database created
- [ ] Environment variables configured
- [ ] Integration tests passing
- [ ] Health monitoring enabled
- [ ] Backup strategy in place
- [ ] Cost monitoring set up
- [ ] Security review completed

### Monitoring

Set up monitoring for:
- Redis connection health
- Operation latency
- Error rates
- Provider fallback events
- Cost usage (Upstash)

## Support

### Getting Help

1. **Check Logs**: Review application logs for errors
2. **Run Tests**: Use the integration test suite
3. **Health Checks**: Monitor Redis health endpoints
4. **Documentation**: Refer to Upstash and Redis documentation

### Resources

- [Upstash Documentation](https://docs.upstash.com/)
- [Redis Documentation](https://redis.io/documentation)
- [StrikeIQ GitHub](https://github.com/your-org/strikeiq)

---

**Note**: This integration maintains full backward compatibility. Existing code using Redis will continue to work without modification.
