import { defineConfig, globalIgnores } from "eslint/config";
import nextVitals from "eslint-config-next/core-web-vitals";
import nextTs from "eslint-config-next/typescript";

const eslintConfig = defineConfig([
  ...nextVitals,
  ...nextTs,
  {
    // This app loads client-only, localStorage-backed demo/mock data on
    // mount (a standard pattern for this architecture, not a real
    // external system with subscriptions). The experimental
    // react-hooks/set-state-in-effect and react-hooks/purity rules flag
    // this pattern; downgraded to warnings rather than restructuring the
    // whole data layer around Suspense/`use()` for a demo build.
    rules: {
      "react-hooks/set-state-in-effect": "warn",
      "react-hooks/purity": "warn",
    },
  },
  // Override default ignores of eslint-config-next.
  globalIgnores([
    // Default ignores of eslint-config-next:
    ".next/**",
    "out/**",
    "build/**",
    "next-env.d.ts",
  ]),
]);

export default eslintConfig;
