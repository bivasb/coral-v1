# Coral Server Deployment Plan

## Overview
This plan outlines the steps to deploy the Coral server with the migrated unified-debug-agent, including Docker socket exposure and agent registration.

## Prerequisites
- Docker installed and running
- Docker socket accessible at `/var/run/docker.sock`
- Environment variables configured (see below)

## Required Environment Variables

Create a `.env` file in this directory with:

```bash
# API Keys
DEEPSEEK_API_KEY=your_deepseek_api_key_here

# Coral Server Configuration  
CORAL_SSE_URL=http://localhost:5555/sse
CORAL_AGENT_ID=unified-debug-agent

# Model Configuration
MODEL_NAME=deepseek-chat
MODEL_PROVIDER=openai
MODEL_TEMPERATURE=0.1
MODEL_MAX_TOKENS=8000
MODEL_BASE_URL=https://api.deepseek.com/v1
TIMEOUT_MS=300
```

## Docker Socket Exposure Strategy

### Option 1: Direct Socket Mount (Recommended for Development)
```bash
docker run \
  -p 5555:5555 \
  -v /var/run/docker.sock:/var/run/docker.sock \
  -v $(pwd)/registry.toml:/config/registry.toml \
  --env-file .env \
  ghcr.io/coral-protocol/coral-server
```

### Option 2: Docker-in-Docker (For Production/Security)
```bash
# Create a Docker network
docker network create coral-network

# Run Docker-in-Docker
docker run -d \
  --name coral-docker \
  --privileged \
  --network coral-network \
  docker:dind

# Run Coral server connected to DinD
docker run \
  -p 5555:5555 \
  --network coral-network \
  -e DOCKER_HOST=tcp://coral-docker:2376 \
  -v $(pwd)/registry.toml:/config/registry.toml \
  --env-file .env \
  ghcr.io/coral-protocol/coral-server
```

## Agent Registration Process

1. **Registry Configuration**: The `registry.toml` file defines available agents
2. **Agent Discovery**: Coral server automatically discovers agents from registry paths
3. **Docker Image Building**: Agents are built as Docker containers using the dockerfile in coral-agent.toml
4. **Runtime Management**: Coral server manages agent lifecycle and communication

## Security Considerations

### Docker Socket Risks
- Direct socket access gives containers full Docker daemon control
- Consider using Docker-in-Docker for production environments
- Implement proper network isolation
- Use read-only mounts where possible

### Agent Security
- Agents run in isolated containers
- Environment variable injection for configuration
- No direct file system access outside containers
- Network communication through Coral server only

## Directory Structure
```
coral-v1/
├── registry.toml                 # Agent registry configuration
├── .env                         # Environment variables (create this)
├── DEPLOYMENT_PLAN.md            # This file
└── unified-debug-agent/          # Migrated agent
    ├── coral-agent.toml          # Agent configuration
    ├── main.py                   # Agent entry point
    ├── requirements.txt          # Python dependencies
    ├── unified_debug_solver.py   # Core debugging logic
    ├── tools/                    # Agent tools
    └── patches/                  # Generated patches
```

## Deployment Steps

1. **Environment Setup**:
   ```bash
   cd /Users/bivasb/Documents/IOA/coral-v1
   cp .env.example .env  # Create and edit .env file
   ```

2. **Start Coral Server**:
   ```bash
   docker run \
     -p 5555:5555 \
     -v /var/run/docker.sock:/var/run/docker.sock \
     -v $(pwd)/registry.toml:/config/registry.toml \
     --env-file .env \
     ghcr.io/coral-protocol/coral-server
   ```

3. **Verify Agent Registration**:
   - Check server logs for agent discovery
   - Verify agent container builds successfully
   - Test agent communication through Coral server API

4. **Testing**:
   - Send test messages to the unified-debug-agent
   - Verify debugging workflow functionality
   - Check Docker socket access for agent operations

## Troubleshooting

### Common Issues
1. **Docker Socket Permission Denied**: Ensure user is in docker group
2. **Agent Build Failures**: Check dockerfile syntax in coral-agent.toml  
3. **Environment Variable Missing**: Verify .env file is properly loaded
4. **Network Connectivity**: Ensure ports 5555 is available and accessible

### Debug Commands
```bash
# Check Docker socket accessibility
docker ps

# View Coral server logs
docker logs <coral-server-container-id>

# Test agent container manually
docker build -t test-agent ./unified-debug-agent
docker run --env-file .env test-agent
```

## Next Steps
1. Create the .env file with actual API keys
2. Test the deployment with the provided Docker commands
3. Verify agent functionality through the Coral server interface
4. Set up monitoring and logging for production use