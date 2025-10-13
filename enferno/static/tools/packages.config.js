// Shared package configuration
// This is the single source of truth for all packages

// Helper function to auto-generate name and filename from import
function generatePackageInfo(importPath, globalName) {
  // Convert package name to kebab-case for name/filename
  // Examples:
  // '@deck.gl/core' -> 'deck-gl-core'
  // '@flowmap.gl/data' -> 'flowmap-gl-data' 
  // 'maplibre-gl' -> 'maplibre-gl'
  const name = importPath
    .replace(/^@/, '')           // Remove @ prefix
    .replace(/\//g, '-')        // Replace / with -
    .replace(/\./, '-')        // Replace . with -
    .toLowerCase();
  
  return {
    name,
    import: importPath,
    globalName,
    filename: name  // Same as name for consistency
  };
}

// Define packages with minimal config - name and filename auto-generated
const packageDefinitions = [
  { import: '@deck.gl/core', globalName: 'DeckCore' },
  { import: '@deck.gl/layers', globalName: 'DeckLayers' },
  { import: '@flowmap.gl/data', globalName: 'FlowmapData' },
  { import: '@flowmap.gl/layers', globalName: 'FlowmapLayers' },
  { import: '@math.gl/web-mercator', globalName: 'webMercator' },
  { import: 'maplibre-gl', globalName: 'MaplibreGL' }
];

// Generate full package configs
export const packageConfigs = packageDefinitions.map(def => 
  generatePackageInfo(def.import, def.globalName)
);
