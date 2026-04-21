# Firebase Web Setup

Canonical `firebase.js` init for a web app. Other Firebase web skills (Auth, Firestore, Storage) import `app` from this module.

## 1. Register a web app

```bash
npx -y firebase-tools@latest apps:create web <nickname>
```

Returns an App ID. Then fetch the config object:

```bash
npx -y firebase-tools@latest apps:sdkconfig <APP_ID>
```

You can also grab the config from the Firebase console (Project settings → Your apps).

## 2. Install

```bash
npm install firebase
```

## 3. Initialize

```javascript
// firebase.js
import { initializeApp } from "firebase/app";

const firebaseConfig = {
  apiKey: "API_KEY",
  authDomain: "PROJECT_ID.firebaseapp.com",
  projectId: "PROJECT_ID",
  storageBucket: "PROJECT_ID.firebasestorage.app",
  messagingSenderId: "SENDER_ID",
  appId: "APP_ID",
};

export const app = initializeApp(firebaseConfig);
```

Consumers import `app` and pass it to service getters:

```javascript
import { app } from "./firebase";
import { getAuth } from "firebase/auth";
import { getFirestore } from "firebase/firestore";

const auth = getAuth(app);
const db = getFirestore(app);
```
