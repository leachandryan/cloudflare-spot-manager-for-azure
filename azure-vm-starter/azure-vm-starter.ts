// This worker handles both webhook requests and VM processing with Cloudflare Queue

// Types
interface VMRecord {
  resourceGroup: string;
  vmName: string;
  queuedAt: number;
  status: 'pending' | 'processing' | 'completed' | 'failed';
}

interface ProcessingResult {
  id: string;
  resourceGroup: string;
  vmName: string;
  queuedAt: number;
  queuedAtFormatted: string;
  status: string;
}

interface CloudflareEnvironment {
  QUEUE_NAME?: Queue<VMRecord>;
  ENVIRONMENT?: string;
  LOG_LEVEL?: string;
  // Azure credentials would be added here as secrets
  AZURE_CLIENT_ID?: string;
  AZURE_CLIENT_SECRET?: string;
  AZURE_TENANT_ID?: string;
  AZURE_SUBSCRIPTION_ID?: string;
}

interface QueueMessage<T = any> {
  id: string;
  body: T;
  ack(): void;
  retry(): void;
}

export default {
  // Handle HTTP requests
  async fetch(request: Request, env: CloudflareEnvironment, ctx: ExecutionContext): Promise<Response> {
    // Handle webhook POST requests to add VMs to queue
    if (request.method === "POST") {
      try {
        // Parse the webhook payload
        const payload = await request.json() as VMRecord;
        
        // Extract VM details
        const { resourceGroup, vmName } = payload;
        
        if (!resourceGroup || !vmName) {
          return new Response('Missing required fields: resourceGroup and vmName', { status: 400 });
        }

        // Create a VM record
        const now = Date.now();
        const vmRecord: VMRecord = {
          resourceGroup,
          vmName,
          queuedAt: now,
          status: 'pending'
        };

        // Get queue name from environment variable
        const queueName = env.QUEUE_NAME;
        
        if (!queueName) {
          return new Response('Queue not configured', { status: 500 });
        }
        
        // Send to queue using the specified queue name
        await queueName.send(vmRecord);
        
        console.log(`VM queued: ${resourceGroup}/${vmName}, at: ${new Date(now).toISOString()}`);

        // Return success
        return new Response(JSON.stringify({
          success: true,
          message: `VM queued: ${resourceGroup}/${vmName}`,
          timestamp: new Date(now).toISOString()
        }), { 
          status: 200,
          headers: { 'Content-Type': 'application/json' }
        });
      } catch (error) {
        console.error('Error in webhook handler:', error);
        const errorMessage = error instanceof Error ? error.message : 'Unknown error';
        return new Response(`Error: ${errorMessage}`, { status: 500 });
      }
    }
    
    // If not a POST request, return info message
    return new Response(JSON.stringify({
      status: "info",
      message: "Queue-based system does not support listing pending VMs via HTTP endpoint"
    }), { 
      status: 200,
      headers: { 'Content-Type': 'application/json' }
    });
  },
  
  // Handle scheduled events
  async scheduled(event: ScheduledEvent, env: CloudflareEnvironment, ctx: ExecutionContext): Promise<void> {
    console.log('Scheduled event triggered:', new Date().toISOString());
    
    // This could be used for cleanup, health checks, or other maintenance tasks
    // For now, just log that the scheduled event ran
    console.log('Scheduled VM restart check completed');
  },
  
  // Queue consumer to process VM restart requests
  async queue(batch: MessageBatch<VMRecord>, env: CloudflareEnvironment, ctx: ExecutionContext): Promise<void> {
    console.log(`Processing ${batch.messages.length} VM restart requests from queue`);
    
    const results: ProcessingResult[] = [];
    
    for (const message of batch.messages) {
      try {
        // The message body contains our VM record
        const vmRecord: VMRecord = message.body;
        
        console.log(`Processing VM: ${vmRecord.resourceGroup}/${vmRecord.vmName}`, vmRecord);
        
        // TODO: Implement Azure API call to restart the VM
        // For now, just log what would happen
        console.log(`Would restart VM: ${vmRecord.resourceGroup}/${vmRecord.vmName}`);
        
        // In a real implementation, you would:
        // 1. Get Azure access token
        // 2. Call Azure REST API to start the VM
        // 3. Handle success/failure appropriately
        
        results.push({
          id: message.id,
          resourceGroup: vmRecord.resourceGroup,
          vmName: vmRecord.vmName,
          queuedAt: vmRecord.queuedAt,
          queuedAtFormatted: new Date(vmRecord.queuedAt).toISOString(),
          status: "would_restart"
        });
        
        // Acknowledge the message to remove it from the queue
        message.ack();
        
      } catch (error) {
        console.error(`Error processing VM from queue:`, error);
        
        // Don't ack the message on error - it will be retried
        // You could implement more sophisticated retry logic here
      }
    }
    
    console.log(`Processed ${results.length} VMs successfully`);
  }
};