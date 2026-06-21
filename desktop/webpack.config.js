const path = require('path');

const commonConfig = {
  mode: 'development',
  module: {
    rules: [
      {
        test: /\.tsx?$/,
        use: 'ts-loader',
        exclude: /node_modules/,
      },
    ],
  },
  resolve: {
    extensions: ['.tsx', '.ts', '.js'],
    alias: {
      '@phoenix/shared': path.resolve(__dirname, '../shared'),
    },
  },
};

const mainConfig = {
  ...commonConfig,
  entry: './src/main/index.ts',
  target: 'electron-main',
  output: {
    filename: 'index.js',
    path: path.resolve(__dirname, 'dist/main'),
  },
  externals: {
    'better-sqlite3': 'commonjs better-sqlite3',
    'argon2': 'commonjs argon2',
    'adbkit': 'commonjs adbkit',
  },
};

const preloadConfig = {
  ...commonConfig,
  entry: './src/preload.ts',
  target: 'electron-preload',
  output: {
    filename: 'preload.js',
    path: path.resolve(__dirname, 'dist'),
  },
};

const rendererConfig = {
  ...commonConfig,
  entry: './src/renderer/src/App.tsx',
  target: 'electron-renderer',
  output: {
    filename: 'renderer.bundle.js',
    path: path.resolve(__dirname, 'dist/renderer'),
  },
};

module.exports = [mainConfig, preloadConfig, rendererConfig];
