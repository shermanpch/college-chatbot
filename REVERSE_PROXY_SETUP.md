# Reverse Proxy Setup Guide

This guide helps you set up a reverse proxy with Nginx and SSL certificates for your college chatbot domain `www.college-coach.dev`.

## Prerequisites

1. **Domain Configuration**: Your domain should point to your droplet's IP address
2. **Running Application**: Your chatbot should be running on port 8000
3. **Root Access**: You'll need sudo privileges on your droplet

## Quick Setup

### Step 1: Configure DNS Records

In your domain registrar's DNS settings, add these A records:
- `college-coach.dev` → your_droplet_ip
- `www.college-coach.dev` → your_droplet_ip

**Wait 5-10 minutes** for DNS propagation.

### Step 2: Run the Setup Script

1. Upload the `setup-reverse-proxy.sh` script to your droplet
2. Make it executable: `chmod +x setup-reverse-proxy.sh`
3. Run the script: `sudo ./setup-reverse-proxy.sh`

The script will:
- Install Nginx and Certbot
- Configure reverse proxy
- Obtain SSL certificates from Let's Encrypt
- Set up automatic certificate renewal
- Configure firewall rules

### Step 3: Deploy Your Application

Make sure your chatbot is running:
```bash
./deploy.sh
```

### Step 4: Test Your Domain

Visit `https://www.college-coach.dev` in your browser.

## Manual Setup (Alternative)

If you prefer to set up manually:

### 1. Install Nginx and Certbot

```bash
sudo apt update
sudo apt install -y nginx certbot python3-certbot-nginx
sudo systemctl enable nginx
sudo systemctl start nginx
```

### 2. Create Nginx Configuration

```bash
sudo nano /etc/nginx/sites-available/college-coach.dev
```

Add this configuration:

```nginx
server {
    listen 80;
    server_name college-coach.dev www.college-coach.dev;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # Proxy settings
    location / {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_cache_bypass $http_upgrade;
        
        # WebSocket support (important for Chainlit)
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        
        # Timeout settings
        proxy_connect_timeout 60s;
        proxy_send_timeout 60s;
        proxy_read_timeout 60s;
    }

    # Health check endpoint
    location /health {
        access_log off;
        return 200 "healthy\n";
        add_header Content-Type text/plain;
    }
}
```

### 3. Enable the Site

```bash
sudo ln -s /etc/nginx/sites-available/college-coach.dev /etc/nginx/sites-enabled/
sudo rm -f /etc/nginx/sites-enabled/default
sudo nginx -t
sudo systemctl reload nginx
```

### 4. Configure Firewall

```bash
sudo ufw allow 'Nginx Full'
sudo ufw allow OpenSSH
```

### 5. Obtain SSL Certificate

```bash
sudo certbot --nginx -d college-coach.dev -d www.college-coach.dev
```

Follow the prompts and provide your email address.

### 6. Set Up Auto-Renewal

```bash
sudo crontab -e
```

Add this line:
```
0 12 * * * /usr/bin/certbot renew --quiet
```

## Troubleshooting

### Common Issues

#### 1. "502 Bad Gateway" Error

**Cause**: Your application isn't running on port 8000.

**Solution**:
```bash
# Check if your app is running
curl http://localhost:8000

# If not running, start it
./deploy.sh

# Check Docker containers
docker ps
```

#### 2. "SSL Certificate Error"

**Cause**: DNS not propagated or pointing to wrong IP.

**Solution**:
```bash
# Check DNS propagation
dig college-coach.dev
dig www.college-coach.dev

# Should return your droplet's IP address
curl http://checkip.amazonaws.com/  # Your server's IP
```

#### 3. Domain Not Loading

**Cause**: Nginx not running or misconfigured.

**Solution**:
```bash
# Check Nginx status
sudo systemctl status nginx

# Check Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Test configuration
sudo nginx -t

# Restart Nginx
sudo systemctl restart nginx
```

#### 4. WebSocket Connection Issues

**Cause**: Proxy headers not properly configured.

**Solution**: Ensure your Nginx config includes WebSocket headers (already included in the script).

### Useful Commands

```bash
# Check Nginx status
sudo systemctl status nginx

# View Nginx access logs
sudo tail -f /var/log/nginx/access.log

# View Nginx error logs
sudo tail -f /var/log/nginx/error.log

# Test SSL certificate renewal
sudo certbot renew --dry-run

# Check certificate status
sudo certbot certificates

# Restart services
sudo systemctl restart nginx
sudo systemctl restart docker

# Check open ports
sudo netstat -tlnp | grep :80
sudo netstat -tlnp | grep :443
sudo netstat -tlnp | grep :8000
```

### Testing Your Setup

1. **HTTP Redirect Test**:
   ```bash
   curl -I http://college-coach.dev
   # Should return 301 or 302 redirect to HTTPS
   ```

2. **HTTPS Test**:
   ```bash
   curl -I https://college-coach.dev
   # Should return 200 OK
   ```

3. **Application Test**:
   ```bash
   curl https://college-coach.dev/health
   # Should return "healthy"
   ```

## Security Considerations

The setup includes:
- SSL/TLS encryption via Let's Encrypt
- Security headers (X-Frame-Options, etc.)
- Automatic certificate renewal
- Firewall configuration

## Next Steps

After successful setup:

1. **Monitor Your Application**: Set up monitoring for your chatbot
2. **Backup Strategy**: Consider backing up your SSL certificates and Nginx config
3. **Performance**: Monitor your application's performance and consider adding caching if needed
4. **Updates**: Keep your system and Docker images updated

## Support

If you encounter issues:

1. Check the troubleshooting section above
2. Review Nginx error logs: `sudo tail -f /var/log/nginx/error.log`
3. Ensure your Docker container is running: `docker ps`
4. Verify DNS configuration: `dig college-coach.dev`

Your chatbot should now be accessible at:
- 🌐 https://college-coach.dev
- 🌐 https://www.college-coach.dev 