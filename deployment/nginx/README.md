# Nginx Configuration for Bridge-X-RAG

This directory contains Nginx configuration files for the Bridge-X-RAG application.

## Configuration Files

- **default.conf**: Basic Nginx configuration for proxying requests to the application

## Production Setup

In production, Nginx serves as a reverse proxy in front of the application, handling:

- SSL termination
- Static file serving
- Request routing
- Load balancing (if multiple application instances are deployed)

## SSL Configuration

For production deployment with SSL:

1. Replace the server_name with your actual domain name
2. Set up SSL certificates using Let's Encrypt or another provider
3. Update the Nginx configuration to use SSL

Example SSL configuration:

```nginx
server {
    listen 80;
    server_name yourdomain.com;
    return 301 https://$host$request_uri;
}

server {
    listen 443 ssl;
    server_name yourdomain.com;

    ssl_certificate /etc/letsencrypt/live/yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/yourdomain.com/privkey.pem;
    
    # SSL configuration
    ssl_protocols TLSv1.2 TLSv1.3;
    ssl_prefer_server_ciphers on;
    ssl_ciphers ECDHE-ECDSA-AES128-GCM-SHA256:ECDHE-RSA-AES128-GCM-SHA256:ECDHE-ECDSA-AES256-GCM-SHA384:ECDHE-RSA-AES256-GCM-SHA384:ECDHE-ECDSA-CHACHA20-POLY1305:ECDHE-RSA-CHACHA20-POLY1305:DHE-RSA-AES128-GCM-SHA256:DHE-RSA-AES256-GCM-SHA384;
    ssl_session_cache shared:SSL:10m;
    ssl_session_timeout 1d;
    ssl_session_tickets off;

    # HSTS
    add_header Strict-Transport-Security "max-age=63072000" always;

    # Proxy to application
    location / {
        proxy_pass http://web:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    # Other locations...
}
```

## Testing Nginx Configuration

To test the Nginx configuration:

```bash
docker-compose -f docker-compose.prod.yml exec nginx nginx -t
```
