# Firebase Auth — Web SDK

## Init

```javascript
import { getAuth, connectAuthEmulator } from "firebase/auth";
import { app } from "./firebase";

const auth = getAuth(app);

// Emulator (default port 9099)
if (location.hostname === "localhost") {
  connectAuthEmulator(auth, "http://localhost:9099");
}

export { auth };
```

## Email/Password

```javascript
import { createUserWithEmailAndPassword, signInWithEmailAndPassword } from "firebase/auth";

await createUserWithEmailAndPassword(auth, email, password); // sign up
await signInWithEmailAndPassword(auth, email, password);     // sign in
```

## OAuth Popup (Google, Facebook, Apple, etc.)

Same pattern for every federated provider — only the provider class differs.

```javascript
import { signInWithPopup, GoogleAuthProvider } from "firebase/auth";

const provider = new GoogleAuthProvider();
const result = await signInWithPopup(auth, provider);
const user = result.user;
// Optional: provider access token
const credential = GoogleAuthProvider.credentialFromResult(result);
const token = credential?.accessToken;
```

| Provider  | Import / constructor                  |
| --------- | ------------------------------------- |
| Google    | `new GoogleAuthProvider()`            |
| Facebook  | `new FacebookAuthProvider()`          |
| Twitter   | `new TwitterAuthProvider()`           |
| GitHub    | `new GithubAuthProvider()`            |
| Apple     | `new OAuthProvider('apple.com')`      |
| Microsoft | `new OAuthProvider('microsoft.com')`  |
| Yahoo     | `new OAuthProvider('yahoo.com')`      |

For `OAuthProvider` providers, use `OAuthProvider.credentialFromResult(result)` to extract the credential.

## Anonymous

```javascript
import { signInAnonymously } from "firebase/auth";
await signInAnonymously(auth);
```

## Email Link (passwordless)

Send:
```javascript
import { sendSignInLinkToEmail } from "firebase/auth";

await sendSignInLinkToEmail(auth, email, {
  url: "https://www.example.com/finishSignUp",
  handleCodeInApp: true,
});
window.localStorage.setItem("emailForSignIn", email);
```

Complete (on the landing page):
```javascript
import { isSignInWithEmailLink, signInWithEmailLink } from "firebase/auth";

if (isSignInWithEmailLink(auth, window.location.href)) {
  const email = window.localStorage.getItem("emailForSignIn")
    ?? window.prompt("Confirm your email");
  await signInWithEmailLink(auth, email, window.location.href);
  window.localStorage.removeItem("emailForSignIn");
}
```

The redirect domain must be in the Firebase Console authorized domains list.

## Observe Auth State

```javascript
import { onAuthStateChanged } from "firebase/auth";

onAuthStateChanged(auth, (user) => {
  if (user) {
    const uid = user.uid;
  } else {
    // signed out
  }
});
```

## Sign Out

```javascript
import { signOut } from "firebase/auth";
await signOut(auth);
```
