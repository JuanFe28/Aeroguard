import js from '@eslint/js';

export default [
  js.configs.recommended,
  {
    files: ['frontend/src/**/*.js'],
    languageOptions: {
      ecmaVersion: 2022,
      sourceType: 'module',
      globals: {
        // Browser & Web APIs
        window: 'readonly',
        document: 'readonly',
        localStorage: 'readonly',
        sessionStorage: 'readonly',
        AudioContext: 'readonly',
        webkitAudioContext: 'readonly',
        WebSocket: 'readonly',
        fetch: 'readonly',
        setTimeout: 'readonly',
        setInterval: 'readonly',
        clearTimeout: 'readonly',
        clearInterval: 'readonly',
        console: 'readonly',
        navigator: 'readonly',
        URL: 'readonly',
        Blob: 'readonly',
        FileReader: 'readonly',
        requestAnimationFrame: 'readonly',
        cancelAnimationFrame: 'readonly',
        CustomEvent: 'readonly',
        HTMLElement: 'readonly',
        Event: 'readonly',
        // External libraries (Leaflet)
        L: 'readonly',
        // AeroGuard runtime globals injected by index.html
        AEROGUARD_API_URL: 'readonly',
        AEROGUARD_WS_URL: 'readonly',
        AEROGUARD_DEMO_MODE: 'readonly',
        GOOGLE_MAPS_API_KEY: 'readonly',
      },
    },
    rules: {
      'no-unused-vars': [
        'warn',
        { argsIgnorePattern: '^_', varsIgnorePattern: '^_' },
      ],
      'no-undef': 'error',
      'no-const-assign': 'error',
      'no-dupe-keys': 'error',
      'no-unreachable': 'warn',
      'eqeqeq': ['warn', 'smart'],
      'no-var': 'warn',
      'prefer-const': 'warn',
    },
  },
  {
    ignores: [
      '**/node_modules/**',
      '**/dist/**',
      '**/.git/**',
      'backend/**',
      'ai_service/**',
      'sensor_simulator/**',
    ],
  },
];
