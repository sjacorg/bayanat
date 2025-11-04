#!/usr/bin/env node

import fs from 'fs/promises';
import path from 'path';
import { packageConfigs, cssPackages } from './packages.config.js';

// Create src/entries directory if it doesn't exist
const entriesDir = 'src/entries';
try {
  await fs.mkdir(entriesDir, { recursive: true });
} catch (error) {
  // Directory already exists
}

// Generate individual entry files
for (const config of packageConfigs) {
  const cssImport = cssPackages[config.name] 
    ? `// Import CSS for styling
import '${cssPackages[config.name]}';

`
    : '';

  const entryContent = `// Auto-generated entry file for ${config.name}
${cssImport}// Import only the specific package we need
import * as PackageModule from '${config.import}';

// Export for module systems
export default PackageModule;

// Also attach to window for direct browser usage
if (typeof window !== 'undefined') {
  window.${config.globalName} = PackageModule;
}
`;

  const entryPath = path.join(entriesDir, `${config.name}.js`);
  await fs.writeFile(entryPath, entryContent, 'utf8');
  console.log(`Generated: ${entryPath}`);
}

console.log(`\n✅ Generated ${packageConfigs.length} entry files in ${entriesDir}/`);