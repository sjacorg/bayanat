import resolve from '@rollup/plugin-node-resolve';
import commonjs from '@rollup/plugin-commonjs';
import json from '@rollup/plugin-json';
import terser from '@rollup/plugin-terser';
import replace from '@rollup/plugin-replace';
import postcss from 'rollup-plugin-postcss';
import cssnano from 'cssnano';
import { packageConfigs } from './packages.config.js';

// Always generate minified production bundles
const packages = packageConfigs;


// Common warning handler
const onwarn = (warning, warn) => {
  // Skip certain warnings
  if (warning.code === 'THIS_IS_UNDEFINED') return;
  if (warning.code === 'CIRCULAR_DEPENDENCY') return;
  
  // Use default for everything else
  warn(warning);
};

// Generate configuration for each package
const configs = packages.map(pkg => ({
  input: `src/entries/${pkg.name}.js`,
  output: {
    file: `../js/packages/${pkg.filename}.min.js`,
    format: 'umd',
    name: pkg.globalName,
    globals: {},
    sourcemap: false,
    banner: `
      if (typeof global === 'undefined') {
        var global = globalThis;
      }
      if (typeof process === 'undefined') {
        var process = {
          env: { NODE_ENV: 'production' },
          browser: true,
          version: 'v16.0.0',
          versions: {},
          platform: 'browser'
        };
      }
    `
  },
  plugins: [
    // Extract and minify CSS
    postcss({
      extract: `${pkg.filename}.min.css`,
      minimize: true,
      plugins: [
        cssnano({
          preset: 'default'
        })
      ]
    }),
    
    // Replace Node.js globals with browser-safe alternatives
    replace({
      preventAssignment: true,
      'process.env.NODE_ENV': JSON.stringify('production'),
      'process.browser': 'true',
      'process.version': JSON.stringify('v16.0.0'),
      'process.versions': JSON.stringify({}),
      'process.platform': JSON.stringify('browser'),
      'process.env': JSON.stringify({ NODE_ENV: 'production' }),
      'typeof process': JSON.stringify('object'),
      'global': 'globalThis',
      '__dirname': '""',
      '__filename': '""'
    }),
    
    // Resolve node modules
    resolve({
      browser: true,
      preferBuiltins: false,
      exportConditions: ['browser'],
      skip: ['fs', 'path', 'os']
    }),
    
    // Convert CommonJS modules to ES6
    commonjs({
      include: ['node_modules/**'],
      transformMixedEsModules: true
    }),
    
    // Handle JSON imports
    json(),
    
    // Always minify
    terser({
      compress: {
        drop_console: false,
        drop_debugger: true
      },
      format: {
        comments: false
      }
    })
  ],
  external: [],
  onwarn
}));

export default configs;
