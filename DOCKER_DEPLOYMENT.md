# Docker Deployment Guide for College Chatbot

This guide provides step-by-step instructions to deploy the Chainlit College Chatbot application using Docker on Windows, macOS, and Linux.

## Overview

The application has been containerized with Docker and includes:
- Chainlit web application (`chatbot/app.py`)
- Vector database with college data (ChromaDB)
- Student dataset and RAG documents
- Custom CSS styling
- All necessary Python dependencies

## Prerequisites

### 1. Install Docker

**Windows:**
- Download and install [Docker Desktop for Windows](https://docs.docker.com/desktop/install/windows-install/)
- Ensure Docker Desktop is running before proceeding

**macOS:**
- Download and install [Docker Desktop for Mac](https://docs.docker.com/desktop/install/mac-install/)
- Ensure Docker Desktop is running before proceeding

**Linux (Ubuntu/Debian):**
```bash
sudo apt update
sudo apt install -y docker.io
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

**Linux (CentOS/RHEL):**
```bash
sudo yum install -y docker
sudo systemctl start docker
sudo systemctl enable docker
sudo usermod -aG docker $USER
```

After adding yourself to the docker group on Linux, log out and log back in for the changes to take effect.

### 2. Get the Project Code

Clone the repository or download the project files:

```bash
git clone <your-repository-url>
cd college-chatbot
```

### 3. Configure Your Environment

You'll need an OpenRouter API key to run the application. Sign up at [OpenRouter](https://openrouter.ai/) if you don't have one.

**Set up your environment file:**
1. Copy the example environment file:
   ```bash
   cp example.env .env
   ```
2. Edit the `.env` file with your API credentials:
   ```bash
   OPENROUTER_API_KEY=your_api_key_here
   OPENROUTER_SELF_RETRIEVAL_MODEL=openai/gpt-4o-mini
   ```

## Quick Start

### Windows (PowerShell)

1. **Open PowerShell and navigate to the project directory:**
   ```powershell
   cd path\to\college-chatbot
   ```

2. **Set up your environment file:**
   ```powershell
   Copy-Item example.env .env
   # Edit .env with your API keys using notepad or your preferred editor
   notepad .env
   ```

3. **Run the deployment script:**
   ```powershell
   .\deploy.ps1
   ```

4. **Access your application at:** `http://localhost:8000`

### macOS/Linux (Terminal)

1. **Open Terminal and navigate to the project directory:**
   ```bash
   cd /path/to/college-chatbot
   ```

2. **Set up your environment file:**
   ```bash
   cp example.env .env
   # Edit .env with your API keys using nano, vim, or your preferred editor
   nano .env
   ```

3. **Run the deployment script:**
   ```bash
   ./deploy.sh
   ```

4. **Access your application at:** `http://localhost:8000`

For detailed setup instructions, continue reading below.

## Environment Configuration

The deployment scripts **require** a `.env` file in the project root directory. This approach offers several advantages:

- **Security**: Your API keys are not exposed in command history or process lists
- **Convenience**: No need to export environment variables every time
- **Consistency**: Same configuration works across different terminals and sessions
- **Version Control**: The `.env` file is already excluded from git via `.gitignore`
- **Simplicity**: One clear way to configure the application

The project includes an `example.env` file with all the necessary variables and documentation. Simply copy it to `.env` and fill in your API keys.

**Important**: The scripts will fail immediately if no `.env` file is found, with clear instructions on how to create one.

## Docker Files

The following files have been created for containerization:

### `.dockerignore`
Excludes unnecessary files from the Docker build context including:
- Development files (notebooks, tests, evaluation)
- Cache directories and build artifacts
- OS-specific files
- Non-essential data directories

### `Dockerfile`
Sets up the containerized environment with:
- Python 3.11-slim base image
- Required environment variables
- All Python dependencies from `requirements.txt`
- Application code, data, and configuration files
- Exposes port 8000 for web access

## Detailed Deployment Steps

### Step 1: Set Environment Variables

**Required: Create a .env file**

1. Copy the example environment file:
   ```bash
   cp example.env .env
   ```

2. Edit the `.env` file with your credentials:
   ```bash
   OPENROUTER_API_KEY=your_api_key_here
   OPENROUTER_SELF_RETRIEVAL_MODEL=openai/gpt-4o-mini
   ```

The deployment scripts **require** a `.env` file and will not work without it.

### Step 2: Build the Docker Image

**Windows (PowerShell):**
```powershell
docker build -t college-chatbot .
```

**macOS/Linux (Terminal):**
```bash
docker build -t college-chatbot .
```

### Step 3: Run the Docker Container

**Windows (PowerShell):**
```powershell
docker run -d -p 8000:8000 --name college-chatbot-container -e OPENROUTER_API_KEY="$env:OPENROUTER_API_KEY" -e OPENROUTER_SELF_RETRIEVAL_MODEL="$env:OPENROUTER_SELF_RETRIEVAL_MODEL" college-chatbot
```

**macOS/Linux (Terminal):**
```bash
docker run -d -p 8000:8000 \
  -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  -e OPENROUTER_SELF_RETRIEVAL_MODEL="$OPENROUTER_SELF_RETRIEVAL_MODEL" \
  --name college-chatbot-container \
  college-chatbot
```

### Step 4: Verify Deployment

Check if the container is running:
```bash
docker ps
```

You should see `college-chatbot-container` in the list of running containers.

### Step 5: Access the Application

Your College Chatbot is now accessible at:
```
http://localhost:8000
```

## Container Management

### Using the Deployment Scripts

Both deployment scripts **require** a `.env` file and will automatically load environment variables from it.

**Windows (PowerShell):**
The `deploy.ps1` script provides convenient commands for container management:

```powershell
# Deploy (loads .env automatically)
.\deploy.ps1

# View container logs
.\deploy.ps1 -Logs

# Check container status
.\deploy.ps1 -Status

# Stop the container
.\deploy.ps1 -Stop

# Get help and see all options
.\deploy.ps1 -Help
```

**macOS/Linux (Terminal):**
The `deploy.sh` script provides convenient commands for container management:

```bash
# Deploy (loads .env automatically)
./deploy.sh

# View container logs
./deploy.sh --logs

# Check container status
./deploy.sh --status

# Stop the container
./deploy.sh --stop

# Get help and see all options
./deploy.sh --help
```

### Manual Container Management (All Platforms)

**View Logs:**
```bash
# View recent logs
docker logs college-chatbot-container

# Follow logs in real-time
docker logs -f college-chatbot-container
```

**Stop the Container:**
```bash
docker stop college-chatbot-container
```

**Start the Container Again:**
```bash
docker start college-chatbot-container
```

**Remove the Container:**
```bash
docker stop college-chatbot-container
docker rm college-chatbot-container
```

## Update and Redeploy

### Using the Deployment Scripts

**Both Windows and macOS/Linux:**
```bash
# Pull latest code changes (if using git)
git pull

# Ensure your .env file is properly configured, then redeploy
```

**Windows (PowerShell):**
```powershell
.\deploy.ps1
```

**macOS/Linux (Terminal):**
```bash
./deploy.sh
```

### Manual Update Process (All Platforms)

If you prefer to run Docker commands manually instead of using the deployment scripts:

**Prerequisites:**
You **must** have a `.env` file with your API keys.

**Windows (PowerShell):**
```powershell
# Pull updates (if using git)
git pull

# Load environment variables from .env file
Get-Content .env | ForEach-Object {
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

# Stop and remove old container
docker stop college-chatbot-container
docker rm college-chatbot-container

# Rebuild image
docker build -t college-chatbot .

# Run new container
docker run -d -p 8000:8000 --name college-chatbot-container -e OPENROUTER_API_KEY="$env:OPENROUTER_API_KEY" -e OPENROUTER_SELF_RETRIEVAL_MODEL="$env:OPENROUTER_SELF_RETRIEVAL_MODEL" college-chatbot
```

**macOS/Linux (Terminal):**
```bash
# Pull updates (if using git)
git pull

# Load environment variables from .env file
set -a
source .env
set +a

# Stop and remove old container
docker stop college-chatbot-container
docker rm college-chatbot-container

# Rebuild image
docker build -t college-chatbot .

# Run new container
docker run -d -p 8000:8000 \
  -e OPENROUTER_API_KEY="$OPENROUTER_API_KEY" \
  -e OPENROUTER_SELF_RETRIEVAL_MODEL="$OPENROUTER_SELF_RETRIEVAL_MODEL" \
  --name college-chatbot-container \
  college-chatbot
```

## Testing and Validation

### 1. Application Load Test
- Access `http://localhost:8000` in a web browser
- Verify the Chainlit interface loads correctly
- Check that the "College Chatbot" branding appears

### 2. Feature Testing
Test key application features:
- **SAT Score Input**: Test manual SAT score entry (400-1600 range)
- **State Selection**: Choose US states for college filtering
- **College Categorization**: Verify Safety/Target/Reach categorization
- **Hybrid Search**: Test search with specific criteria
- **Clarifying Questions**: Test preference-based re-ranking
- **PDF Report Generation**: Verify final college recommendations report

### 3. Error Monitoring
Monitor container logs for any issues:
```bash
docker logs college-chatbot-container
```

Common issues to check for:
- Vector store initialization errors
- Missing data files
- API key authentication problems
- Port binding conflicts

## Troubleshooting

### Container Won't Start
- Check logs: `docker logs college-chatbot-container`
- Verify your `.env` file exists and contains the required API keys
- Ensure both `OPENROUTER_API_KEY` and `OPENROUTER_SELF_RETRIEVAL_MODEL` are set correctly
- Ensure port 8000 is not already in use

**Check port usage:**
- **Windows:** `netstat -an | findstr :8000`
- **macOS/Linux:** `netstat -tulpn | grep :8000`

### Application Not Accessible
- Verify container is running: `docker ps`
- Check if Docker Desktop is running (Windows/macOS)
- Ensure no firewall is blocking port 8000
- Try accessing `http://127.0.0.1:8000` instead of `localhost`

### Vector Store Issues
- The application will attempt to build the vector store from source documents if missing
- Check logs for ChromaDB initialization messages
- Ensure `data/chatbot/peterson_rag_documents/` contains source documents

### Performance Issues
- Monitor resource usage: `docker stats college-chatbot-container`
- Increase Docker Desktop memory allocation if needed (Windows/macOS)
- Check for memory or CPU constraints

### Docker Permission Issues (Linux)
If you get permission errors:
```bash
sudo usermod -aG docker $USER
```
Then log out and log back in.

## Platform-Specific Notes

### Windows
- Use PowerShell (recommended) or Command Prompt
- Docker Desktop must be running
- Windows paths use backslashes (`\`)
- Environment variables use `$env:VARIABLE_NAME`

### macOS
- Docker Desktop must be running
- Use Terminal or iTerm2
- Environment variables use `$VARIABLE_NAME`
- The deployment script (`deploy.sh`) works natively

### Linux
- Docker can run natively without Docker Desktop
- Use Terminal/Bash
- May need `sudo` for Docker commands if not in docker group
- The deployment script (`deploy.sh`) works natively

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **Local Access**: By default, the application is only accessible locally
3. **Firewall**: Consider firewall settings if accessing from other machines
4. **Updates**: Regularly update the base image and dependencies

## Advanced Configuration

### Custom Port
To run on a different port (e.g., 3000):

**Windows:**
```powershell
docker run -d -p 3000:8000 --name college-chatbot-container -e OPENROUTER_API_KEY="your_key" -e OPENROUTER_SELF_RETRIEVAL_MODEL="openai/gpt-4o-mini" college-chatbot
```

**macOS/Linux:**
```bash
docker run -d -p 3000:8000 \
  -e OPENROUTER_API_KEY="your_key" \
  -e OPENROUTER_SELF_RETRIEVAL_MODEL="your_model" \
  --name college-chatbot-container \
  college-chatbot
```

Then access at `http://localhost:3000`

### Additional Environment Variables
You can pass additional environment variables:

**Windows:**
```powershell
docker run -d -p 8000:8000 --name college-chatbot-container -e OPENROUTER_API_KEY="your_key" -e OPENROUTER_SELF_RETRIEVAL_MODEL="your_model" -e CUSTOM_VAR="value" college-chatbot
```

**macOS/Linux:**
```bash
docker run -d -p 8000:8000 \
  -e OPENROUTER_API_KEY="your_key" \
  -e OPENROUTER_SELF_RETRIEVAL_MODEL="your_model" \
  -e CUSTOM_VAR="value" \
  --name college-chatbot-container \
  college-chatbot
```

## Support

If you encounter issues:
1. Check the container logs first: `docker logs college-chatbot-container`
2. Verify all prerequisites are met (Docker installed, API key set)
3. Ensure data files are present and accessible
4. Check platform-specific troubleshooting section above

The Docker setup is designed to be self-contained and should work out of the box once the API key and model are provided.
