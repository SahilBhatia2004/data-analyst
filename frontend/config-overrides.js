const webpack = require('webpack');

module.exports = function override(config, env) {
  // Ignore source map warnings
  config.ignoreWarnings = [
    { module: /@plotly\/mapbox-gl/ },
    { file: /@plotly\/mapbox-gl/ },
  ];

  // Fix Node.js polyfill issues
  config.resolve.fallback = {
    ...config.resolve.fallback,
    stream: require.resolve('stream-browserify'),
    assert: require.resolve('assert/'),
    buffer: require.resolve('buffer/'),
    crypto: require.resolve('crypto-browserify'),
    util: require.resolve('util/'),
    path: require.resolve('path-browserify'),
    fs: false,
    os: false,
    tls: false,
    net: false,
    http: false,
    https: false,
    zlib: false,
    url: false,
  };

  return config;
};
