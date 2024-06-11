// webhook-handler.ts
// Receives webhook POST requests and sends VM info to queue
// Includes API key authentication for security

// Types
interface VMRecord {
  resourceGroup: string;
  vmName: string;
  queuedAt: number;
  status: 'pending';
}

interface WebhookPayload {
  resourceGroup: string;
  vmName: string;
}

interface WebhookResponse {
  success: boolean;
  message: string;
  timestamp: string;
}

interface CloudflareEnvironment {
  QUEUE_NAME: Queue<VMRecord>;
  WEBHOOK_API_KEY: string;  // Secret for authenticating webhook requests
  ENVIRONMENT?: string;
  LOG_LEVEL?: string;
}

export default {
  async fetch(request: Request, env: CloudflareEnvironment, ctx: ExecutionContext): Promise<Response> {
    // Get the URL path
    const url = new URL(request.url);
    const path = url.pathname;
    
    // Only proceed if this is a webhook request
    if (!path.startsWith('/webhook')) {
      return new Response('Not found. Use /webhook endpoint for webhooks.', { status: 404 });
    }
    
    // Only accept POST requests
    if (request.method !== 'POST') {
      return new Response('Method not allowed. Only POST requests are accepted.', { status: 405 });
    }

    // Validate API key authentication
    const authHeader = request.headers.get('Authorization');
    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      console.warn('Missing or invalid Authorization header');
      return new Response('Unauthorized: Missing API key', { status: 401 });
    }

    const providedApiKey = authHeader.substring(7); // Remove "Bearer " prefix
    if (providedApiKey !== env.WEBHOOK_API_KEY) {
      console.warn('Invalid API key provided');
      return new Response('Unauthorized: Invalid API key', { status: 401 });
    }

    try {
      // Parse the webhook payload
      const payload: WebhookPayload = await request.json();
      
      // Extract VM details
      const { resourceGroup, vmName } = payload;
      
      if (!resourceGroup || !vmName) {
        return new Response('Missing required fields: resourceGroup and vmName', { status: 400 });
      }

      // Basic input validation
      if (typeof resourceGroup !== 'string' || typeof vmName !== 'string') {
        return new Response('Invalid field types: resourceGroup and vmName must be strings', { status: 400 });
      }

      // Sanitize input - only allow alphanumeric, hyphens, and underscores
      if (!/^[a-zA-Z0-9_-]+$/.test(resourceGroup) || !/^[a-zA-Z0-9_-]+$/.test(vmName)) {
        return new Response('Invalid characters in resourceGroup or vmName', { status: 400 });
      }

      // Create a VM record
      const now = Date.now();
      const vmRecord: VMRecord = {
        resourceGroup,
        vmName,
        queuedAt: now,
        status: 'pending'
      };

      // Send to queue directly using the binding
      await env.QUEUE_NAME.send(vmRecord);
      
      console.log(`VM queued: ${resourceGroup}/${vmName}, at: ${new Date(now).toISOString()}`);

      // Return success response
      const response: WebhookResponse = {
        success: true,
        message: `VM queued: ${resourceGroup}/${vmName}`,
        timestamp: new Date(now).toISOString()
      };

      return new Response(JSON.stringify(response), { 
        status: 200,
        headers: { 'Content-Type': 'application/json' }
      });
      
    } catch (error) {
      console.error('Error in webhook handler:', error);
      const errorMessage = error instanceof Error ? error.message : 'Unknown error occurred';
      return new Response(`Error: ${errorMessage}`, { status: 500 });
    }
  }
};