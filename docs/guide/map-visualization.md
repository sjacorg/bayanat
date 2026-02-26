# Map Visualization

The Map Visualization feature renders actor movement patterns on an interactive map, showing how individuals moved between locations over time based on their life events.

## Accessing the Map

Open the Map Visualization from the Actors page toolbar. The map uses your current search query, so any active filters (text search, advanced search, labels, etc.) carry over to scope which actors appear on the map.

## How It Works

Bayanat analyzes each actor's events chronologically. When an actor has events at different locations, those locations become nodes on the map and the transitions between them become directional flows (arrows). The map aggregates this across all matching actors to reveal patterns.

## Map Elements

### Nodes (Locations)

Circles on the map represent locations where events occurred. Size and color indicate volume: locations with more events appear larger and shift from blue (low) through green (mid) to red (high). Hover over a node to see its name and event count.

### Flows (Arrows)

Curved arrows between locations represent movement. Arrow thickness and color follow the same volume scale. Arrows are directional, showing which way actors moved. At lower zoom levels, nearby nodes cluster together automatically.

## Interacting with the Map

### Clicking a Node

Opens a panel listing all actors who have events at that location, along with context about each actor's previous and next event in their timeline.

### Clicking a Flow

Opens a panel listing actors who moved between those two specific locations, showing the origin and destination events for each actor.

### Event Type Filter

Use the event type dropdown to filter the visualization by specific event types (e.g., Arrest, Detention). The map and actor lists update to show only matching events.

### Actor Drill-down

Click any actor in the side panel to open their full profile in the standard actor drawer.

## Base Layers

The map supports OpenStreetMap and Google Satellite imagery, switchable from the layer control.
