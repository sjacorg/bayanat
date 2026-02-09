const MobilityMapUtils = {
  CONFIG: {
    colors: {
      arrow: {
        hue: 173,
        saturation: [55, 80],
        lightness: [60, 10],
        noRange: 'hsl(173, 55%, 32%)',
      },
      dot: {
        fill: '#28726c',
        stroke: '#fff',
      },
      location: '#00a1f1',
      geo: '#ffbb00',
      geoMain: '#000000',
      event: '#257e74',
      cluster: 'rgba(124, 207, 91, 1)',
      clusterStroke: 'rgba(124, 207, 91, 0.5)',
    },

    map: {
      bounds: { south: -85, west: -360, north: 85, east: 360 },
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
      arrowWidths: [2, 3, 4, 5, 6, 7],
      dotSizes: [6, 9, 12, 15, 18, 22],
    },

    clustering: {
      threshold: 50,
    },
  },

  // =============================================
  // CLUSTERING
  // =============================================

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

      cluster.x /= cluster.keys.length;
      cluster.y /= cluster.keys.length;

      clusters.push(cluster);
    }

    return clusters;
  },

  buildClusters({ points, flows, map, minWeight, maxWeight, disableClustering }) {
    const clusterDefs = [];
    const clusterByLocationId = {};
    const flowGroups = {};

    if (minWeight === null || maxWeight === null) {
      const weights = flows.map((f) => f.weight);
      minWeight = Math.min(...weights);
      maxWeight = Math.max(...weights);
    }

    const locationTraffic = {};
    flows.forEach((f) => {
      locationTraffic[f.from] = (locationTraffic[f.from] || 0) + f.weight;
      locationTraffic[f.to] = (locationTraffic[f.to] || 0) + f.weight;
    });

    const pixels = {};
    for (const id in points) {
      pixels[id] = map.latLngToContainerPoint(points[id].latlng);
    }

    let rawClusters;
    if (disableClustering) {
      rawClusters = Object.keys(pixels).map((key) => ({
        keys: [key],
        x: pixels[key].x,
        y: pixels[key].y,
      }));
    } else {
      rawClusters = this.clusterPoints(pixels, locationTraffic);
    }

    const clusterTotals = [];

    rawClusters.forEach((c, index) => {
      const memberIds = c.keys.map((k) => Number(k));

      let sumLat = 0, sumLon = 0, count = 0;

      memberIds.forEach((id) => {
        const pt = points[id];
        if (!pt) return;
        sumLat += pt.latlng.lat;
        sumLon += pt.latlng.lng;
        count++;
      });

      let clusterTotal = 0;
      memberIds.forEach((id) => {
        clusterTotal += locationTraffic[id] || 0;
      });

      clusterTotals.push(clusterTotal);

      clusterDefs.push({
        id: index,
        memberIds,
        centerLat: count ? sumLat / count : 0,
        centerLon: count ? sumLon / count : 0,
        traffic: clusterTotal,
        radius: 0,
      });

      memberIds.forEach((id) => {
        clusterByLocationId[id] = index;
      });
    });

    let clusterMin = 0, clusterMax = 0;
    if (clusterTotals.length) {
      clusterMin = Math.min(...clusterTotals);
      clusterMax = Math.max(...clusterTotals);
    }

    clusterDefs.forEach((c) => {
      c.radius = this.getClusterRadius(c.traffic, clusterMin, clusterMax);
      delete c.traffic;
    });

    flows.forEach((f) => {
      const fromClusterId = clusterByLocationId[f.from];
      const toClusterId = clusterByLocationId[f.to];

      if (fromClusterId == null || toClusterId == null) return;
      if (fromClusterId === toClusterId) return;

      const key = `${fromClusterId}|${toClusterId}`;

      if (!flowGroups[key]) {
        flowGroups[key] = { fromClusterId, toClusterId, flows: [] };
      }

      flowGroups[key].flows.push({
        fromKey: f.from,
        toKey: f.to,
        weight: f.weight,
      });
    });

    return { clusters: clusterDefs, clusterByLocationId, flowGroups, minWeight, maxWeight };
  },

  getClusterRadius(clusterTotal, minWeight, maxWeight) {
    const dotSizes = this.CONFIG.sizes.dotSizes;

    if (minWeight === maxWeight) return dotSizes[0];

    let t = (clusterTotal - minWeight) / (maxWeight - minWeight);
    const compression = Math.min(1, (maxWeight - minWeight) / 5);
    t = Math.min(1, t * compression);

    return dotSizes[0] + t * (dotSizes[dotSizes.length - 1] - dotSizes[0]);
  },

  getClusterPixels(clusters, map) {
    const pixels = {};
    clusters.forEach((c) => {
      pixels[c.id] = map.latLngToContainerPoint(L.latLng(c.centerLat, c.centerLon));
    });
    return pixels;
  },

  getClusterVisualStyle(cluster, markerTypes, clickToZoomCluster) {
    let fillColor = this.CONFIG.colors.dot.fill;
    let strokeStyle = this.CONFIG.colors.dot.stroke;
    let strokeWidth = 2;
    let dotSize = cluster.radius;

    if (markerTypes.size === 1) {
      const type = [...markerTypes][0];
      if (type === 'location') fillColor = this.CONFIG.colors.location;
      if (type === 'event') fillColor = this.CONFIG.colors.event;
      if (type === 'geo') fillColor = this.CONFIG.colors.geo;
      if (type === 'geo-main') fillColor = this.CONFIG.colors.geoMain;
    }

    if (cluster.memberIds.length > 1 && clickToZoomCluster) {
      fillColor = this.CONFIG.colors.cluster;
      strokeStyle = this.CONFIG.colors.clusterStroke;
      strokeWidth = cluster.radius * 1.25;
      dotSize = cluster.radius * 1.2;
    }

    return { fillColor, strokeStyle, strokeWidth, dotSize };
  },

  // =============================================
  // ARROW PROCESSING
  // =============================================

  prepareArrowSegments(flowGroups, clusterPixels) {
    const merged = {};

    Object.values(flowGroups).forEach((group) => {
      const fromPx = clusterPixels[group.fromClusterId];
      const toPx = clusterPixels[group.toClusterId];
      if (!fromPx || !toPx) return;

      const key = `${group.fromClusterId}->${group.toClusterId}`;

      const entry = (merged[key] ??= {
        fromCluster: group.fromClusterId,
        toCluster: group.toClusterId,
        start: fromPx,
        end: toPx,
        rawPairs: [],
        weight: 0,
      });

      group.flows.forEach((f) => {
        entry.weight += f.weight;
        entry.rawPairs.push({ fromId: f.fromKey, toId: f.toKey, weight: f.weight });
      });
    });

    const segments = Object.values(merged);
    if (!segments.length) return { segments: [], arrowMin: 0, arrowMax: 0 };

    const [arrowMin, arrowMax] = this.getMinMax(segments.map((s) => s.weight));

    // Compute widths
    segments.forEach((seg) => {
      seg.width = this.getArrowWidth(seg.weight, arrowMin, arrowMax, seg.rawPairs);
    });

    // Apply bidirectional spacing
    const baseSpacing = this.CONFIG.sizes.bidirectionalArrowSpacing;
    const comp = this.CONFIG.sizes.arrowPaddingCompensation;

    segments.forEach((seg) => {
      const opposite = merged[`${seg.toCluster}->${seg.fromCluster}`];
      const thisHalf = seg.width * comp;
      const oppositeHalf = opposite ? opposite.width * comp : 0;
      const offset = thisHalf + oppositeHalf + baseSpacing;

      const { offsetA1, offsetB1 } = this.computeOffsets(seg.start, seg.end, offset);
      seg.from = offsetA1;
      seg.to = offsetB1;
    });

    return { segments, arrowMin, arrowMax };
  },

  getArrowColor(weight, minW, maxW) {
    const cfg = this.CONFIG.colors.arrow;
    if (minW === maxW) return cfg.noRange;

    let t = (weight - minW) / (maxW - minW);
    const compression = Math.min(1, (maxW - minW) / 5);
    t = Math.min(1, t * compression);

    const sat = cfg.saturation[0] + t * (cfg.saturation[1] - cfg.saturation[0]);
    const light = cfg.lightness[0] + t * (cfg.lightness[1] - cfg.lightness[0]);

    return `hsl(${cfg.hue}, ${sat}%, ${light}%)`;
  },

  getArrowWidth(weight, minWeight, maxWeight, rawPairs = []) {
    const widths = this.CONFIG.sizes.arrowWidths;
    if (minWeight === maxWeight) return widths[2];

    let t = (weight - minWeight) / (maxWeight - minWeight);
    t = Math.min(1, Math.max(0, t));

    const baseWidth = widths[0] + t * (widths[widths.length - 1] - widths[0]);

    // Aggregation boost for heavy flows
    const count = rawPairs.length;
    const aggFactor = count <= 1 ? 0 : 1 - Math.exp(-count / 6);
    const weightGate = Math.pow(t, 1.8);
    const boost = 1 + aggFactor * weightGate * 1.2;

    return baseWidth * boost;
  },

  computeOffsets(p1, p2, offset) {
    const dx = p2.x - p1.x;
    const dy = p2.y - p1.y;
    const len = Math.sqrt(dx * dx + dy * dy);

    if (len === 0) {
      return { offsetA1: p1, offsetB1: p2 };
    }

    const ox = -(dy / len) * offset;
    const oy = (dx / len) * offset;

    return {
      offsetA1: { x: p1.x + ox, y: p1.y + oy },
      offsetB1: { x: p2.x + ox, y: p2.y + oy },
    };
  },

  // =============================================
  // HIT TESTING
  // =============================================

  pointInCircle(x, y, dot) {
    const dx = x - dot.center.x;
    const dy = y - dot.center.y;
    return dx * dx + dy * dy <= dot.radius * dot.radius;
  },

  pointOnArrow(px, py, arrow, ctx) {
    ctx.save();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.translate(arrow.origin.x, arrow.origin.y);
    ctx.rotate(arrow.angle);
    const isHit = ctx.isPointInPath(arrow.hitPath, px, py);
    ctx.restore();
    return isHit;
  },

  // =============================================
  // FLOW FILTERING
  // =============================================

  filterFlows(flows, selectedPoint = null) {
    const base = flows.map((f) => ({
      from: f.origin,
      to: f.dest,
      weight: f.count,
    }));

    if (!selectedPoint) return base;

    if (typeof selectedPoint === 'number') {
      return base.filter((f) => f.from === selectedPoint || f.to === selectedPoint);
    }

    if (selectedPoint.type === 'cluster') {
      const members = new Set(selectedPoint.memberIds);
      return base.filter((f) => members.has(f.from) || members.has(f.to));
    }

    return base;
  },

  // =============================================
  // DATA PARSING
  // =============================================

  createIdGenerator(list) {
    const ids = list.map((item) => Number(item.id)).filter((n) => Number.isFinite(n));
    let max = ids.length ? Math.max(...ids) : 0;
    return () => ++max;
  },

  parseLocationsToMapData(locations, options) {
    if (!Array.isArray(locations)) return { locations: [], flows: [] };

    const nextId = this.createIdGenerator(locations);

    const parsed = locations
      .filter((loc) => Number.isFinite(loc.lat) || Number.isFinite(loc.latlng?.lat))
      .map((loc) => ({
        id: Number.isFinite(Number(loc.id)) ? Number(loc.id) : nextId(),
        title: loc.title || null,
        title_ar: loc.title_ar || null,
        full_string: loc.full_string || loc.full_location || loc.name || '',
        lat: loc.latlng?.lat ?? loc.lat ?? null,
        lon: loc.latlng?.lng ?? loc.lng ?? null,
        ...(options.showParentId ? { parentId: options.parentId ?? null } : {}),
        total_events: 0,
        events: [],
        markerType: 'location',
      }));

    return { locations: parsed, flows: [] };
  },

  parseEventsToMapData(events, options = {}) {
    if (!Array.isArray(events)) return { locations: [], flows: [] };

    const nextId = this.createIdGenerator(events.map((ev) => ev.location || {}));
    const sorted = [...events].sort((a, b) => new Date(a.from_date) - new Date(b.from_date));

    const locationMap = new Map();
    const flowMap = new Map();

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
          events_by_type: {},
          events: [],
        });
      }

      const entry = locationMap.get(id);
      entry.total_events += 1;

      if (eventType) {
        entry.events_by_type[eventType] = (entry.events_by_type[eventType] || 0) + 1;
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
        ...(options.showParentId ? { parentId: loc.parentId ?? null } : {}),
      });
    });

    for (let i = 0; i < sorted.length - 1; i++) {
      const current = sorted[i].location;
      const next = sorted[i + 1].location;

      if (!current || !next || current.id === next.id) continue;

      const key = `${current.id}->${next.id}`;

      if (!flowMap.has(key)) {
        flowMap.set(key, { origin: current.id, dest: next.id, count: 0, events_by_type: {} });
      }

      const flow = flowMap.get(key);
      flow.count += 1;

      const eventType = sorted[i + 1].eventtype?.title || null;
      if (eventType) {
        flow.events_by_type[eventType] = (flow.events_by_type[eventType] || 0) + 1;
      }
    }

    return {
      locations: Array.from(locationMap.values()),
      flows: Array.from(flowMap.values()),
    };
  },

  parseGeoLocationsToMapData(geoLocations, options = {}) {
    if (!Array.isArray(geoLocations)) return { locations: [], flows: [] };

    const nextId = this.createIdGenerator(geoLocations);

    const parsed = geoLocations
      .filter((loc) => Number.isFinite(loc.lat) && Number.isFinite(loc.lng))
      .map((loc, index) => ({
        id: Number.isFinite(Number(loc.id)) ? Number(loc.id) : nextId(),
        number: index + 1,
        title: loc.title || null,
        title_ar: null,
        full_string: loc.title || loc.full_string || loc.full_location || loc.geotype?.title || '',
        lat: loc.lat,
        lon: loc.lng,
        ...(options.showParentId ? { parentId: options.parentId ?? null } : {}),
        total_events: 0,
        events: [],
        markerType: Boolean(loc.main) ? 'geo-main' : 'geo',
        geotypeId: loc.geotype?.id ?? null,
        geotypeTitle: loc.geotype?.title ?? null,
        main: Boolean(loc.main),
        comment: loc.comment || null,
      }));

    return { locations: parsed, flows: [] };
  },

  // =============================================
  // UTILITIES
  // =============================================

  getMinMax(values = []) {
    if (!values.length) return [0, 0];
    return [Math.min(...values), Math.max(...values)];
  },

  tooltipCityNames(names = []) {
    const MAX_VISIBLE = 3;
    if (names.length > MAX_VISIBLE) {
      const visible = names.slice(0, MAX_VISIBLE);
      return window.translations.cityListWithMore_(visible, names.length - MAX_VISIBLE);
    }
    return names.join(', ');
  },

  copyCoordinates({ lat, lon }) {
    return navigator.clipboard.writeText(`${lat.toFixed(6)}, ${lon.toFixed(6)}`);
  },

  async pollUntilDone(
    checkFn,
    { interval = 1500, timeout = 60000, pendingValue = 'pending', statusKey = 'status' } = {}
  ) {
    const start = Date.now();

    while (Date.now() - start < timeout) {
      const result = await checkFn();
      if (result?.[statusKey] !== pendingValue) return result;
      await new Promise((resolve) => setTimeout(resolve, interval));
    }

    throw new Error('Polling timeout');
  },
};
