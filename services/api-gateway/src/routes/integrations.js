const express = require('express');
const { clerkClient } = require('@clerk/express');
const { requireAuth } = require('@clerk/express');
const router = express.Router();

/**
 * GET /api/integrations/google/sync
 * Securely fetches the Google OAuth token from Clerk for the authenticated user,
 * and pushes it to the Tool Gateway's internal Vault API.
 */
router.post('/google/sync', requireAuth(), async (req, res) => {
  try {
    const userId = req.auth.userId;
    const tenantId = req.tenant.id; // added by mapTenantMiddleware

    // 1. Fetch the Google OAuth token from Clerk
    // The provider ID is 'oauth_google'
    const response = await clerkClient.users.getUserOauthAccessToken(userId, 'oauth_google');
    
    // clerkClient returns a PaginatedResource or array depending on version.
    // Usually it returns an array of OauthAccessToken objects.
    const tokens = Array.isArray(response) ? response : response.data;
    
    if (!tokens || tokens.length === 0) {
      return res.status(400).json({ error: 'No Google OAuth token found for this user. Connect Google in Clerk first.' });
    }

    const googleToken = tokens[0]; // Get the most recent token

    // Format the payload to match what the Tool Gateway adapter expects
    const tokenPayload = {
      access_token: googleToken.token,
      refresh_token: googleToken.tokenSecret || null, // Clerk sometimes abstracts refresh tokens
      scopes: googleToken.scopes || [],
      // For Google Adapter, we typically need client_id/client_secret but Clerk hides this.
      // If we use Clerk's token, the gateway doesn't need to refresh it itself (Clerk handles refresh).
      // However, our GoogleWorkspaceAdapter expects a standard google-auth Credentials object.
      // We will pass what we have, and Tool Gateway will construct the Credentials.
      token_source: 'clerk'
    };

    // 2. Push to Tool Gateway Vault
    // The Tool Gateway is an internal service, usually reachable via internal networking.
    // We'll use the TOOL_GATEWAY_URL env var.
    const TOOL_GATEWAY_URL = process.env.TOOL_GATEWAY_URL || 'http://localhost:8002';
    
    const fetch = (await import('node-fetch')).default; // Use dynamic import for node-fetch if using v3
    
    const vaultRes = await fetch(`${TOOL_GATEWAY_URL}/internal/vault/google`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        // In production, add a shared internal secret to authenticate this call
        // 'X-Internal-Auth': process.env.INTERNAL_SERVICE_SECRET
      },
      body: JSON.stringify({
        tenant_id: tenantId,
        payload: tokenPayload
      })
    });

    if (!vaultRes.ok) {
      const errorText = await vaultRes.text();
      console.error('Failed to store token in Tool Gateway:', errorText);
      return res.status(500).json({ error: 'Failed to sync token to internal vault' });
    }

    res.json({ success: true, message: 'Google tokens successfully synced to vault' });

  } catch (error) {
    console.error('Error syncing Google OAuth token:', error);
    res.status(500).json({ error: 'Internal server error during token sync' });
  }
});

module.exports = router;
