#!/usr/bin/env python3
"""
Azure Spot VM Eviction Monitor

This script monitors an Azure VM for eviction notices and sends a webhook notification
before the VM is stopped. Works on Windows, Linux, and other server operating systems.
Now includes API key authentication for secure webhook communication.
"""

import os
import json
import time
import logging
import datetime
import requests
import socket
import argparse
from datetime import datetime, timezone
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.FileHandler("spot_monitor.log"), logging.StreamHandler()]
)
logger = logging.getLogger("AzureSpotMonitor")

# Constants
METADATA_URL = "http://169.254.169.254/metadata/instance"
SCHEDULED_EVENTS_URL = "http://169.254.169.254/metadata/scheduledevents?api-version=2019-08-01"
INSTANCE_INFO_URL = f"{METADATA_URL}?api-version=2021-02-01"
WEBHOOK_URL = "https://azure-vm-manager.mastercraftapps.workers.dev/webhook"
CHECK_INTERVAL = 5  # seconds
METADATA_TIMEOUT = 3  # shorter timeout (seconds)
HEARTBEAT_INTERVAL = 300  # log a heartbeat every 5 minutes
MAX_CONSECUTIVE_ERRORS = 10  # maximum number of errors before backing off

# Default resource group fallback (only used if metadata fails completely)
DEFAULT_RESOURCE_GROUP = "test"

# API Key for webhook authentication - should be set as environment variable
WEBHOOK_API_KEY = os.getenv('WEBHOOK_API_KEY')

def get_azure_metadata():
    """Retrieve Azure VM metadata including resourceGroup and vmName."""
    try:
        headers = {"Metadata": "true"}
        response = requests.get(INSTANCE_INFO_URL, headers=headers, timeout=METADATA_TIMEOUT)
        response.raise_for_status()
        metadata = response.json()
        
        vm_name = metadata.get("compute", {}).get("name")
        resource_group = metadata.get("compute", {}).get("resourceGroupName")
        
        if not vm_name or not resource_group:
            logger.warning("Could not retrieve VM name or resource group from metadata")
            return None, None
            
        # Log what we found in metadata
        logger.info(f"Metadata reports resource group as: {resource_group}")
        
        # Return exactly as received from metadata (preserving case)
        return resource_group, vm_name
    except requests.exceptions.RequestException as e:
        logger.error(f"Error retrieving Azure metadata: {e}")
        return None, None

def check_scheduled_events():
    """Check for scheduled maintenance events on the VM."""
    try:
        headers = {"Metadata": "true"}
        response = requests.get(SCHEDULED_EVENTS_URL, headers=headers, timeout=METADATA_TIMEOUT)
        response.raise_for_status()
        events_data = response.json()
        
        if not events_data or "Events" not in events_data:
            return None
            
        events = events_data.get("Events", [])
        
        # Filter for preempt events (spot VM eviction) or other termination events
        termination_events = [
            event for event in events
            if event.get("EventType") in ["Preempt", "Terminate", "Reboot", "Redeploy"]
        ]
        
        if termination_events:
            return termination_events[0]  # Return the first termination event
        return None
    except requests.exceptions.RequestException as e:
        logger.error(f"Error checking scheduled events: {e}")
        return None

def send_webhook(resource_group, vm_name, event_type=None, event_time=None):
    """Send webhook notification with VM information.
    Now includes API key authentication.
    """
    if not WEBHOOK_API_KEY:
        logger.error("WEBHOOK_API_KEY environment variable not set - cannot authenticate with webhook")
        return False
    
    # Simplified payload with just resource group and VM name
    # Using exact case as received from metadata
    payload = {
        "resourceGroup": resource_group,
        "vmName": vm_name
    }
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {WEBHOOK_API_KEY}"
    }
    
    try:
        logger.info(f"Sending webhook notification: {payload}")
        response = requests.post(WEBHOOK_URL, headers=headers, json=payload, timeout=5)
        
        if response.status_code == 401:
            logger.error("Webhook authentication failed - check WEBHOOK_API_KEY")
            return False
        elif response.status_code == 400:
            logger.error(f"Bad request to webhook: {response.text}")
            return False
        
        response.raise_for_status()
        logger.info(f"Webhook sent successfully: {response.status_code}")
        
        # Log the response for debugging
        try:
            response_data = response.json()
            logger.info(f"Webhook response: {response_data}")
        except:
            logger.info(f"Webhook response (non-JSON): {response.text}")
        
        return True
        
    except requests.exceptions.RequestException as e:
        logger.error(f"Error sending webhook: {e}")
        return False

def main():
    """Main function to periodically check for VM termination events."""
    parser = argparse.ArgumentParser(description='Monitor Azure Spot VM for eviction notices.')
    parser.add_argument('--webhook', type=str, help='Custom webhook URL (optional)')
    parser.add_argument('--interval', type=int, default=CHECK_INTERVAL, 
                        help=f'Check interval in seconds (default: {CHECK_INTERVAL})')
    parser.add_argument('--heartbeat', type=int, default=HEARTBEAT_INTERVAL,
                        help=f'Heartbeat interval in seconds (default: {HEARTBEAT_INTERVAL})')
    parser.add_argument('--api-key', type=str, help='Webhook API key (can also use WEBHOOK_API_KEY env var)')
    args = parser.parse_args()
    
    # Update constants if provided via arguments
    global WEBHOOK_URL, WEBHOOK_API_KEY
    if args.webhook:
        WEBHOOK_URL = args.webhook
    if args.api_key:
        WEBHOOK_API_KEY = args.api_key
    
    # Validate API key is available
    if not WEBHOOK_API_KEY:
        logger.error("No API key provided. Set WEBHOOK_API_KEY environment variable or use --api-key argument")
        sys.exit(1)
    
    check_interval = args.interval or CHECK_INTERVAL
    heartbeat_interval = args.heartbeat or HEARTBEAT_INTERVAL
    
    # Get VM information - more resilient with retries
    resource_group, vm_name = None, None
    retry_count = 0
    max_retries = 5
    
    while (not resource_group or not vm_name) and retry_count < max_retries:
        resource_group, vm_name = get_azure_metadata()
        if not resource_group or not vm_name:
            retry_count += 1
            logger.warning(f"Failed to get metadata, retry {retry_count}/{max_retries}")
            time.sleep(2)  # Short pause between retries
    
    # Fallback if metadata service is not available
    if not vm_name:
        hostname = socket.gethostname()
        logger.warning(f"Could not get VM name, using hostname: {hostname}")
        vm_name = hostname
    
    if not resource_group:
        logger.warning(f"Could not get resource group, using default: {DEFAULT_RESOURCE_GROUP}")
        resource_group = DEFAULT_RESOURCE_GROUP
    
    logger.info(f"Monitoring VM: {vm_name} in resource group: {resource_group}")
    logger.info(f"Webhook URL: {WEBHOOK_URL}")
    logger.info(f"Check interval: {check_interval} seconds")
    logger.info(f"Heartbeat interval: {heartbeat_interval} seconds")
    logger.info(f"API key configured: {'Yes' if WEBHOOK_API_KEY else 'No'}")
    
    # Test webhook connectivity on startup
    logger.info("Testing webhook connectivity...")
    if send_webhook(resource_group, vm_name):
        logger.info("Webhook connectivity test successful")
    else:
        logger.warning("Webhook connectivity test failed - continuing anyway")
    
    # Keep track of events we've already processed
    processed_events = set()
    
    # Track errors and last heartbeat
    consecutive_errors = 0
    last_heartbeat_time = time.time()
    
    # Main monitoring loop
    while True:
        current_time = time.time()
        
        try:
            # Check for scheduled events
            event = check_scheduled_events()
            
            # Reset error counter on success
            consecutive_errors = 0
            
            if event and event.get("EventId") not in processed_events:
                event_id = event.get("EventId")
                event_type = event.get("EventType")
                event_time = event.get("NotBefore", datetime.now(timezone.utc).isoformat())
                
                logger.warning(f"VM termination event detected: {event_type}, scheduled for: {event_time}")
                
                # Send webhook notification
                success = send_webhook(resource_group, vm_name, event_type, event_time)
                
                if success:
                    # Add to processed events to avoid duplicate notifications
                    processed_events.add(event_id)
                    logger.info(f"Processed event {event_id}")
                else:
                    # If webhook fails, we'll try again on the next iteration
                    logger.warning("Webhook failed, will retry on next check")
            
            # Send heartbeat notification periodically
            if current_time - last_heartbeat_time >= heartbeat_interval:
                logger.info("Sending heartbeat notification")
                send_webhook(resource_group, vm_name)
                last_heartbeat_time = current_time
                
        except Exception as e:
            consecutive_errors += 1
            logger.error(f"Error in main loop (attempt {consecutive_errors}): {e}")
            
            # If too many consecutive errors, back off check interval
            if consecutive_errors > MAX_CONSECUTIVE_ERRORS:
                backoff_interval = min(300, check_interval * 2)  # Max 5 minute backoff
                logger.warning(f"Too many consecutive errors, backing off to {backoff_interval}s")
                time.sleep(backoff_interval)
                # Reset error counter after backoff
                consecutive_errors = MAX_CONSECUTIVE_ERRORS // 2
            
        # Sleep before next check
        time.sleep(check_interval)

if __name__ == "__main__":
    try:
        logger.info("Starting Azure Spot VM Monitor")
        main()
    except KeyboardInterrupt:
        logger.info("Monitor stopped by user")
    except Exception as e:
        logger.critical(f"Fatal error: {e}")
        sys.exit(1)