#!/bin/bash

# College Chatbot - Docker Compose Deployment Script
# This script automates the Docker Compose build and deployment process

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Determine if sudo is needed for Docker
DOCKER_CMD="docker"
if ! docker ps &> /dev/null 2>&1; then
    if sudo docker ps &> /dev/null 2>&1; then
        DOCKER_CMD="sudo docker"
        echo -e "${YELLOW}[WARNING]${NC} Using sudo for Docker commands. You may be prompted for your password."
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

# Function to check if Docker and Docker Compose are available
check_docker() {
    if ! command -v docker &> /dev/null; then
        print_error "Docker is not installed. Please install Docker first."
        exit 1
    fi

    if ! $DOCKER_CMD compose version &> /dev/null; then
        print_error "Docker Compose v2 is required. Please update Docker."
        exit 1
    fi

    print_success "Docker and Docker Compose are available"
}

# Function to load and validate .env file
load_and_validate_env() {
    if [ ! -f ".env" ]; then
        print_error ".env file not found!"
        echo ""
        echo "To set up your environment:"
        echo "  1. Copy the example file: cp .env.example .env"
        echo "  2. Edit .env with your API credentials and tunnel token"
        echo "  3. Run this script again"
        echo ""
        echo "Required variables in .env:"
        echo "  OPENROUTER_API_KEY=your_api_key_here"
        echo "  OPENROUTER_SELF_RETRIEVAL_MODEL=openai/gpt-4o-mini"
        echo "  TUNNEL_TOKEN=your_tunnel_token_here"
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

    if [ -z "$TUNNEL_TOKEN" ]; then
        missing_vars+=("TUNNEL_TOKEN")
    fi

    if [ ${#missing_vars[@]} -gt 0 ]; then
        print_error "Required environment variables are missing from .env file: ${missing_vars[*]}"
        echo ""
        echo "Please add the missing variables to your .env file:"
        for var in "${missing_vars[@]}"; do
            echo "  ${var}=your_value_here"
        done
        echo ""
        echo "You can use .env.example as a reference."
        exit 1
    fi

    print_success "All required environment variables are set"
}

# Function to show container status
show_status() {
    echo ""
    print_status "Service status:"
    $DOCKER_CMD compose ps
    echo ""
    print_status "Useful commands:"
    echo "  ./deploy.sh --logs          View logs from all services"
    echo "  ./deploy.sh --follow-logs   Follow logs in real-time"
    echo "  ./deploy.sh --stop          Stop all services"
    echo "  ./deploy.sh --down          Stop and remove all containers"
    echo "  ./deploy.sh --status        Show service status"
}

# Main deployment function
main() {
    echo "============================================"
    echo "  College Chatbot Deployment"
    echo "============================================"

    check_docker
    load_and_validate_env

    print_status "Building and starting services..."
    $DOCKER_CMD compose up -d --build

    print_success "Services started successfully"
    show_status
    print_success "Deployment completed!"
}

# Show help
show_help() {
    echo "College Chatbot - Docker Compose Deployment Script"
    echo ""
    echo "Usage:"
    echo "  ./deploy.sh                - Build and start all services (app + tunnel)"
    echo "  ./deploy.sh --help         - Show this help message"
    echo "  ./deploy.sh --logs         - Show logs from all services"
    echo "  ./deploy.sh --follow-logs  - Follow logs in real-time"
    echo "  ./deploy.sh --stop         - Stop all services"
    echo "  ./deploy.sh --down         - Stop and remove all containers"
    echo "  ./deploy.sh --status       - Show service status"
    echo ""
    echo "Environment Setup:"
    echo "  This script requires a .env file with your credentials."
    echo ""
    echo "  Required variables in .env:"
    echo "    OPENROUTER_API_KEY=your_api_key_here"
    echo "    OPENROUTER_SELF_RETRIEVAL_MODEL=openai/gpt-4o-mini"
    echo "    TUNNEL_TOKEN=your_tunnel_token_here"
    echo ""
    echo "Setup Steps:"
    echo "  1. Copy the example environment file:"
    echo "     cp .env.example .env"
    echo "  2. Edit .env with your API credentials and tunnel token"
    echo "  3. Run the deployment script:"
    echo "     ./deploy.sh"
    echo ""
    echo "Note: This script automatically detects if sudo is needed for Docker commands."
}

# Handle command line arguments
case "${1:-}" in
    --help|-h)
        show_help
        exit 0
        ;;
    --logs)
        $DOCKER_CMD compose logs
        exit 0
        ;;
    --follow-logs)
        print_status "Following logs in real-time (press Ctrl+C to exit)..."
        $DOCKER_CMD compose logs -f
        exit 0
        ;;
    --stop)
        print_status "Stopping services..."
        $DOCKER_CMD compose stop
        print_success "Services stopped"
        exit 0
        ;;
    --down)
        print_status "Stopping and removing containers..."
        $DOCKER_CMD compose down
        print_success "All containers removed"
        exit 0
        ;;
    --status)
        show_status
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
