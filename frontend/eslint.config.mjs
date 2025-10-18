import { dirname } from "path";
import { fileURLToPath } from "url";
import { FlatCompat } from "@eslint/eslintrc";

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

const compat = new FlatCompat({
  baseDirectory: __dirname,
});

const eslintConfig = [
  ...compat.extends("next/core-web-vitals", "next/typescript"),
  {
    ignores: [
      "node_modules/**",
      ".next/**",
      "out/**",
      "build/**",
      "next-env.d.ts",
    ],
  },
  {
    rules: {
      // Turn off or downgrade rules to warnings for development
      "@typescript-eslint/no-explicit-any": "off", // Allow 'any' type
      "@typescript-eslint/no-unused-vars": "warn", // Warn instead of error for unused vars
      "react/no-unescaped-entities": "off", // Allow unescaped quotes/apostrophes
      "react-hooks/exhaustive-deps": "warn", // Warn instead of error for hook dependencies
      "@typescript-eslint/no-empty-object-type": "off", // Allow empty interfaces
    },
  },
];

export default eslintConfig;
