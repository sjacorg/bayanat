// Import all required packages
import * as DeckCore from '@deck.gl/core';
import * as DeckLayers from '@deck.gl/layers';
import * as FlowmapData from '@flowmap.gl/data';
import * as FlowmapLayers from '@flowmap.gl/layers';

// Create the FlowmapBundle global object
const FlowmapBundle = {
  // Flowmap.gl packages
  FlowmapData,
  FlowmapLayers,
  
  // Deck.gl packages
  DeckCore,
  DeckLayers,
};

// Export for module systems
export default FlowmapBundle;

// Also attach to window for direct browser usage
if (typeof window !== 'undefined') {
  window.FlowmapBundle = FlowmapBundle;
}