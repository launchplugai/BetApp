#!/bin/bash
# SSL setup script for DNA Matrix
# Run this after DNS is pointed to this server

DOMAIN="dna.launchplugai.com"
EMAIL="launchplugai@gmail.com"

echo "Setting up SSL for $DOMAIN..."
echo "Make sure DNS A record points to 187.77.211.80 first!"

# Create webroot for certbot
mkdir -p /tmp/certbot

# Run certbot (manual mode since we can't bind to 80/443 easily)
/home/linuxbrew/.linuxbrew/bin/certbot certonly \
    --standalone \
    --preferred-challenges http \
    -d "$DOMAIN" \
    --agree-tos \
    -m "$EMAIL" \
    --no-eff-email \
    --http-01-port 8080 \
    --force-interactive

echo "SSL setup complete. Update nginx config with the certificate paths."
