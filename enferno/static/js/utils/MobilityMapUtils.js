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
};
