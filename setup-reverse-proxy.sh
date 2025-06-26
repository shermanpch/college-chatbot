#!/bin/bash

# College Chatbot - Reverse Proxy Setup Script
# This script sets up Nginx reverse proxy with SSL for college-coach.dev

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration - Load from environment variables or use defaults
DOMAIN="${DOMAIN:-college-coach.dev}"
WWW_DOMAIN="${WWW_DOMAIN:-www.$DOMAIN}"
APP_PORT="${PORT:-8000}"
EMAIL="${SSL_EMAIL:-your-email@example.com}"

# Note: These values are loaded from your .env file:
# - DOMAIN: Your main domain (e.g., "yourdomain.com")
# - WWW_DOMAIN: Your www subdomain (defaults to www.DOMAIN if not set)
# - PORT: Port your application runs on (default: 8000)
# - SSL_EMAIL: Your email for Let's Encrypt certificates

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to load environment variables
load_env_file() {
    if [ -f ".env" ]; then
        print_status "Loading environment variables from .env file..."
        # Export variables from .env file (ignore comments and empty lines)
        set -a
        source .env
        set +a
        
        # Update configuration with loaded values
        DOMAIN="${DOMAIN:-college-coach.dev}"
        WWW_DOMAIN="${WWW_DOMAIN:-www.$DOMAIN}"
        APP_PORT="${PORT:-8000}"
        EMAIL="${SSL_EMAIL:-your-email@example.com}"
        
        print_success "Environment variables loaded"
    else
        print_warning ".env file not found, using default configuration"
    fi
}

# Function to check if running as root
check_root() {
    if [ "$EUID" -ne 0 ]; then
        print_error "This script must be run as root (use sudo)"
        exit 1
    fi
}

# Function to check if domain points to this server
check_dns() {
    print_status "Checking DNS configuration..."
    
    SERVER_IP=$(curl -s http://checkip.amazonaws.com/)
    DOMAIN_IP=$(dig +short $DOMAIN)
    WWW_DOMAIN_IP=$(dig +short $WWW_DOMAIN)
    
    print_status "Server IP: $SERVER_IP"
    print_status "Domain IP ($DOMAIN): $DOMAIN_IP"
    print_status "WWW Domain IP ($WWW_DOMAIN): $WWW_DOMAIN_IP"
    
    if [ "$SERVER_IP" != "$DOMAIN_IP" ]; then
        print_warning "Domain $DOMAIN does not point to this server"
        print_warning "Please update your DNS records before continuing"
        echo "Add this A record: $DOMAIN -> $SERVER_IP"
    fi
    
    if [ "$SERVER_IP" != "$WWW_DOMAIN_IP" ]; then
        print_warning "Domain $WWW_DOMAIN does not point to this server"
        print_warning "Please update your DNS records before continuing"
        echo "Add this A record: $WWW_DOMAIN -> $SERVER_IP"
    fi
}

# Function to install Nginx
install_nginx() {
    print_status "Installing Nginx..."
    apt update -qq
    DEBIAN_FRONTEND=noninteractive apt install -y nginx
    systemctl enable nginx
    systemctl start nginx
    print_success "Nginx installed and started"
}

# Function to install Certbot
install_certbot() {
    print_status "Installing Certbot for SSL certificates..."
    DEBIAN_FRONTEND=noninteractive apt install -y certbot python3-certbot-nginx
    print_success "Certbot installed"
}

# Function to create Nginx configuration
create_nginx_config() {
    print_status "Creating Nginx configuration..."
    
    cat > /etc/nginx/sites-available/$DOMAIN << EOF
server {
    listen 80;
    server_name $DOMAIN $WWW_DOMAIN;

    # Security headers
    add_header X-Frame-Options DENY;
    add_header X-Content-Type-Options nosniff;
    add_header X-XSS-Protection "1; mode=block";
    add_header Referrer-Policy "strict-origin-when-cross-origin";

    # Proxy settings
    location / {
        proxy_pass http://localhost:$APP_PORT;
        proxy_http_version 1.1;
        proxy_set_header Upgrade \$http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host \$host;
        proxy_set_header X-Real-IP \$remote_addr;
        proxy_set_header X-Forwarded-For \$proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto \$scheme;
        proxy_cache_bypass \$http_upgrade;
        
        # WebSocket support
        proxy_set_header Upgrade \$http_upgrade;
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
EOF

    # Enable the site
    ln -sf /etc/nginx/sites-available/$DOMAIN /etc/nginx/sites-enabled/
    
    # Remove default site if it exists
    rm -f /etc/nginx/sites-enabled/default
    
    # Test Nginx configuration
    nginx -t
    
    if [ $? -eq 0 ]; then
        print_success "Nginx configuration created and validated"
        systemctl reload nginx
    else
        print_error "Nginx configuration is invalid"
        exit 1
    fi
}

# Function to obtain SSL certificate
setup_ssl() {
    print_status "Setting up SSL certificate with Let's Encrypt..."
    
    # Check if email is set
    if [ "$EMAIL" = "your-email@example.com" ]; then
        print_error "Please update the EMAIL variable in this script with your actual email address"
        exit 1
    fi
    
    # Obtain certificate
    certbot --nginx -d $DOMAIN -d $WWW_DOMAIN --non-interactive --agree-tos --email $EMAIL --redirect
    
    if [ $? -eq 0 ]; then
        print_success "SSL certificate obtained and configured"
    else
        print_error "Failed to obtain SSL certificate"
        exit 1
    fi
}

# Function to setup automatic certificate renewal
setup_renewal() {
    print_status "Setting up automatic certificate renewal..."
    
    # Add cron job for certificate renewal
    (crontab -l 2>/dev/null; echo "0 12 * * * /usr/bin/certbot renew --quiet") | crontab -
    
    print_success "Automatic renewal configured"
}

# Function to configure firewall
configure_firewall() {
    print_status "Configuring firewall..."
    
    if command -v ufw &> /dev/null; then
        # Check if UFW is installed and available
        if ufw status >/dev/null 2>&1; then
            # Enable UFW if not already enabled (with --force to avoid prompts)
            ufw --force enable >/dev/null 2>&1 || true
            
            # Allow Nginx Full profile (HTTP and HTTPS)
            ufw allow 'Nginx Full' >/dev/null 2>&1 || ufw allow 80/tcp >/dev/null 2>&1 || true
            ufw allow 443/tcp >/dev/null 2>&1 || true
            
            # Allow SSH to prevent lockout
            ufw allow OpenSSH >/dev/null 2>&1 || ufw allow 22/tcp >/dev/null 2>&1 || true
            
            print_success "UFW firewall configured"
        else
            print_warning "UFW is not properly configured. Manually allowing ports..."
            # Fallback: try to allow ports directly
            ufw allow 80/tcp >/dev/null 2>&1 || true
            ufw allow 443/tcp >/dev/null 2>&1 || true
            ufw allow 22/tcp >/dev/null 2>&1 || true
            print_warning "Basic firewall rules applied. Please verify UFW configuration manually."
        fi
    else
        print_warning "UFW not found. Please ensure ports 80, 443, and 22 are open"
        print_warning "You may need to configure your firewall manually:"
        echo "  - Port 80 (HTTP)"
        echo "  - Port 443 (HTTPS)" 
        echo "  - Port 22 (SSH)"
    fi
}

# Function to check if app is running
check_app() {
    print_status "Checking if your application is running on port $APP_PORT..."
    
    if curl -s http://localhost:$APP_PORT > /dev/null; then
        print_success "Application is running on port $APP_PORT"
    else
        print_warning "Application is not responding on port $APP_PORT"
        print_warning "Make sure to start your Docker container before testing the domain"
        echo "Run: ./deploy.sh"
    fi
}

# Function to test the setup
test_setup() {
    print_status "Testing the setup..."
    
    # Test HTTP redirect
    HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://$DOMAIN)
    if [ "$HTTP_STATUS" = "301" ] || [ "$HTTP_STATUS" = "302" ]; then
        print_success "HTTP to HTTPS redirect is working"
    else
        print_warning "HTTP redirect test returned status: $HTTP_STATUS"
    fi
    
    # Test HTTPS
    HTTPS_STATUS=$(curl -s -o /dev/null -w "%{http_code}" https://$DOMAIN)
    if [ "$HTTPS_STATUS" = "200" ]; then
        print_success "HTTPS is working"
    else
        print_warning "HTTPS test returned status: $HTTPS_STATUS"
    fi
}

# Main function
main() {
    echo "============================================"
    echo "  College Chatbot - Reverse Proxy Setup"
    echo "============================================"
    echo ""
    
    load_env_file
    
    # Prompt for email if not set
    if [ "$EMAIL" = "your-email@example.com" ]; then
        echo "Please enter your email address for Let's Encrypt SSL certificates:"
        read -p "Email: " EMAIL
        echo ""
    fi
    
    check_root
    check_dns
    
    echo "This script will:"
    echo "  1. Install Nginx"
    echo "  2. Install Certbot for SSL certificates"
    echo "  3. Configure reverse proxy for $DOMAIN and $WWW_DOMAIN"
    echo "  4. Obtain and install SSL certificates"
    echo "  5. Set up automatic certificate renewal"
    echo "  6. Configure firewall rules"
    echo ""
    echo "Domain: $DOMAIN"
    echo "WWW Domain: $WWW_DOMAIN"
    echo "App Port: $APP_PORT"
    echo "Email: $EMAIL"
    echo ""
    
    print_status "Proceeding with automatic setup..."
    
    install_nginx
    install_certbot
    create_nginx_config
    configure_firewall
    setup_ssl
    setup_renewal
    check_app
    test_setup
    
    echo ""
    print_success "Reverse proxy setup completed successfully!"
    echo ""
    echo "Your chatbot should now be accessible at:"
    echo "  🌐 https://$DOMAIN"
    echo "  🌐 https://$WWW_DOMAIN"
    echo ""
    echo "Next steps:"
    echo "  1. Make sure your Docker container is running: ./deploy.sh"
    echo "  2. Test your domain in a browser"
    echo "  3. SSL certificates will auto-renew via cron job"
}

# Show help
show_help() {
    echo "College Chatbot - Reverse Proxy Setup Script"
    echo ""
    echo "This script sets up Nginx as a reverse proxy with SSL certificates"
    echo "for your college chatbot domain."
    echo ""
    echo "Usage:"
    echo "  sudo ./setup-reverse-proxy.sh        - Run the automated setup"
    echo "  ./setup-reverse-proxy.sh --help      - Show this help"
    echo ""
    echo "Prerequisites:"
    echo "  - Domain DNS records pointing to this server"
    echo "  - Your chatbot application running on port 8000"
    echo "  - Root access (script must be run with sudo)"
    echo ""
    echo "What this script does (automatically, no prompts):"
    echo "  1. Installs Nginx and Certbot"
    echo "  2. Configures reverse proxy to forward requests to your app"
    echo "  3. Obtains free SSL certificates from Let's Encrypt"
    echo "  4. Sets up automatic certificate renewal"
    echo "  5. Configures security headers and firewall rules"
    echo ""
    echo "Note: This script runs automatically without user prompts."
    echo "Configuration is loaded from .env file or uses defaults."
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    "")
        main
        ;;
    *)
        print_error "Unknown option: $1"
        show_help
        exit 1
        ;;
esac 