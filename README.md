# Azure Spot VM Eviction Monitor

A high-performance TypeScript-based monitoring solution that detects and responds to Azure Spot VM evictions in **under 30 seconds**, ensuring minimal service disruption and automated recovery with enterprise-grade security.

## Why This Matters

**Spot VMs save 60-90% on cloud costs** but can be evicted with only 30 seconds notice. This tool ensures your applications stay online by automatically restarting evicted VMs faster than manual intervention, turning unreliable spot instances into a robust, cost-effective infrastructure solution.

The **cloud-agnostic architecture** makes it easily adaptable for AWS Spot Instances, Google Cloud Preemptible VMs, and other cloud providers, positioning this as a universal spot instance management platform.

## Public vs Enterprise Versions

This is the **public demonstration version** showcasing core functionality. The **private enterprise version** includes advanced features:

- 🏥 **Health Check Endpoints** - Application-level monitoring and restart decisions
- 🏗️ **Infrastructure as Code** - Terraform and Pulumi integration for complete VM lifecycle management  
- ☁️ **Multi-Cloud Support** - AWS Spot Instances, Google Cloud Preemptible VMs, Oracle Cloud
- 📊 **Advanced Analytics** - Cost optimization insights and usage patterns
- 🎯 **PKI Management** - Automated lifecycle management support for SSL keys

**Interested in enterprise features for commercial projects?** [Contact me](mailto:your-email@example.com) to discuss licensing and implementation.

## Overview

This project provides a comprehensive solution for managing Azure Spot VM evictions through:

1. **Python Monitoring Agent**: Runs on the Spot VM and detects eviction events
2. **TypeScript Cloudflare Workers**: Queue-based architecture for processing eviction notifications and initiating VM restart
3. **Secure API Communication**: API key authentication between components

## Architecture

```
┌─────────────────┐    Webhook   ┌──────────────────┐    Queue    ┌─────────────────┐    Azure API   ┌─────────────────┐
│                 │  (Secured)   │                  │             │                 │                │                 │
│  Azure Spot VM  ├─────────────►│   Webhook        ├────────────►│  VM Processor   ├───────────────►│  Azure          │
│  with Python    │              │   Handler        │             │  Worker         │                │  Management     │
│  Monitor Agent  │              │   Worker         │             │                 │                │  API            │
│                 │              │                  │             │                 │                │                 │
└─────────────────┘              └──────────────────┘             └─────────────────┘                └─────────────────┘
```

## Features

- **🔒 Secure Communication**: API key authentication between Python agent and webhook handler
- **⚡ Queue-Based Processing**: Non-blocking webhook responses with reliable VM processing
- **🚀 TypeScript Architecture**: Two independent Cloudflare Workers for scalability
- **📊 Comprehensive Logging**: Detailed monitoring and error tracking
- **🔄 Automatic Recovery**: Intelligent retry logic and error handling
- **🌐 Multi-Platform Support**: Works on Linux and Windows VMs

## Technology Stack

- **Workers**: TypeScript, Cloudflare Workers (Serverless)
- **VM Agent**: Python 3.6+, Azure Instance Metadata Service
- **Queue**: Cloudflare Queues for reliable message processing
- **Authentication**: API Key-based authentication, Input validation
- **Deployment**: Wrangler CLI for ease of deployment on Cloudflare

## Quick Start

### 1. Clone Repository
```bash
git clone https://github.com/your-username/azure-spot-vm-manager.git
cd azure-spot-vm-manager
```

### 2. Install Dependencies
```bash
npm install
```

### 3. Configure Environment
```bash
# Copy environment template
cp .env.example .env

# Generate API key
openssl rand -hex 16

# Edit .env with your values
nano .env
```

### 4. Set Cloudflare Secrets
```bash
# Set webhook API key
wrangler secret put WEBHOOK_API_KEY --env queue
wrangler secret put WEBHOOK_API_KEY --env processor

# Set Azure credentials (for VM restart functionality)
wrangler secret put AZURE_CLIENT_ID --env processor
wrangler secret put AZURE_CLIENT_SECRET --env processor
wrangler secret put AZURE_TENANT_ID --env processor
wrangler secret put AZURE_SUBSCRIPTION_ID --env processor
```

### 5. Deploy Workers
```bash
# Build TypeScript
npm run build

# Deploy webhook handler
wrangler deploy --env queue

# Deploy VM processor
wrangler deploy --env processor
```

### 6. Install Python Agent on VM
```bash
# Download the Python agent
wget https://raw.githubusercontent.com/your-username/azure-spot-vm-manager/main/python-agent/vm-monitor.py

# Set API key
export WEBHOOK_API_KEY="your-api-key-here"

# Run the agent
python3 vm-monitor.py
```

## Project Structure

```
azure-spot-vm-manager/
├── webhook-handler/
│   └── webhook-handler.ts      # Receives webhooks, queues VMs
├── azure-vm-starter/
│   └── azure-vm-starter.ts     # Processes queue, restarts VMs
├── python-agent/
│   ├── vm-monitor.py           # VM monitoring agent
│   └── install-instructions.md # Installation guide
├── docs/
│   ├── api.md                  # API documentation
│   └── deployment.md           # Deployment guide
├── wrangler.toml               # Cloudflare Workers configuration
├── tsconfig.json               # TypeScript configuration
├── .env.example                # Environment variables template
└── README.md                   # This file
```

## API Documentation

### Webhook Endpoint
**POST** `/webhook`

**Headers:**
```
Authorization: Bearer {WEBHOOK_API_KEY}
Content-Type: application/json
```

**Body:**
```json
{
  "resourceGroup": "production-rg",
  "vmName": "spot-vm-01"
}
```

**Response:**
```json
{
  "success": true,
  "message": "VM queued: production-rg/spot-vm-01",
  "timestamp": "2024-10-15T10:30:00.000Z"
}
```

## Security Features

- **🔐 API Key Authentication**: Prevents unauthorized webhook access
- **✅ Input Validation**: Sanitizes resource group and VM names
- **🛡️ Request Validation**: Type checking and format validation
- **📝 Audit Logging**: Comprehensive request and error logging
- **🚫 Rate Limiting**: Built-in Cloudflare protection

## Requirements

- **Node.js**: 18+ (for development)
- **Python**: 3.6+ (for VM agent)
- **Azure**: Spot VM with Instance Metadata Service access
- **Cloudflare**: Account with Workers and Queues enabled
- **Azure Credentials**: Service Principal with VM start permissions

## Python Monitoring Agent

The monitoring agent (`vm-monitor.py`) runs on your Azure Spot VM and performs the following functions:

- Monitors the Azure Instance Metadata Service for eviction notices
- Sends secure webhook notifications when an eviction is detected
- Provides periodic heartbeats to verify the agent is running
- Handles service restarts and unexpected shutdowns gracefully
- Includes API key authentication for secure communication

### Installation

#### Ubuntu/Linux VM

1. Create the monitoring directory:
   ```bash
   sudo mkdir -p /vm-monitor
   cd /vm-monitor
   ```

2. Download the Python script:
   ```bash
   sudo wget https://raw.githubusercontent.com/your-username/azure-spot-vm-manager/main/python-agent/vm-monitor.py
   sudo chmod +x vm-monitor.py
   ```

3. Set environment variables:
   ```bash
   # Set API key
   export WEBHOOK_API_KEY="your-api-key-here"
   
   # Optional: Set custom webhook URL
   export WEBHOOK_URL="https://your-worker.workers.dev/webhook"
   ```

4. Create a systemd service file:
   ```bash
   sudo nano /etc/systemd/system/azure-spot-monitor.service
   ```

5. Add the following content to the service file:
   ```ini
   [Unit]
   Description=Azure Spot VM Eviction Monitor
   After=network.target

   [Service]
   Type=simple
   User=root
   WorkingDirectory=/vm-monitor
   Environment=WEBHOOK_API_KEY=your-api-key-here
   ExecStart=/usr/bin/python3 /vm-monitor/vm-monitor.py
   Restart=always
   RestartSec=10

   [Install]
   WantedBy=multi-user.target
   ```

6. Enable and start the service:
   ```bash
   sudo systemctl daemon-reload
   sudo systemctl enable azure-spot-monitor
   sudo systemctl start azure-spot-monitor
   ```

7. Verify the service is running:
   ```bash
   sudo systemctl status azure-spot-monitor
   ```

#### Windows Server

1. Create the monitoring directory:
   ```powershell
   New-Item -Path "C:\vm-monitor" -ItemType Directory -Force
   cd C:\vm-monitor
   ```

2. Download the Python script:
   ```powershell
   Invoke-WebRequest -Uri "https://raw.githubusercontent.com/your-username/azure-spot-vm-manager/main/python-agent/vm-monitor.py" -OutFile "vm-monitor.py"
   ```

3. Set environment variable:
   ```powershell
   [Environment]::SetEnvironmentVariable("WEBHOOK_API_KEY", "your-api-key-here", "Machine")
   ```

4. Create a scheduled task to run the script at startup:
   ```powershell
   $action = New-ScheduledTaskAction -Execute "python" -Argument "C:\vm-monitor\vm-monitor.py"
   $trigger = New-ScheduledTaskTrigger -AtStartup
   $settings = New-ScheduledTaskSettingsSet -ExecutionTimeLimit 0 -RestartCount 3 -RestartInterval (New-TimeSpan -Minutes 1)
   Register-ScheduledTask -TaskName "AzureSpotMonitor" -Action $action -Trigger $trigger -Settings $settings -RunLevel Highest -Force
   ```

5. Start the scheduled task:
   ```powershell
   Start-ScheduledTask -TaskName "AzureSpotMonitor"
   ```

## Development

### Local Development
```bash
# Install dependencies
npm install

# Type check
npm run type-check

# Run tests
npm test

# Build project
npm run build

# Run locally
wrangler dev --env dev-webhook
wrangler dev --env dev-processor
```

### Deployment Environments

- **Development**: `--env dev-webhook` / `--env dev-processor`
- **Staging**: `--env staging-webhook` / `--env staging-processor`
- **Production**: `--env webhook` / `--env processor`

## Monitoring and Maintenance

### Check if the agent is running

On Linux:
```bash
ps aux | grep vm-monitor.py
sudo systemctl status azure-spot-monitor
```

On Windows:
```powershell
Get-Process -Name python | Where-Object {$_.CommandLine -like "*vm-monitor.py*"}
```

### View logs

On Linux:
```bash
tail -f /vm-monitor/spot_monitor.log
```

On Windows:
```powershell
Get-Content -Path "C:\vm-monitor\spot_monitor.log" -Tail 20 -Wait
```

### Restart the service

On Linux:
```bash
sudo systemctl restart azure-spot-monitor
```

On Windows:
```powershell
Restart-ScheduledTask -TaskName "AzureSpotMonitor"
```

## Troubleshooting

### Common Issues

1. **Authentication Errors**
   - Verify `WEBHOOK_API_KEY` is set correctly in both Python agent and Cloudflare secrets
   - Check API key format (should be 32+ character hex string)
   - Ensure no extra spaces or characters in API key

2. **Agent Not Detecting Evictions**
   - Verify the VM is a Spot VM
   - Ensure the metadata service is accessible
   - Check logs for timeout or connection errors

3. **Webhook Connection Issues**
   - Verify the Cloudflare Worker URL is correct
   - Check network connectivity from the VM
   - Test webhook connectivity:
     ```bash
     curl -H "Authorization: Bearer your-api-key" \
          -H "Content-Type: application/json" \
          -d '{"resourceGroup":"test","vmName":"test"}' \
          https://your-worker.workers.dev/webhook
     ```

4. **VM Restart Failures**
   - Verify Azure credentials are set correctly in Cloudflare secrets
   - Check Azure service principal permissions
   - Review Cloudflare Worker logs for Azure API errors

### Testing Connectivity

```bash
# Test metadata service connectivity
curl -H Metadata:true "http://169.254.169.254/metadata/instance?api-version=2021-02-01"

# Test webhook connectivity (with authentication)
curl -v -H "Authorization: Bearer your-api-key" \
     -H "Content-Type: application/json" \
     -d '{"resourceGroup":"test-rg","vmName":"test-vm"}' \
     https://your-worker.workers.dev/webhook
```

## Security Considerations

- The Python agent runs with elevated privileges to ensure it can access the metadata service
- Use strong, randomly generated API keys (minimum 32 characters)
- Rotate API keys regularly
- Monitor webhook logs for unauthorized access attempts
- Only minimal permissions should be granted to the Azure service principal
- Keep dependencies updated to address security vulnerabilities