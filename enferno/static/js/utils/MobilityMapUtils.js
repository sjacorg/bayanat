const MobilityMapUtils = {
  CONFIG: {
    colors: {
      arrow: {
        hue: 173, // Base arrow hue
        saturation: [55, 80], // From low → high traffic
        lightness: [60, 10], // From light → dark
        noRange: 'hsl(173, 55%, 32%)', // When all weights are equal
      },
      dot: {
        fill: '#28726c', // Cluster point color
        stroke: '#fff', // Cluster outline
      },
      location: '#00a1f1',
      geo: '#ffbb00',
      geoMain: '#000000',
      event: '#257e74',
      cluster: 'rgba(124, 207, 91, 1)',
      clusterStroke: 'rgba(124, 207, 91, 0.5)',
    },

    map: {
      bounds: {
        south: -85,
        west: -360,
        north: 85,
        east: 360,
      },
      scrollWheelZoom: true,
      defaultZoom: 12,
      minZoom: 2,
      maxBoundsViscosity: 0.1,
      worldCopyJump: false,
      osm: {
        url: window.__MAPS_API_ENDPOINT__,
        attribution:
          '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
      },
      google: {
        url: 'https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}',
        subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
        maxZoom: 20,
        attribution: `&copy; <a href="https://www.google.com/maps">Google Maps</a>, Imagery ©${new Date().getFullYear()} Google, Maxar Technologies`,
      },
    },

    sizes: {
      arrowPaddingCompensation: 0.25,
      bidirectionalArrowSpacing: 1,
      arrowWidths: [1, 2, 3, 4, 5, 6],
      dotSizes: [6, 9, 12, 15, 18, 22],
    },

    clustering: {
      threshold: 50, // Pixel distance for clustering
    },
  },

  // Groups nearby points into pixel clusters
  clusterPoints(pixels) {
    const threshold = this.CONFIG.clustering.threshold;
    const keys = Object.keys(pixels);
    const clusters = [];
    const visited = new Set();

    for (let i = 0; i < keys.length; i++) {
      if (visited.has(keys[i])) continue;

      const p1 = pixels[keys[i]];
      const cluster = { keys: [keys[i]], x: p1.x, y: p1.y };
      visited.add(keys[i]);

      for (let j = i + 1; j < keys.length; j++) {
        if (visited.has(keys[j])) continue;

        const p2 = pixels[keys[j]];
        const dx = p2.x - p1.x;
        const dy = p2.y - p1.y;

        if (Math.sqrt(dx * dx + dy * dy) < threshold) {
          cluster.keys.push(keys[j]);
          cluster.x += p2.x;
          cluster.y += p2.y;
          visited.add(keys[j]);
        }
      }

      // Average cluster center
      cluster.x /= cluster.keys.length;
      cluster.y /= cluster.keys.length;

      clusters.push(cluster);
    }

    return clusters;
  },

  // Hit test for circle-based nodes
  pointInCircle(x, y, dot) {
    const dx = x - dot.center.x;
    const dy = y - dot.center.y;
    return dx * dx + dy * dy <= dot.radius * dot.radius;
  },

  // Hit test for arrow segments
  pointOnArrow(px, py, arrow, ctx) {
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.translate(arrow.origin.x, arrow.origin.y);
    ctx.rotate(arrow.angle);
    const isHit = ctx.isPointInPath(arrow.hitPath, px, py);
    ctx.restore();

    return isHit;
  },

  // Returns arrow color based on weight range
  getArrowColor(weight, minW, maxW) {
    const cfg = this.CONFIG.colors.arrow;

    // All arrows same weight → use static color
    if (minW === maxW) return cfg.noRange;

    let t = (weight - minW) / (maxW - minW);

    // Compress extreme ranges so colors don't blow out
    const compression = Math.min(1, (maxW - minW) / 5);
    t = Math.min(1, t * compression);

    const sat = cfg.saturation[0] + t * (cfg.saturation[1] - cfg.saturation[0]);

    const light = cfg.lightness[0] + t * (cfg.lightness[1] - cfg.lightness[0]);

    return `hsl(${cfg.hue}, ${sat}%, ${light}%)`;
  },

  getAggregationFactor(rawPairs = []) {
    const count = rawPairs.length;
    if (count <= 1) return 0;

    return 1 - Math.exp(-count / 6);
  },

  getArrowWidth(weight, minWeight, maxWeight, rawPairs = []) {
    const widths = this.CONFIG.sizes.arrowWidths;

    if (minWeight === maxWeight) return widths[2];

    // 1. Base size from weight only
    let t = (weight - minWeight) / (maxWeight - minWeight);
    t = Math.min(1, Math.max(0, t));

    const minW = widths[0];
    const maxW = widths[widths.length - 1];
    let baseWidth = minW + t * (maxW - minW);

    // 2. Aggregation factor
    const aggFactor = this.getAggregationFactor(rawPairs);

    // 3. IMPORTANT: only let heavy flows benefit
    const weightGate = Math.pow(t, 1.8);
    // - small flows ≈ 0
    // - big flows ≈ 1

    const maxAggBoost = 1.2; // subtle, not dominant
    const boost = 1 + aggFactor * weightGate * maxAggBoost;

    return baseWidth * boost;
  },

  computeOffsets(p1, p2, offset) {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const len = Math.sqrt(dx * dx + dy * dy);

    if (len === 0) {
      return { offsetA1: p1, offsetB1: p2, offsetA2: p1, offsetB2: p2 };
    }

    const ox = -(dy / len) * offset;
    const oy = (dx / len) * offset;

    return {
      offsetA1: { x: p1.x + ox, y: p1.y + oy },
      offsetB1: { x: p2.x + ox, y: p2.y + oy },
      offsetA2: { x: p1.x - ox, y: p1.y - oy },
      offsetB2: { x: p2.x - ox, y: p2.y - oy },
    };
  },

  async pollUntilDone(
    checkFn,
    { interval = 1500, timeout = 60000, pendingValue = 'pending', statusKey = 'status' } = {},
  ) {
    const start = Date.now();

    while (Date.now() - start < timeout) {
      const result = await checkFn();
      const status = result?.[statusKey];

      if (status !== pendingValue) {
        return result;
      }

      await new Promise((resolve) => setTimeout(resolve, interval));
    }

    throw new Error('Polling timeout');
  },

  createIdGenerator(list) {
    const ids = list
      .map(item => Number(item.id))
      .filter(n => Number.isFinite(n));

    let max = ids.length ? Math.max(...ids) : 0;

    return () => ++max;
  },

  parseLocationsToMapData(locations, options) {
    if (!Array.isArray(locations)) {
      return { locations: [], flows: [] };
    }

    const nextId = this.createIdGenerator(locations);

    const parsed = locations
      .filter((loc) => Number.isFinite(loc.lat) || Number.isFinite(loc.latlng?.lat))
      .map((loc) => { 
        const id = Number.isFinite(Number(loc.id)) ? Number(loc.id) : nextId();
        return {
        id,

        title: loc.title || null,
        title_ar: loc.title_ar || null,
        full_string: loc.full_string || loc.full_location || loc.name || '',

        lat: loc.latlng?.lat ?? loc.lat ?? null,
        lon: loc.latlng?.lng ?? loc.lng ?? null,

        ...(options.showParentId ? { parentId: options.parentId ?? null } : {}),

        // No events → but keep structure for tooltip compatibility
        total_events: 0,
        events: [],
        markerType: 'location',
      }});

    return {
      locations: parsed,
      flows: [], // no flows here
    };
  },

  parseEventsToMapData(events, options = {}) {
    if (!Array.isArray(events)) {
      return { locations: [], flows: [] };
    }

    const nextId = this.createIdGenerator(events.map(ev => ev.location || {}));

    // 1. Sort events chronologically
    const sorted = [...events].sort(
      (a, b) => new Date(a.from_date) - new Date(b.from_date)
    );

    const locationMap = new Map();
    const flowMap = new Map();

    // 2. Build locations
    sorted.forEach((event, index) => {
      const loc = event.location;
      if (!loc) return;

      const id = Number.isFinite(Number(loc.id)) ? Number(loc.id) : nextId();
      const eventType = event.eventtype?.title || null;

      if (!locationMap.has(id)) {
        locationMap.set(id, {
          id,
          title: loc.title,
          title_ar: loc.title_ar,

          full_string: loc.full_location || loc.full_string,

          lat: loc.latlng?.lat ?? loc.lat,
          lon: loc.latlng?.lng ?? loc.lng,

          ...(options.showParentId ? { parentId: loc.parentId ?? null } : {}),
          total_events: 0,

          markerType: 'event',
          events_by_type: {}, // ✅ ADD
          events: [],
        });
      }

      const entry = locationMap.get(id);
      entry.total_events += 1;

      // Aggregate location event types
      if (eventType) {
        entry.events_by_type[eventType] =
          (entry.events_by_type[eventType] || 0) + 1;
      }

      entry.events.push({
        eventId: event.id,
        number: index + 1,
        title: event.title,
        eventType,
        from_date: event.from_date,
        to_date: event.to_date,
        estimated: Boolean(event.estimated),
        main: Boolean(event.main),

        // ✅ Parent shown in tooltip
        ...(options.showParentId ? { parentId: loc.parentId ?? null } : {}),
      });
    });

    // 3. Build flows
    for (let i = 0; i < sorted.length - 1; i++) {
      const currentEvent = sorted[i];
      const nextEvent = sorted[i + 1];

      const current = currentEvent.location;
      const next = nextEvent.location;

      if (!current || !next) continue;
      if (current.id === next.id) continue;

      const key = `${current.id}->${next.id}`;

      if (!flowMap.has(key)) {
        flowMap.set(key, {
          origin: current.id,
          dest: next.id,
          count: 0,
          events_by_type: {},
        });
      }

      const flow = flowMap.get(key);
      flow.count += 1;

      // ✅ USE NEXT EVENT TYPE (this is the fix)
      const eventType = nextEvent.eventtype?.title || null;

      if (eventType) {
        flow.events_by_type[eventType] =
          (flow.events_by_type[eventType] || 0) + 1;
      }
    }

    return {
      locations: Array.from(locationMap.values()),
      flows: Array.from(flowMap.values()),
    };
  },

  parseGeoLocationsToMapData(geoLocations, options = {}) {
    if (!Array.isArray(geoLocations)) {
      return { locations: [], flows: [] };
    }

    const nextId = this.createIdGenerator(geoLocations);

    const parsed = geoLocations
      .filter((loc) => Number.isFinite(loc.lat) && Number.isFinite(loc.lng))
      .map((loc, index) => {
        const id = Number.isFinite(Number(loc.id)) ? Number(loc.id) : nextId();

        return {
          id, // keep IDs separate from event/locations
          number: index + 1,

          title: loc.title || null,
          title_ar: null,

          full_string:
            loc.title || loc.full_string || loc.full_location || loc.geotype?.title || '',

          lat: loc.lat,
          lon: loc.lng,

          ...(options.showParentId ? { parentId: options.parentId ?? null } : {}),

          // match the structure of other location parsers
          total_events: 0,
          events: [],

          // Used for styling / tooltip differentiation (optional)
          markerType: Boolean(loc.main) ? 'geo-main' : 'geo',
          geotypeId: loc.geotype?.id ?? null,
          geotypeTitle: loc.geotype?.title ?? null,
          main: Boolean(loc.main),
          comment: loc.comment || null,
        };
      });

    return {
      locations: parsed,
      flows: [],
    };
  },

  findClosestCluster(newCluster, oldClusters, projFn) {
    let closest = null;
    let minDist = Infinity;

    const newPx = projFn(newCluster.centerLat, newCluster.centerLon);

    oldClusters.forEach((old) => {
      const oldPx = projFn(old.centerLat, old.centerLon);
      const dist = Math.hypot(newPx.x - oldPx.x, newPx.y - oldPx.y);

      if (dist < minDist) {
        minDist = dist;
        closest = old;
      }
    });

    return { cluster: closest, dist: minDist };
  },

  lerp(a, b, t) {
    return a + (b - a) * t;
  },

  filterFlows(flows, selectedPoint = null) {
    const base = flows.map((f) => ({
      from: f.origin,
      to: f.dest,
      weight: f.count,
    }));

    if (!selectedPoint) return base;

    // Single location
    if (typeof selectedPoint === 'number') {
      return base.filter((f) => f.from === selectedPoint || f.to === selectedPoint);
    }

    // Cluster selection
    if (selectedPoint.type === 'cluster') {
      const members = new Set(selectedPoint.memberIds);

      return base.filter((f) => members.has(f.from) || members.has(f.to));
    }

    return base;
  },
  buildClusters({ points, flows, map, minWeight, maxWeight, disableClustering }) {
    const clusterDefs = [];
    const clusterByLocationId = {};
    const flowGroups = {};

    // ---- Weight range ----
    if (minWeight === null || maxWeight === null) {
      const weights = flows.map((f) => f.weight);
      minWeight = Math.min(...weights);
      maxWeight = Math.max(...weights);
    }

    // ---- Traffic per location ----
    const locationTraffic = {};
    flows.forEach((f) => {
      locationTraffic[f.from] = (locationTraffic[f.from] || 0) + f.weight;
      locationTraffic[f.to] = (locationTraffic[f.to] || 0) + f.weight;
    });

    // ---- Project points to pixels ----
    const pixels = {};
    for (const id in points) {
      pixels[id] = map.latLngToContainerPoint(points[id].latlng);
    }

    // ---- Raw clustering ----
    let rawClusters;
    if (disableClustering) {
      rawClusters = Object.keys(pixels).map((key) => {
        const p = pixels[key];

        return {
          keys: [key],
          x: p.x,
          y: p.y,
        };
      });
    } else {
      rawClusters = MobilityMapUtils.clusterPoints(pixels, locationTraffic);
    }

    // ---- Pass 1: build cluster objects + collect totals ----
    const clusterTotals = [];

    rawClusters.forEach((c, index) => {
      const memberIds = c.keys.map((k) => Number(k));

      let sumLat = 0;
      let sumLon = 0;
      let count = 0;

      memberIds.forEach((id) => {
        const pt = points[id];
        if (!pt) return;
        sumLat += pt.latlng.lat;
        sumLon += pt.latlng.lng;
        count++;
      });

      const centerLat = count ? sumLat / count : 0;
      const centerLon = count ? sumLon / count : 0;

      // Cluster traffic total (can be 0 if no in/out)
      let clusterTotal = 0;
      memberIds.forEach((id) => {
        clusterTotal += locationTraffic[id] || 0;
      });
      const identicalCoords = this.areAllSameCoords(memberIds, points);
      clusterTotals.push(clusterTotal);

      clusterDefs.push({
        id: index,
        memberIds,
        centerLat,
        centerLon,
        traffic: clusterTotal, // temp, for radius calc
        identicalCoords,
        radius: 0, // will be set in pass 2
      });

      memberIds.forEach((id) => {
        clusterByLocationId[id] = index;
      });
    });

    // ---- Pass 2: compute global min/max and assign radius ----
    let clusterMin = 0;
    let clusterMax = 0;

    if (clusterTotals.length) {
      clusterMin = Math.min(...clusterTotals);
      clusterMax = Math.max(...clusterTotals);
    }

    clusterDefs.forEach((c) => {
      c.radius = MobilityMapUtils.getClusterRadius(c.traffic, clusterMin, clusterMax);
      delete c.traffic; // no longer needed
    });

    // ---- Group flows by cluster pairs ----
    flows.forEach((f) => {
      const fromClusterId = clusterByLocationId[f.from];
      const toClusterId = clusterByLocationId[f.to];

      if (fromClusterId == null || toClusterId == null) return;
      if (fromClusterId === toClusterId) return;

      const key = `${fromClusterId}|${toClusterId}`;

      if (!flowGroups[key]) {
        flowGroups[key] = {
          fromClusterId,
          toClusterId,
          flows: [],
        };
      }

      flowGroups[key].flows.push({
        fromKey: f.from,
        toKey: f.to,
        weight: f.weight,
      });
    });

    return {
      clusters: clusterDefs,
      clusterByLocationId,
      flowGroups,
      minWeight,
      maxWeight,
    };
  },
  getClusterRadius(clusterTotal, minWeight, maxWeight) {
    const dotSizes = MobilityMapUtils.CONFIG.sizes.dotSizes;

    if (minWeight === maxWeight) {
      return dotSizes[0];
    }

    let t = (clusterTotal - minWeight) / (maxWeight - minWeight);

    const range = maxWeight - minWeight;
    const compression = Math.min(1, range / 5);
    t = Math.min(1, t * compression);

    const minR = dotSizes[0];
    const maxR = dotSizes[dotSizes.length - 1];

    return minR + t * (maxR - minR);
  },
  tooltipCityNames(names = []) {
    const MAX_VISIBLE = 3;

    if (names.length > MAX_VISIBLE) {
      const visible = names.slice(0, MAX_VISIBLE);
      return `${visible.join(', ')} and ${names.length - MAX_VISIBLE} more`;
    }

    return names.join(', ');
  },
  copyCoordinates({ lat, lon }) {
    const text = `${lat.toFixed(6)}, ${lon.toFixed(6)}`;

    return navigator.clipboard.writeText(text);
  },
  getClusterVisualStyle(c, markerTypes, clickToZoomCluster) {
    let fillColor = this.CONFIG.colors.dot.fill;
    let strokeStyle = this.CONFIG.colors.dot.stroke;
    let strokeWidth = 2;
    let dotSize = c.radius;

    // Set color based on marker types if uniform
    if (markerTypes.size === 1) {
      const type = [...markerTypes][0];
      if (type === 'location') fillColor = this.CONFIG.colors.location;
      if (type === 'event') fillColor = this.CONFIG.colors.event;
      if (type === 'geo') fillColor = this.CONFIG.colors.geo;
      if (type === 'geo-main') fillColor = this.CONFIG.colors.geoMain;
    }

    // If it's clustered, use cluster style
    if (c.memberIds.length > 1 && clickToZoomCluster && !c.identicalCoords) {
      fillColor = this.CONFIG.colors.cluster;
      strokeStyle = this.CONFIG.colors.clusterStroke;
      strokeWidth = c.radius * 1.25;
      dotSize = c.radius * 1.2;
    }

    return { fillColor, strokeStyle, strokeWidth, dotSize };
  },
  areAllSameCoords(memberIds, points) {
    if (memberIds.length <= 1) return false;
    const first = points[memberIds[0]].latlng;
    return memberIds.every(id => {
      const ll = points[id].latlng;
      return ll.lat === first.lat && ll.lng === first.lng;
    });
  }
};
