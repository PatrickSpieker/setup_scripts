# Firebase Auth — Security Rules

Use `request.auth` in Firestore/Storage rules to gate access by sign-in state, UID, or token claims. For rule-writing guidance beyond auth checks, see `firebase-firestore-basics` or `firebase-storage-basics`.

## Common checks

```
// Signed in
allow read, write: if request.auth != null;

// Owns doc by path (match /users/{userId})
allow read, write: if request.auth != null && request.auth.uid == userId;

// Owns doc by field
allow read, write: if request.auth != null && request.auth.uid == resource.data.owner_uid;

// Verified email required
allow create: if request.auth.token.email_verified == true;
```

## Token claims

`request.auth.token` holds standard JWT claims plus any custom claims you set:

- `email`, `email_verified`, `name`, `picture`
- `firebase.sign_in_provider` — e.g. `google.com`, `password`, `anonymous`
- Custom claims set via Admin SDK
