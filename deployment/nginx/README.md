# Nginx Configuration for Bridge-X-RAG

This directory contains Nginx configuration files for the Bridge-X-RAG application.

## Configuration Files

- **nginx.conf**: Optimized Nginx configuration for proxying requests to the application with enhanced performance, security, and reliability

## Production Setup

In production, Nginx serves as a reverse proxy in front of the application, handling:

- SSL termination with Let's Encrypt certificates
- HTTP to HTTPS redirection
- Request routing to the application
- Security headers and optimizations
- Performance tuning and caching
- Rate limiting and DDoS protection

## How It Works

The Nginx configuration works in conjunction with the Certbot container to provide:

1. Automatic HTTP to HTTPS redirection
2. ACME challenge handling for Let's Encrypt certificate issuance and renewal
3. Secure SSL configuration with modern ciphers and security headers
4. Proxy configuration to the Bridge-X-RAG API
5. Performance optimizations for high traffic loads
6. Security protections against common web vulnerabilities

## Optimized Configuration Overview

Our Nginx configuration has been optimized for production use with the following enhancements:

### Performance Optimizations

1. **Worker Process Configuration**
   - Automatic worker process scaling based on CPU cores
   - Increased file descriptor limits for high concurrency
   - Optimized event handling with epoll and multi_accept

2. **Connection Handling**
   - TCP optimizations with sendfile, tcp_nopush, and tcp_nodelay
   - Optimized keepalive settings for persistent connections
   - Buffer tuning for different types of content

3. **Compression**
   - Gzip compression for all compressible content types
   - Optimized compression level for balance of CPU and bandwidth
   - Conditional compression based on client capabilities

4. **Caching**
   - File descriptor caching for frequently accessed files
   - Browser caching for static assets with appropriate expires headers
   - Different cache policies for different content types

5. **HTTP/2 Support**
   - Full HTTP/2 support for multiplexed connections
   - Header compression for reduced bandwidth usage
   - Binary protocol for more efficient data transfer

### Security Enhancements

1. **SSL Hardening**
   - Modern TLS protocols (TLSv1.2, TLSv1.3) only
   - Strong cipher suite configuration
   - OCSP Stapling for certificate validation
   - SSL session cache optimization

2. **Security Headers**
   - HTTP Strict Transport Security (HSTS)
   - Content Security Policy (CSP)
   - X-Content-Type-Options
   - X-Frame-Options
   - X-XSS-Protection
   - Referrer-Policy

3. **Rate Limiting**
   - Request rate limiting to prevent abuse
   - Burst handling for legitimate traffic spikes
   - Different rate limits for different endpoints

4. **Access Control**
   - Protection for sensitive files and directories
   - Server information hiding
   - Explicit deny rules for unauthorized access

### Reliability Improvements

1. **Enhanced Logging**
   - Detailed log format with request and response information
   - Buffered logging for better performance
   - Selective logging based on content type

2. **Timeout Management**
   - Optimized timeouts for different request types
   - Shorter timeouts for health checks
   - Longer timeouts for API operations

3. **Resource Management**
   - Buffer size optimization for different content types
   - Connection pool management
   - Worker process resource allocation

## SSL Configuration

The SSL configuration is automatically set up by the `init-letsencrypt.sh` script and has been enhanced with additional security measures:

```nginx
# SSL configuration
ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
include /etc/letsencrypt/options-ssl-nginx.conf;
ssl_dhparam /etc/letsencrypt/ssl-dhparams.pem;

# Additional SSL optimizations
ssl_session_cache shared:SSL:10m;
ssl_session_timeout 1d;
ssl_session_tickets off;

# OCSP Stapling
ssl_stapling on;
ssl_stapling_verify on;
resolver 8.8.8.8 8.8.4.4 valid=300s;
resolver_timeout 5s;

# Security headers
add_header Strict-Transport-Security "max-age=63072000; includeSubDomains; preload" always;
add_header X-Content-Type-Options nosniff always;
add_header X-Frame-Options SAMEORIGIN always;
add_header X-XSS-Protection "1; mode=block" always;
add_header Referrer-Policy strict-origin-when-cross-origin always;
add_header Content-Security-Policy "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; font-src 'self'; connect-src 'self'" always;
```

## Specialized Location Blocks

The configuration includes specialized location blocks for different types of content:

### Main Application

```nginx
location / {
    # Rate limiting
    limit_req zone=api_limit burst=20 nodelay;

    # Proxy settings
    proxy_pass http://bridgex-rag-api:8000;
    proxy_http_version 1.1;
    proxy_set_header X-Real-IP $remote_addr;
    proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    proxy_set_header X-Forwarded-Proto $scheme;
    proxy_set_header Upgrade $http_upgrade;
    proxy_set_header Connection 'upgrade';
    proxy_set_header Host $http_host;
    proxy_set_header X-NginX-Proxy true;
    proxy_redirect off;

    # Buffering settings
    proxy_buffering on;
    proxy_buffer_size 16k;
    proxy_busy_buffers_size 24k;
    proxy_buffers 64 4k;

    # Timeouts
    proxy_connect_timeout 300s;
    proxy_send_timeout 300s;
    proxy_read_timeout 300s;

    # Cache control
    add_header Cache-Control "no-store, no-cache, must-revalidate, proxy-revalidate, max-age=0";
    expires off;
}
```

### Health Checks

```nginx
location /api/health {
    access_log off;
    limit_req zone=api_limit burst=5 nodelay;

    proxy_pass http://bridgex-rag-api:8000/api/health;
    proxy_http_version 1.1;
    proxy_set_header Host $host;
    proxy_set_header X-Real-IP $remote_addr;

    # Shorter timeout for health checks
    proxy_connect_timeout 5s;
    proxy_send_timeout 5s;
    proxy_read_timeout 5s;
}
```

### Static Assets

```nginx
location /static/ {
    proxy_pass http://bridgex-rag-api:8000/static/;
    expires 1d;
    add_header Cache-Control "public, max-age=86400";
}
```

### API Documentation

```nginx
location /docs {
    proxy_pass http://bridgex-rag-api:8000/docs;
    expires 1h;
    add_header Cache-Control "public, max-age=3600";
}
```

## Gzip Compression

The configuration includes optimized Gzip compression settings:

```nginx
# Gzip settings
gzip on;
gzip_vary on;
gzip_proxied any;
gzip_comp_level 6;
gzip_buffers 16 8k;
gzip_http_version 1.1;
gzip_min_length 256;
gzip_types
    application/atom+xml
    application/javascript
    application/json
    application/ld+json
    application/manifest+json
    application/rss+xml
    application/vnd.geo+json
    application/vnd.ms-fontobject
    application/x-font-ttf
    application/x-web-app-manifest+json
    application/xhtml+xml
    application/xml
    font/opentype
    image/bmp
    image/svg+xml
    image/x-icon
    text/cache-manifest
    text/css
    text/plain
    text/vcard
    text/vnd.rim.location.xloc
    text/vtt
    text/x-component
    text/x-cross-domain-policy;
```

## Rate Limiting

The configuration includes rate limiting to protect against abuse:

```nginx
# Rate limiting zone
limit_req_zone $binary_remote_addr zone=api_limit:10m rate=10r/s;

# Usage in location blocks
location / {
    limit_req zone=api_limit burst=20 nodelay;
    # Other settings...
}
```

## Customizing the Configuration

To customize the Nginx configuration:

1. Edit the `nginx.conf` file to update:
   - `server_name`: Your domain names
   - Rate limiting settings based on expected traffic
   - Proxy buffer sizes based on response sizes
   - Cache settings based on content update frequency
   - Security headers based on application requirements

2. Test the configuration:
   ```bash
   docker-compose -f docker-compose.prod.yml exec nginx nginx -t
   ```

3. Apply the changes:
   ```bash
   docker-compose -f docker-compose.prod.yml exec nginx nginx -s reload
   ```

## Performance Tuning

For further performance tuning:

1. **Adjust Worker Processes**: If your server has many CPU cores, you may want to set a specific number:
   ```nginx
   worker_processes 8;  # Set to number of CPU cores
   ```

2. **Tune Buffer Sizes**: For applications with large responses:
   ```nginx
   proxy_buffer_size 32k;
   proxy_buffers 64 8k;
   ```

3. **Adjust Rate Limits**: For high-traffic applications:
   ```nginx
   limit_req_zone $binary_remote_addr zone=api_limit:10m rate=30r/s;
   ```

4. **Enable Microcaching**: For dynamic content that doesn't change frequently:
   ```nginx
   proxy_cache_path /var/cache/nginx levels=1:2 keys_zone=microcache:10m max_size=1g inactive=60m;

   location / {
       proxy_cache microcache;
       proxy_cache_valid 200 1m;
       proxy_cache_use_stale updating error timeout invalid_header http_500 http_502 http_503 http_504;
       proxy_cache_lock on;
       # Other settings...
   }
   ```

## Troubleshooting

### Configuration Testing

To test the Nginx configuration:

```bash
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```

### Viewing Logs

To view Nginx access and error logs:

```bash
# Access logs
docker-compose -f docker-compose.prod.yml exec nginx tail -f /var/log/nginx/access.log

# Error logs
docker-compose -f docker-compose.prod.yml exec nginx tail -f /var/log/nginx/error.log
```

### Performance Analysis

To analyze Nginx performance:

```bash
# Check current connections
docker-compose -f docker-compose.prod.yml exec nginx sh -c "nginx -V && echo 'Connections:' && netstat -an | grep :443 | wc -l"

# Check Nginx status (if stub_status module is enabled)
docker-compose -f docker-compose.prod.yml exec nginx curl http://localhost/nginx_status
```

### Common Issues

1. **502 Bad Gateway**: The application container is not running or not accessible
   - Check if the application container is running: `docker ps | grep bridgex-rag-api`
   - Verify the application is listening on the correct port: `docker exec bridgex-rag-api netstat -tulpn | grep 8000`
   - Check if the proxy_pass URL is correct in the Nginx configuration

2. **SSL Certificate Issues**: Certificate not found or invalid
   - Check if certificates exist: `docker exec nginx ls -la /etc/letsencrypt/live/`
   - Verify certificate validity: `docker exec nginx openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -text -noout`
   - Check certificate expiration: `docker exec nginx openssl x509 -in /etc/letsencrypt/live/your-domain.com/fullchain.pem -noout -dates`

3. **Rate Limiting Too Strict**: Legitimate users getting 429 errors
   - Increase the rate limit: Modify `rate=10r/s` to a higher value
   - Increase burst allowance: Modify `burst=20` to a higher value
   - Consider using different rate limiting zones for different endpoints

4. **High CPU Usage**: Nginx using too much CPU
   - Check worker processes: Might be too many for your server
   - Reduce gzip compression level: Change `gzip_comp_level 6` to a lower value
   - Disable unnecessary modules in the Nginx build
