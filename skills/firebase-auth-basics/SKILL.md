---
name: firebase-auth-basics
description: Set up and use Firebase Authentication — provisioning, client sign-in flows, and security rules.
---

# Firebase Auth

Set up and use Firebase Authentication — provisioning, client sign-in flows, and security rules.

## Prerequisites

- A Firebase project and the Firebase CLI (`npx -y firebase-tools@latest`). See `firebase-basics` if not set up.

## Provisioning

Google, anonymous, and email/password providers can be enabled via `firebase.json`. Others require the console.

```json
{
  "auth": {
    "providers": {
      "anonymous": true,
      "emailPassword": true,
      "googleSignIn": {
        "oAuthBrandDisplayName": "Your Brand Name",
        "supportEmail": "support@example.com",
        "authorizedRedirectUris": ["https://example.com"]
      }
    }
  }
}
```

For other providers (Facebook, Apple, Twitter, GitHub, Microsoft, Yahoo, phone), enable at https://console.firebase.google.com/project/_/authentication/providers.

## Client SDK

Web: see [references/client_sdk_web.md](references/client_sdk_web.md).

Default to Google Sign-In unless the user asks otherwise.

## Security Rules

Use `request.auth` in Firestore/Storage rules to gate access. See [references/security_rules.md](references/security_rules.md).
