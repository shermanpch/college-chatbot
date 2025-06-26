# College Chatbot - Docker Deployment Script for Windows
# This script automates the Docker build and deployment process on Windows

param(
    [switch]$Help,
    [switch]$Logs,
    [switch]$Stop,
    [switch]$Status,
    [switch]$DeployWithProxy
)

# Configuration
$IMAGE_NAME = "college-chatbot"
$CONTAINER_NAME = "college-chatbot-container"
$PORT = "8000"

# Colors for output (Windows PowerShell colors)
$RED = "Red"
$GREEN = "Green"
$YELLOW = "Yellow"
$BLUE = "Cyan"

# Function to print colored output
function Write-Status {
    param([string]$Message)
    Write-Host "[INFO] $Message" -ForegroundColor $BLUE
}

function Write-Success {
    param([string]$Message)
    Write-Host "[SUCCESS] $Message" -ForegroundColor $GREEN
}

function Write-Warning {
    param([string]$Message)
    Write-Host "[WARNING] $Message" -ForegroundColor $YELLOW
}

function Write-Error {
    param([string]$Message)
    Write-Host "[ERROR] $Message" -ForegroundColor $RED
}

# Function to check if Docker is installed and running
function Test-Docker {
    try {
        $null = docker --version
        Write-Success "Docker is installed"
    }
    catch {
        Write-Error "Docker is not installed or not in PATH."
        Write-Host "Please install Docker Desktop for Windows from: https://docs.docker.com/desktop/install/windows-install/"
        exit 1
    }

    try {
        $null = docker ps 2>$null
        Write-Success "Docker is running and accessible"
    }
    catch {
        Write-Error "Docker daemon is not running or not accessible."
        Write-Host "Please make sure Docker Desktop is running."
        exit 1
    }
}

# Function to load and validate .env file
function Import-AndValidateEnvFile {
    # Check if .env file exists
    if (-not (Test-Path ".env")) {
        Write-Error ".env file not found!"
        Write-Host ""
        Write-Host "To set up your environment:"
        Write-Host "  1. Copy the example file: Copy-Item example.env .env"
        Write-Host "  2. Edit .env with your API credentials"
        Write-Host "  3. Run this script again"
        Write-Host ""
        Write-Host "Required variables in .env:"
        Write-Host "  OPENROUTER_API_KEY=your_api_key_here"
        Write-Host "  OPENROUTER_SELF_RETRIEVAL_MODEL=openai/gpt-4o-mini"
        exit 1
    }

    Write-Status "Loading environment variables from .env file..."
    
    try {
        Get-Content ".env" | ForEach-Object {
            if ($_ -match "^\s*([^#=]+)=(.*)$") {
                $name = $matches[1].Trim()
                $value = $matches[2].Trim()
                # Remove quotes if present
                if ($value -match '^".*"$' -or $value -match "^'.*'$") {
                    $value = $value.Substring(1, $value.Length - 2)
                }
                [Environment]::SetEnvironmentVariable($name, $value, "Process")
            }
        }
        Write-Success "Environment variables loaded from .env file"
    }
    catch {
        Write-Error "Failed to load .env file: $_"
        exit 1
    }

    # Validate required variables
    $missingVars = @()

    if (-not $env:OPENROUTER_API_KEY) {
        $missingVars += "OPENROUTER_API_KEY"
    }

    if (-not $env:OPENROUTER_SELF_RETRIEVAL_MODEL) {
        $missingVars += "OPENROUTER_SELF_RETRIEVAL_MODEL"
    }

    if ($missingVars.Count -gt 0) {
        Write-Error "Required environment variables are missing from .env file: $($missingVars -join ', ')"
        Write-Host ""
        Write-Host "Please add the missing variables to your .env file:"
        foreach ($var in $missingVars) {
            Write-Host "  $var=your_value_here"
        }
        Write-Host ""
        Write-Host "You can use example.env as a reference."
        exit 1
    }
    
    Write-Success "All required environment variables are set"
}

# Function to stop and remove existing container
function Remove-ExistingContainer {
    try {
        $containerExists = docker ps -a --format "{{.Names}}" | Where-Object { $_ -eq $CONTAINER_NAME }
        if ($containerExists) {
            Write-Status "Stopping and removing existing container..."
            docker stop $CONTAINER_NAME 2>$null | Out-Null
            docker rm $CONTAINER_NAME 2>$null | Out-Null
            Write-Success "Cleaned up existing container"
        }
    }
    catch {
        # Container might not exist, which is fine
    }
}

# Function to build Docker image
function Build-Image {
    Write-Status "Building Docker image..."

    try {
        docker build -t $IMAGE_NAME .
        if ($LASTEXITCODE -eq 0) {
            Write-Success "Docker image built successfully"
        }
        else {
            Write-Error "Failed to build Docker image"
            exit 1
        }
    }
    catch {
        Write-Error "Failed to build Docker image: $_"
        exit 1
    }
}

# Function to run container
function Start-Container {
    Write-Status "Starting container..."

    try {
        docker run -d `
            -p "${PORT}:${PORT}" `
            -e "OPENROUTER_API_KEY=$env:OPENROUTER_API_KEY" `
            -e "OPENROUTER_SELF_RETRIEVAL_MODEL=$env:OPENROUTER_SELF_RETRIEVAL_MODEL" `
            --name $CONTAINER_NAME `
            $IMAGE_NAME

        if ($LASTEXITCODE -eq 0) {
            Write-Success "Container started successfully"
            Write-Success "Application is accessible at: http://localhost:$PORT"
        }
        else {
            Write-Error "Failed to start container"
            exit 1
        }
    }
    catch {
        Write-Error "Failed to start container: $_"
        exit 1
    }
}

# Function to show container status
function Show-Status {
    Write-Host ""
    Write-Status "Container status:"
    docker ps --filter "name=$CONTAINER_NAME" --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}"

    Write-Host ""
    Write-Status "To view logs, run:"
    Write-Host ".\deploy.ps1 -Logs"
    Write-Host "Or: docker logs $CONTAINER_NAME"

    Write-Host ""
    Write-Status "To follow logs in real-time, run:"
    Write-Host "docker logs -f $CONTAINER_NAME"

    Write-Host ""
    Write-Status "To stop the container, run:"
    Write-Host ".\deploy.ps1 -Stop"
    Write-Host "Or: docker stop $CONTAINER_NAME"
}

# Main deployment function
function Start-Deployment {
    Write-Host "============================================"
    Write-Host "  College Chatbot Deployment"
    Write-Host "============================================"

    # Check prerequisites
    Test-Docker
    
    # Load and validate environment variables from .env file
    Import-AndValidateEnvFile

    # Clean up any existing deployment
    Remove-ExistingContainer

    # Build and run
    Build-Image
    Start-Container

    # Show status
    Show-Status

    Write-Success "Deployment completed successfully!"
}

# Function to show reverse proxy information (Windows note)
function Show-ReverseProxyInfo {
    Write-Warning "Reverse proxy setup is designed for Linux servers."
    Write-Host ""
    Write-Host "For Windows development:"
    Write-Host "  - Use the application directly at http://localhost:8000"
    Write-Host "  - For production deployment, use a Linux server with ./deploy.sh --deploy-with-proxy"
    Write-Host ""
    Write-Host "For production deployment on Linux:"
    Write-Host "  1. Deploy your application to a Linux server (Ubuntu/Debian recommended)"
    Write-Host "  2. Upload all project files to your server"
    Write-Host "  3. Configure your .env file with domain and email:"
    Write-Host "     DOMAIN=your-domain.com"
    Write-Host "     SSL_EMAIL=your-email@example.com"
    Write-Host "  4. Run: ./deploy.sh --deploy-with-proxy"
    Write-Host ""
    Write-Host "This will deploy your app and automatically setup:"
    Write-Host "  - Nginx reverse proxy"
    Write-Host "  - SSL certificates from Let's Encrypt"
    Write-Host "  - Automatic certificate renewal"
    Write-Host "  - Security headers and firewall configuration"
    Write-Host ""
    Write-Warning "Windows reverse proxy setup is not supported by this script."
}

# Show help
function Show-Help {
    Write-Host "College Chatbot - Docker Deployment Script"
    Write-Host ""
    Write-Host "Usage:"
    Write-Host "  .\deploy.ps1                     - Deploy the application"
    Write-Host "  .\deploy.ps1 -Help               - Show this help message"
    Write-Host "  .\deploy.ps1 -Logs               - Show container logs"
    Write-Host "  .\deploy.ps1 -Stop               - Stop the container"
    Write-Host "  .\deploy.ps1 -Status             - Show container status"
    Write-Host "  .\deploy.ps1 -DeployWithProxy    - Deploy app and show proxy info"
    Write-Host ""
    Write-Host "Environment Setup:"
    Write-Host "  This script requires a .env file with your API credentials."
    Write-Host ""
    Write-Host "  Required variables in .env:"
    Write-Host "    OPENROUTER_API_KEY=your_api_key_here"
    Write-Host "    OPENROUTER_SELF_RETRIEVAL_MODEL=openai/gpt-4o-mini"
    Write-Host ""
    Write-Host "Setup Steps:"
    Write-Host "  1. Copy the example environment file:"
    Write-Host "     Copy-Item example.env .env"
    Write-Host "  2. Edit .env with your API credentials"
    Write-Host "  3. Run the deployment script:"
    Write-Host "     .\deploy.ps1"
    Write-Host ""
    Write-Host "Production Deployment:"
    Write-Host "  For production with custom domain and SSL:"
    Write-Host "  - Use a Linux server (Ubuntu/Debian recommended)"
    Write-Host "  - Use the setup-reverse-proxy.sh script on your server"
    Write-Host "  - See REVERSE_PROXY_SETUP.md for detailed instructions"
    Write-Host ""
    Write-Host "Note: Make sure Docker Desktop is running before executing this script."
}

# Handle command line arguments
if ($Help) {
    Show-Help
    exit 0
}
elseif ($Logs) {
    try {
        docker logs $CONTAINER_NAME
    }
    catch {
        Write-Error "Failed to get container logs. Make sure the container is running."
        exit 1
    }
    exit 0
}
elseif ($Stop) {
    Write-Status "Stopping container..."
    try {
        docker stop $CONTAINER_NAME
        Write-Success "Container stopped"
    }
    catch {
        Write-Error "Failed to stop container. It may not be running."
        exit 1
    }
    exit 0
}
elseif ($Status) {
    Show-Status
    exit 0
}
elseif ($DeployWithProxy) {
    Start-Deployment
    Write-Host ""
    Show-ReverseProxyInfo
    exit 0
}
else {
    # Default action: deploy
    Start-Deployment
}
