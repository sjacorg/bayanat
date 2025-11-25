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
    },

    map: {
      bounds: {
        south: -85,
        west: -360,
        north: 85,
        east: 360,
      },
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
      bidirectionalArrowSpacing: 4,
      arrowWidths: [2, 5, 7, 12], // Thin → thick based on traffic
      dotSizes: [6, 8, 10, 12, 14, 16],
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
  pointOnArrow(x, y, a) {
    const dx = a.pTip.x - a.pStart.x;
    const dy = a.pTip.y - a.pStart.y;
    const len = Math.sqrt(dx * dx + dy * dy);
    if (!len) return false;

    const ux = dx / len;
    const uy = dy / len;
    const px = x - a.pStart.x;
    const py = y - a.pStart.y;

    const proj = px * ux + py * uy;
    if (proj < 0 || proj > len) return false;

    const perp = Math.abs(-uy * px + ux * py);
    return perp <= a.width / 2 + 4;
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

  getArrowWidth(weight, minWeight, maxWeight) {
    const widths = this.CONFIG.sizes.arrowWidths;
    const min = minWeight;
    const max = maxWeight;

    // Edge case: all weights identical
    if (min === max) return widths[1]; // small but not tiny

    // Normalize 0..1
    let t = (weight - min) / (max - min);

    // 👇 DYNAMIC RANGE COMPRESSION
    const range = max - min;
    const compression = Math.min(1, range / 5);

    t = t * compression;
    t = Math.min(1, t);

    const minW = widths[0];
    const maxW = widths[widths.length - 1];

    return minW + t * (maxW - minW);
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

  parseEventsToMapData(events) {
    if (!Array.isArray(events)) {
      return { locations: [], flows: [] };
    }

    // 1. Sort events chronologically
    const sorted = [...events].sort((a, b) => new Date(a.from_date) - new Date(b.from_date));

    const locationMap = new Map();
    const flowMap = new Map();

    // 2. Build locations
    sorted.forEach((event) => {
      const loc = event.location;
      if (!loc) return;

      const id = loc.id;

      if (!locationMap.has(id)) {
        locationMap.set(id, {
          id,
          name: loc.full_location || loc.title,
          lat: loc.latlng?.lat ?? loc.lat,
          lon: loc.latlng?.lng ?? loc.lng,
          total_events: 0,
        });
      }

      locationMap.get(id).total_events += 1;
    });

    // 3. Build flows
    for (let i = 0; i < sorted.length - 1; i++) {
      const current = sorted[i].location;
      const next = sorted[i + 1].location;

      if (!current || !next) continue;
      if (current.id === next.id) continue;

      const key = `${current.id}->${next.id}`;

      if (!flowMap.has(key)) {
        flowMap.set(key, {
          origin: current.id,
          dest: next.id,
          count: 0,
        });
      }

      flowMap.get(key).count += 1;
    }

    return {
      locations: Array.from(locationMap.values()),
      flows: Array.from(flowMap.values()),
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
  const base = flows.map(f => ({
    from: f.origin,
    to: f.dest,
    weight: f.count,
  }));

  if (!selectedPoint) return base;

  return base.filter(
    f => f.from === selectedPoint || f.to === selectedPoint
  );
},
buildClusters({ points, flows, map, minWeight, maxWeight }) {
  const clusterDefs = [];
  const clusterByLocationId = {};
  const flowGroups = {};

  // ---- Weight range ----
  if (minWeight === null || maxWeight === null) {
    const weights = flows.map(f => f.weight);
    minWeight = Math.min(...weights);
    maxWeight = Math.max(...weights);
  }

  // ---- Traffic per location ----
  const locationTraffic = {};
  flows.forEach((f) => {
    locationTraffic[f.from] = (locationTraffic[f.from] || 0) + f.weight;
    locationTraffic[f.to]   = (locationTraffic[f.to]   || 0) + f.weight;
  });

  // ---- Project points to pixels ----
  const pixels = {};
  for (const id in points) {
    pixels[id] = map.latLngToContainerPoint(points[id].latlng);
  }

  // ---- Raw clustering ----
  const rawClusters = MobilityMapUtils.clusterPoints(pixels);

  // ---- Build cluster objects ----
  rawClusters.forEach((c, index) => {
    const memberIds = c.keys.map(k => Number(k));

    // Center in lat/lon
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

    // Cluster traffic total
    let clusterTotal = 0;
    memberIds.forEach((id) => {
      clusterTotal += locationTraffic[id] || 0;
    });

    // Radius scaling
    const radius = MobilityMapUtils.getClusterRadius(
      clusterTotal,
      minWeight,
      maxWeight
    );

    clusterDefs.push({
      id: index,
      memberIds,
      centerLat,
      centerLon,
      radius,
    });

    memberIds.forEach((id) => {
      clusterByLocationId[id] = index;
    });
  });

  // ---- Group flows by cluster pairs ----
  flows.forEach((f) => {
    const fromClusterId = clusterByLocationId[f.from];
    const toClusterId   = clusterByLocationId[f.to];

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
    return dotSizes[Math.floor(dotSizes.length / 2)];
  }

  let t = (clusterTotal - minWeight) / (maxWeight - minWeight);

  const range = maxWeight - minWeight;
  const compression = Math.min(1, range / 5);
  t = Math.min(1, t * compression);

  const minR = dotSizes[0];
  const maxR = dotSizes[dotSizes.length - 1];

  return minR + t * (maxR - minR);
}

};
