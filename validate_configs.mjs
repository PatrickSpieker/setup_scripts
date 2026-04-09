#!/usr/bin/env node
// Validates JSON (including JSONC with trailing commas) and YAML files.
// Usage: node validate_configs.mjs <file> [json|yaml]

import { readFileSync } from "fs";
import { createRequire } from "module";

const require = createRequire(import.meta.url);

const file = process.argv[2];
if (!file) {
  console.error("Usage: node validate_configs.mjs <file> [json|yaml]");
  process.exit(1);
}

const type =
  process.argv[3] ||
  (file.endsWith(".yaml") || file.endsWith(".yml") ? "yaml" : "json");

try {
  const content = readFileSync(file, "utf8");
  if (type === "yaml") {
    const yaml = require("js-yaml");
    yaml.load(content);
  } else {
    // Strip trailing commas for JSONC support
    const cleaned = content.replace(/,(\s*[}\]])/g, "$1");
    JSON.parse(cleaned);
  }
  console.log(`OK: ${file}`);
} catch (e) {
  console.error(`FAIL: ${file}: ${e.message}`);
  process.exit(1);
}
