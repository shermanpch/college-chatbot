#!/bin/bash

# College Chatbot - Docker Deployment Script
# This script automates the Docker build and deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
IMAGE_NAME="college-chatbot"
CONTAINER_NAME="college-chatbot-container"
PORT="8000"

# Determine if sudo is needed for Docker
DOCKER_CMD="docker"
if ! docker ps &> /dev/null 2>&1; then
    if sudo docker ps &> /dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
        print_warning() {
            echo -e "${YELLOW}[WARNING]${NC} Using sudo for Docker commands. You may be prompted for your password."
        }
        print_warning
    else
        echo "Cannot access Docker daemon with or without sudo. Please check Docker installation."
        exit 1
    fi
fi

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

# Function to check if Docker is installed
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        echo "Run: sudo apt update && sudo apt install -y docker.io"
        exit 1
    fi

    # Test Docker access (already done above to set DOCKER_CMD)
    print_success "Docker is available"
}

# Function to load and validate .env file
load_and_validate_env() {
    # Check if .env file exists
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        echo ""
        echo "To set up your environment:"
        echo "  1. Copy the example file: cp example.env .env"
        echo "  2. Edit .env with your API credentials"
        echo "  3. Run this script again"
        echo ""
        echo "Required variables in .env:"
        echo "  OPENROUTER_API_KEY=your_api_key_here"
        echo "  OPENROUTER_SELF_RETRIEVAL_MODEL=openai/gpt-4o-mini"
        exit 1
    fi

    print_status "Loading environment variables from .env file..."
    
    # Export variables from .env file (ignore comments and empty lines)
    set -a
    source .env
    set +a
    
    print_success "Environment variables loaded from .env file"

    # Validate required variables
    local missing_vars=()

    if [ -z "$OPENROUTER_API_KEY" ]; then
        missing_vars+=("OPENROUTER_API_KEY")
    fi

    if [ -z "$OPENROUTER_SELF_RETRIEVAL_MODEL" ]; then
        missing_vars+=("OPENROUTER_SELF_RETRIEVAL_MODEL")
    fi

    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Required environment variables are missing from .env file: ${missing_vars[*]}"
        echo ""
        echo "Please add the missing variables to your .env file:"
        for var in "${missing_vars[@]}"; do
            echo "  ${var}=your_value_here"
        done
        echo ""
        echo "You can use example.env as a reference."
        exit 1
    fi
    
    print_success "All required environment variables are set"
}

# Function to stop and remove existing container
cleanup_existing() {
    if $DOCKER_CMD ps -a --format '{{.Names}}' | grep -q "^${CONTAINER_NAME}$"; then
        print_status "Stopping and removing existing container..."
        $DOCKER_CMD stop $CONTAINER_NAME 2>/dev/null || true
        $DOCKER_CMD rm $CONTAINER_NAME 2>/dev/null || true
        print_success "Cleaned up existing container"
    fi
}

# Function to build Docker image
build_image() {
    print_status "Building Docker image..."
    if $DOCKER_CMD build -t $IMAGE_NAME . ; then
        print_success "Docker image built successfully"
    else
        print_error "Failed to build Docker image"
        exit 1
    fi
}

# Function to run container
run_container() {
    print_status "Starting container..."

    if $DOCKER_CMD run -d \
        -p $PORT:$PORT \
        -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
        -e OPENROUTER_SELF_RETRIEVAL_MODEL="$OPENROUTER_SELF_RETRIEVAL_MODEL" \
        --name $CONTAINER_NAME \
        $IMAGE_NAME; then
        print_success "Container started successfully"
        print_success "Application is accessible at: http://localhost:$PORT"
    else
        print_error "Failed to start container"
        exit 1
    fi
}

# Function to show container status
show_status() {
    echo ""
    print_status "Container status:"
    $DOCKER_CMD ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    echo ""
    print_status "To view logs, run:"
    echo "./deploy.sh --logs"
    echo "Or: $DOCKER_CMD logs $CONTAINER_NAME"

    echo ""
    print_status "To follow logs in real-time, run:"
    echo "$DOCKER_CMD logs -f $CONTAINER_NAME"

    echo ""
    print_status "To stop the container, run:"
    echo "./deploy.sh --stop"
    echo "Or: $DOCKER_CMD stop $CONTAINER_NAME"
}

# Main deployment function
main() {
    echo "============================================"
    echo "  College Chatbot Deployment"
    echo "============================================"

    # Check prerequisites
    check_docker
    
    # Load and validate environment variables from .env file
    load_and_validate_env

    # Clean up any existing deployment
    cleanup_existing

    # Build and run
    build_image
    run_container

    # Show status
    show_status

    print_success "Deployment completed successfully!"
}

# Show help
show_help() {
    echo "College Chatbot - Docker Deployment Script"
    echo ""
    echo "Usage:"
    echo "  ./deploy.sh                      - Deploy the application"
    echo "  ./deploy.sh --help               - Show this help message"
    echo "  ./deploy.sh --logs               - Show container logs"
    echo "  ./deploy.sh --stop               - Stop the container"
    echo "  ./deploy.sh --status             - Show container status"
    echo "  ./deploy.sh --deploy-with-proxy  - Deploy app and setup reverse proxy"
    echo ""
    echo "Environment Setup:"
    echo "  This script requires a .env file with your API credentials."
    echo ""
    echo "  Required variables in .env:"
    echo "    OPENROUTER_API_KEY=your_api_key_here"
    echo "    OPENROUTER_SELF_RETRIEVAL_MODEL=openai/gpt-4o-mini"
    echo ""
    echo "Setup Steps:"
    echo "  1. Copy the example environment file:"
    echo "     cp example.env .env"
    echo "  2. Edit .env with your API credentials"
    echo "  3. Run the deployment script:"
    echo "     ./deploy.sh"
    echo ""
    echo "Reverse Proxy Setup:"
    echo "  For production deployment with a custom domain:"
    echo "  1. Configure DNS records to point your domain to this server"
    echo "  2. Add DOMAIN and SSL_EMAIL to your .env file:"
    echo "     DOMAIN=your-domain.com"
    echo "     SSL_EMAIL=your-email@example.com"
    echo "  3. Run: ./deploy.sh --deploy-with-proxy"
    echo "  4. Follow the prompts to configure SSL certificates"
    echo ""
    echo "Note: This script automatically detects if sudo is needed for Docker commands."
}

# Function to validate reverse proxy configuration
validate_proxy_config() {
    local missing_vars=()
    local warnings=()

    # Check if production deployment variables are set
    if [ -z "$DOMAIN" ] || [ "$DOMAIN" = "college-coach.dev" ]; then
        warnings+=("DOMAIN is not set or using default value")
    fi

    if [ -z "$SSL_EMAIL" ] || [ "$SSL_EMAIL" = "your-email@example.com" ]; then
        warnings+=("SSL_EMAIL is not set or using example value")
    fi

    if [ ${#warnings[@]} -gt 0 ]; then
        print_warning "Production deployment configuration warnings:"
        for warning in "${warnings[@]}"; do
            echo "  - ${warning}"
        done
        echo ""
        echo "Please update your .env file with your actual domain and email:"
        echo "  DOMAIN=your-domain.com"
        echo "  SSL_EMAIL=your-email@example.com"
        echo ""
        echo "The setup script will prompt you for these values if not set."
        echo ""
    fi
}

# Function to setup reverse proxy
setup_reverse_proxy() {
    print_status "Setting up reverse proxy..."
    
    validate_proxy_config
    
    if [ ! -f "setup-reverse-proxy.sh" ]; then
        print_error "setup-reverse-proxy.sh not found!"
        print_error "Please ensure the reverse proxy setup script is in the same directory."
        exit 1
    fi
    
    # Make the script executable
    chmod +x setup-reverse-proxy.sh
    
    if [ "$EUID" -eq 0 ]; then
        print_status "Running reverse proxy setup as root..."
        if ./setup-reverse-proxy.sh; then
            print_success "Reverse proxy setup completed successfully"
        else
            print_error "Reverse proxy setup failed. Check the logs above for details."
            print_warning "You can try running the setup manually with: sudo ./setup-reverse-proxy.sh"
            exit 1
        fi
    else
        print_status "Running reverse proxy setup with sudo..."
        if sudo ./setup-reverse-proxy.sh; then
            print_success "Reverse proxy setup completed successfully"
        else
            print_error "Reverse proxy setup failed. Check the logs above for details."
            print_warning "You can try running the setup manually with: sudo ./setup-reverse-proxy.sh"
            exit 1
        fi
    fi
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --logs)
        $DOCKER_CMD logs $CONTAINER_NAME
        exit 0
        ;;
    --stop)
        print_status "Stopping container..."
        $DOCKER_CMD stop $CONTAINER_NAME
        print_success "Container stopped"
        exit 0
        ;;
    --status)
        show_status
        exit 0
        ;;
    --deploy-with-proxy)
        main
        setup_reverse_proxy
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
