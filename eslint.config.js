import js from "@eslint/js";
import globals from "globals";
import tseslint from "typescript-eslint";

export default tseslint.config(
  {
    extends: [js.configs.recommended, tseslint.configs.recommendedTypeChecked],
    files: ["frontend/src/**/*.{ts,js}"],
    languageOptions: {
      globals: globals.browser,
      parserOptions: {
        projectService: true,
        tsconfigRootDir: import.meta.dirname,
      },
    },
  },
  {
    extends: [js.configs.recommended],
    files: ["utils/**/*.js"],
    languageOptions: {
      globals: globals.browser,
    },
  },
);
