const Flowmap = Vue.defineComponent({
  props: {
    locations: { type: Array, required: true },
    flows: { type: Array, required: true },
  },

  data() {
    return {
      map: null,
      canvas: null,
      ctx: null,
      frameRequested: false,
      mapsApiEndpoint: mapsApiEndpoint,
      translations: window.translations,

      // Location id -> { latlng, label }
      points: {},

      // Interaction
      selectedPoint: null,
      hoveredArrow: null,

      // Hit-test shapes (in screen space)
      dotShapes: [],
      arrowShapes: [],

      // Precomputed logical structures
      clusterDefs: [], // [{ id, memberIds, centerLat, centerLon, radius }]
      clusterByLocationId: {}, // locId -> clusterId
      flowGroups: {}, // "fromClusterId|toClusterId" -> { fromClusterId, toClusterId, flows: [...] }
      currentFlows: [], // normalized + filtered flows

      // Visual scaling
      arrowWidths: [2, 5, 7, 12],
      dotSizes: [6, 8, 10, 12, 14, 16],
      minWeight: null,
      maxWeight: null,

      // Tooltip data
      tooltip: {
        visible: false,
        x: 0,
        y: 0,
        type: null, // "dot" | "arrow"
        content: null,
      },

      // Tile attribution
      attribution: '&copy; <a target="_blank" href="http://osm.org/copyright">OpenStreetMap</a> contributors',
      googleAttribution: `&copy; <a href="https://www.google.com/maps">Google Maps</a>, Imagery ©${this.currentYear} Google, Maxar Technologies`,
    };
  },

  mounted() {
    this.$nextTick(() => {
      this.initMap();
      this.initPoints();
      this.initCanvas();
      // First full build
      this.rebuildShapes();
    });
  },

  watch: {
    locations: {
      deep: true,
      handler() {
        this.selectedPoint = null;
        this.minWeight = null;
        this.maxWeight = null;
        this.initPoints();
        this.rebuildShapes();
      },
    },
    flows: {
      deep: true,
      handler() {
        this.selectedPoint = null;
        this.minWeight = null;
        this.maxWeight = null;
        this.rebuildShapes();
      },
    },
  },

  computed: {
    currentYear() {
      return new Date().getFullYear();
    },
  },

  methods: {
    /* =============================================
     MAP INITIALIZATION
    ============================================= */
    initMap() {
      const el = this.$refs.mapContainer;
      if (!el) return this.$nextTick(() => this.initMap());

      this.map = L.map(el).setView([45.52, -73.57], 12);

      const osmLayer = L.tileLayer(this.mapsApiEndpoint, { attribution: this.attribution }).addTo(this.map);
      
      // If Google maps api key exists then add google layer and control
      if (window.__GOOGLE_MAPS_API_KEY__) {
        const googleLayer = L.tileLayer('https://{s}.google.com/vt/lyrs=s&x={x}&y={y}&z={z}', {
          attribution: this.googleAttribution,
          maxZoom: 20,
          subdomains: ['mt0', 'mt1', 'mt2', 'mt3'],
        });
        const baseMaps = { 'OpenStreetMap': osmLayer, 'Google Satellite': googleLayer };
        L.control.layers(baseMaps).addTo(this.map);
      }

      // Add the fullscreen control with improved readability
      this.map.addControl(
        new L.Control.Fullscreen({
          title: {
            false: this.translations.enterFullscreen_,
            true: this.translations.exitFullscreen_,
          },
        }),
      );

      // Fit to valid locations
      const validLocs = this.locations.filter(
        (loc) => Number.isFinite(loc.lat) && Number.isFinite(loc.lon),
      );

      if (validLocs.length > 0) {
        const bounds = L.latLngBounds(validLocs.map((loc) => [loc.lat, loc.lon]));
        this.map.fitBounds(bounds);
      } else {
        // Fallback world view
        this.map.setView([20, 0], 2);
      }

      this.map.on('click', this.onMapClick);
      this.map.on('mousemove', this.onMapHover);

      // 🔹 FAST PATH: just reposition precomputed shapes
      this.map.on('move', this.scheduleFrame);
      this.map.on('zoom', this.scheduleFrame);
      this.map.on('zoomanim', this.scheduleFrame);

      // 🔹 HEAVY PATH: recompute clusters when zoom starts
      this.map.on('zoomstart', this.rebuildShapes);

      window.addEventListener('resize', this.resizeCanvas);
    },

    scheduleFrame() {
      if (this.frameRequested) return;
      this.frameRequested = true;

      requestAnimationFrame(() => {
        this.drawFrame();
        this.frameRequested = false;
      });
    },

    initPoints() {
      this.points = {};
      this.locations.forEach((loc) => {
        this.points[loc.id] = {
          latlng: L.latLng(loc.lat, loc.lon),
          label: loc.name,
        };
      });
    },

    initCanvas() {
      this.canvas = this.$refs.overlay;
      this.ctx = this.canvas.getContext('2d');
      this.resizeCanvas();
    },

    resizeCanvas() {
      if (!this.canvas || !this.$refs.mapContainer) return;

      const { clientWidth, clientHeight } = this.$refs.mapContainer;
      this.canvas.width = clientWidth;
      this.canvas.height = clientHeight;

      // Canvas size changed → clusters based on pixel distance should update
      this.rebuildShapes();
    },

    /* =============================================
     FLOW NORMALIZATION & SCALING
    ============================================= */
    getFilteredFlows() {
      const base = this.flows.map((f) => ({
        from: f.origin,
        to: f.dest,
        weight: f.count,
      }));

      if (!this.selectedPoint) return base;

      return base.filter((f) => f.from === this.selectedPoint || f.to === this.selectedPoint);
    },

    getArrowWidth(weight) {
      const widths = this.arrowWidths;
      const min = this.minWeight;
      const max = this.maxWeight;

      // Edge case: all weights identical
      if (min === max) {
        return widths[1]; // small but not tiny
      }

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

    getArrowColor(weight, minW, maxW) {
      if (minW === maxW) return 'hsl(173, 55%, 32%)';

      let t = (weight - minW) / (maxW - minW);

      const range = maxW - minW;
      const compression = Math.min(1, range / 5);
      t = Math.min(1, t * compression);

      const sat = 55 + t * 25;
      const light = 60 - t * 50;
      return `hsl(173, ${sat}%, ${light}%)`;
    },

    /* =============================================
     UTILITIES
    ============================================= */
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

    clusterPoints(pixels) {
      const threshold = 50; // px
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

    /* =============================================
     HEAVY REBUILD (CLUSTERS & GROUPS)
     Runs when: flows change, locations change, zoom, selection change
    ============================================= */
    rebuildShapes() {
      if (!this.map || !this.ctx) return;

      const flows = this.getFilteredFlows();
      this.currentFlows = flows;

      this.dotShapes = [];
      this.arrowShapes = [];
      this.clusterDefs = [];
      this.clusterByLocationId = {};
      this.flowGroups = {};

      if (!flows.length) {
        this.drawFrame();
        return;
      }

      // Compute global weight range once per flow dataset
      if (this.minWeight === null || this.maxWeight === null) {
        const weights = flows.map((f) => f.weight);
        this.minWeight = Math.min(...weights);
        this.maxWeight = Math.max(...weights);
      }

      // Per-location traffic (for dot radius)
      const locationTraffic = {};
      flows.forEach((f) => {
        locationTraffic[f.from] = (locationTraffic[f.from] || 0) + f.weight;
        locationTraffic[f.to] = (locationTraffic[f.to] || 0) + f.weight;
      });

      // Project all locations → pixels (at current zoom) for clustering
      const pixels = {};
      for (const id in this.points) {
        pixels[id] = this.map.latLngToContainerPoint(this.points[id].latlng);
      }

      const rawClusters = this.clusterPoints(pixels);

      // Build clusterDefs + mapping locId → clusterId
      rawClusters.forEach((c, index) => {
        const memberIds = c.keys.map((k) => Number(k));

        // Approximate cluster center in lat/lon = average of member locations
        let sumLat = 0;
        let sumLon = 0;
        let count = 0;
        memberIds.forEach((id) => {
          const pt = this.points[id];
          if (pt) {
            sumLat += pt.latlng.lat;
            sumLon += pt.latlng.lng;
            count++;
          }
        });

        const centerLat = count ? sumLat / count : 0;
        const centerLon = count ? sumLon / count : 0;

        // Cluster traffic → dot size
        let clusterTotal = 0;
        memberIds.forEach((id) => {
          clusterTotal += locationTraffic[id] || 0;
        });

        let radius;
        if (this.minWeight === this.maxWeight) {
          radius = this.dotSizes[Math.floor(this.dotSizes.length / 2)];
        } else {
          const ranges = this.dotSizes;
          let t = (clusterTotal - this.minWeight) / (this.maxWeight - this.minWeight);
          const range = this.maxWeight - this.minWeight;
          const compression = Math.min(1, range / 5);
          t = Math.min(1, t * compression);
          const minR = ranges[0];
          const maxR = ranges[ranges.length - 1];
          radius = minR + t * (maxR - minR);
        }

        this.clusterDefs.push({
          id: index,
          memberIds,
          centerLat,
          centerLon,
          radius,
        });

        memberIds.forEach((id) => {
          this.clusterByLocationId[id] = index;
        });
      });

      // Group flows by cluster pair
      const flowGroups = {};
      flows.forEach((f) => {
        const fromClusterId = this.clusterByLocationId[f.from];
        const toClusterId = this.clusterByLocationId[f.to];

        if (fromClusterId == null || toClusterId == null) return;
        if (fromClusterId === toClusterId) return; // skip self-loop in cluster

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

      this.flowGroups = flowGroups;

      // Draw once with fresh shapes
      this.drawFrame();
    },

    /* =============================================
     FAST FRAME DRAWING
     Runs on: move, zoomanim, zoom, resize
     Uses ONLY precomputed clusterDefs + flowGroups
    ============================================= */
    drawFrame() {
      if (!this.ctx || !this.map) return;

      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      this.arrowShapes = [];
      this.dotShapes = [];

      if (!this.clusterDefs.length || !Object.keys(this.flowGroups).length) {
        return;
      }

      // Map clusterId → current pixel coordinates (center)
      const clusterPixels = {};
      this.clusterDefs.forEach((c) => {
        const latlng = L.latLng(c.centerLat, c.centerLon);
        const p = this.map.latLngToContainerPoint(latlng);
        clusterPixels[c.id] = p;
      });

      const minW = this.minWeight ?? 0;
      const maxW = this.maxWeight ?? 0;

      // ------------------------------------------------------
      // SORTED ARROW DRAWING (heaviest flows always on top)
      // ------------------------------------------------------

      const arrowSegments = [];
      const groups = this.flowGroups;

      Object.keys(groups).forEach((key) => {
        const group = groups[key];

        const fromPx = clusterPixels[group.fromClusterId];
        const toPx = clusterPixels[group.toClusterId];
        if (!fromPx || !toPx) return;

        const A = { x: fromPx.x, y: fromPx.y };
        const B = { x: toPx.x, y: toPx.y };

        const oppositeKey = `${group.toClusterId}|${group.fromClusterId}`;
        const opposite = groups[oppositeKey];

        const spacing = 4;
        const { offsetA1, offsetB1, offsetA2, offsetB2 } = this.computeOffsets(A, B, spacing);

        // forward direction (clusterFrom -> clusterTo)
        group.flows.forEach((f) => {
          arrowSegments.push({
            from: offsetA1,
            to: offsetB1,
            weight: f.weight,
            width: this.getArrowWidth(f.weight),
            clusterFrom: group.fromClusterId,
            clusterTo: group.toClusterId,
          });
        });

        // backward direction (clusterTo -> clusterFrom)
        if (opposite) {
          opposite.flows.forEach((f) => {
            arrowSegments.push({
              from: offsetB2,
              to: offsetA2,
              weight: f.weight,
              width: this.getArrowWidth(f.weight),
              clusterFrom: group.toClusterId,
              clusterTo: group.fromClusterId,
            });
          });
        }
      });

      // Sort by weight → draw thin first, heavy last
      arrowSegments.sort((a, b) => a.weight - b.weight);

      // Draw sorted
      arrowSegments.forEach((seg) => {
        this.drawArrowRect(
          seg.from,
          seg.to,
          seg.width,
          seg.clusterFrom,
          seg.clusterTo,
          seg.weight,
          minW,
          maxW,
        );
      });

      // Draw cluster dots
      this.clusterDefs.forEach((c) => {
        const p = clusterPixels[c.id];
        if (!p) return;

        const radius = c.radius;

        ctx.beginPath();
        ctx.arc(p.x, p.y, radius, 0, Math.PI * 2);
        ctx.fillStyle = '#28726c';
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = '#fff';
        ctx.stroke();

        this.dotShapes.push({
          center: { x: p.x, y: p.y },
          radius,
          key: c.memberIds.join(','),
        });
      });
    },

    /* =============================================
     ARROW DRAWING (per arrow, used by drawFrame)
    ============================================= */
    drawArrowRect(p1, p2, width, clusterFrom, clusterTo, weight, minW, maxW) {
      const ctx = this.ctx;

      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len === 0) return;

      const tipW = Math.max(width * 6, 25);
      const bodyLen = Math.max(len - tipW, 0);
      const angle = Math.atan2(dy, dx);
      const overlap = 1;

      ctx.save();
      ctx.translate(p1.x, p1.y);
      ctx.rotate(angle);

      // --- Build arrow path as ONE shape ---
      ctx.beginPath();

      // Top body
      ctx.moveTo(0, -width / 2);
      ctx.lineTo(bodyLen, -width / 2);

      // Tip top
      ctx.lineTo(bodyLen + tipW, -width / 2);

      // Tip bottom (your asymmetry)
      ctx.lineTo(bodyLen - overlap, width + 10);

      // Body bottom
      ctx.lineTo(bodyLen - overlap, width / 2);
      ctx.lineTo(0, width / 2);

      ctx.closePath();

      // --- Stroke shadow FIRST ---
      ctx.lineJoin = "round";
      ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(255,255,255,1)"; // your chosen shadow color
      ctx.lineWidth = 2;
      ctx.stroke();

      // --- Fill arrow ---
      ctx.fillStyle = this.getArrowColor(weight, minW, maxW);
      ctx.fill();

      ctx.restore();

      // Tip point for hit-testing
      const pTip = {
        x: p1.x + Math.cos(angle) * (bodyLen + tipW),
        y: p1.y + Math.sin(angle) * (bodyLen + tipW),
      };

      // Preserve your shape info
      this.arrowShapes.push({
        pStart: p1,
        pTip,
        width,
        clusterFrom,
        clusterTo,
      });
    },

    /* =============================================
     CLICK HANDLING HELPERS
    ============================================= */
    pointInCircle(x, y, dot) {
      const dx = x - dot.center.x;
      const dy = y - dot.center.y;
      return dx * dx + dy * dy <= dot.radius * dot.radius;
    },

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

    getClusterTraffic(id) {
      let outgoing = 0;
      let incoming = 0;

      this.currentFlows.forEach((f) => {
        if (f.from == id) outgoing += f.weight;
        if (f.to == id) incoming += f.weight;
      });

      return { outgoing, incoming };
    },

    // NEW: cluster-aware arrow aggregation with pair breakdown
    getClusterArrowDetails(clusterFrom, clusterTo) {
      const fromCluster = this.clusterDefs[clusterFrom];
      const toCluster = this.clusterDefs[clusterTo];
      if (!fromCluster || !toCluster) {
        return { total: 0, pairs: [], fromMembers: [], toMembers: [] };
      }

      const fromMembers = fromCluster.memberIds;
      const toMembers = toCluster.memberIds;

      const pairsMap = new Map();
      let total = 0;

      this.currentFlows.forEach((f) => {
        if (fromMembers.includes(f.from) && toMembers.includes(f.to)) {
          total += f.weight;
          const key = `${f.from}|${f.to}`;
          if (!pairsMap.has(key)) {
            pairsMap.set(key, {
              fromId: f.from,
              toId: f.to,
              weight: 0,
            });
          }
          const entry = pairsMap.get(key);
          entry.weight += f.weight;
        }
      });

      const pairs = Array.from(pairsMap.values()).map((p) => ({
        ...p,
        fromLabel: this.points[p.fromId]?.label || p.fromId,
        toLabel: this.points[p.toId]?.label || p.toId,
      }));

      // Sort pairs by weight desc
      pairs.sort((a, b) => b.weight - a.weight);

      return { total, pairs, fromMembers, toMembers };
    },

    /* =============================================
     CLICK HANDLING
    ============================================= */
    onMapClick(e) {
      const p = this.map.latLngToContainerPoint(e.latlng);

      // Try dots first
      for (const dot of this.dotShapes) {
        if (this.pointInCircle(p.x, p.y, dot)) {
          const ids = dot.key.split(',').map(Number);
          this.selectedPoint = ids[0];

          let outgoing = 0;
          let incoming = 0;
          ids.forEach((id) => {
            const t = this.getClusterTraffic(id);
            outgoing += t.outgoing;
            incoming += t.incoming;
          });

          this.rebuildShapes();
          return;
        }
      }

       // 2️⃣ Arrow clicks
      for (const arrow of this.arrowShapes) {
        if (this.pointOnArrow(p.x, p.y, arrow)) {
          return;
        }
      }

      // 3️⃣ NOTHING HIT → clear filter
      if (this.selectedPoint !== null) {
        this.clearFilter();
      }
    },

    onMapHover(e) {
      if (!this.map || !this.canvas) return;

      const p = this.map.latLngToContainerPoint(e.latlng);
      let hovering = false;
      let tooltipText = null;

      // Check DOTS
      for (const dot of this.dotShapes) {
        if (this.pointInCircle(p.x, p.y, dot)) {
          hovering = true;

          const ids = dot.key.split(',').map(Number);
          const names = ids.map((id) => this.points[id]?.label || id);

          let outgoing = 0;
          let incoming = 0;

          ids.forEach((id) => {
            const t = this.getClusterTraffic(id);
            outgoing += t.outgoing;
            incoming += t.incoming;
          });

          tooltipText =
            `Cluster:\n` +
            `${names.join(', ')}\n\n` +
            `Outgoing: ${outgoing}\n` +
            `Incoming: ${incoming}`;

          break;
        }
      }

      // Check ARROWS if no dot match
      if (!hovering) {
        for (const arrow of this.arrowShapes) {
          if (this.pointOnArrow(p.x, p.y, arrow)) {
            hovering = true;

            const { clusterFrom, clusterTo } = arrow;
            const { total, pairs, fromMembers, toMembers } =
              this.getClusterArrowDetails(clusterFrom, clusterTo);

            const fromNames = fromMembers.map((id) => this.points[id]?.label || id);
            const toNames = toMembers.map((id) => this.points[id]?.label || id);

            tooltipText =
              `Flow:\n` +
              `${fromNames.join(', ')} → ${toNames.join(', ')}\n\n` +
              `Total Trips: ${total}`;

            if (pairs.length) {
              tooltipText += `\n\nRoutes:\n`;
              pairs.slice(0, 5).forEach((p) => {
                tooltipText += `${p.fromLabel} → ${p.toLabel}: ${p.weight}\n`;
              });

              if (pairs.length > 5) {
                tooltipText += `...and ${pairs.length - 5} more`;
              }
            }

            break;
          }
        }
      }

      // Update cursor
      this.$refs.mapContainer.style.cursor = hovering ? 'pointer' : 'grab';

      // Tooltip handling
      if (hovering) {
        this.tooltip.visible = true;
        this.tooltip.x = p.x + 12;
        this.tooltip.y = p.y + 12;
        this.tooltip.content = tooltipText;
      } else {
        this.tooltip.visible = false;
      }
    },

    clearFilter() {
      this.selectedPoint = null;
      this.rebuildShapes();
    },
  },

  template: `
    <v-container fluid class="pa-0 fill-height position-relative">

      <!-- Map -->
      <div ref="mapContainer" class="w-100 h-100 position-relative"></div>

      <!-- Canvas Overlay -->
      <canvas
        ref="overlay"
        class="position-absolute top-0 left-0 w-100 h-100 pointer-events-none"
        style="zIndex: 1000;"
      ></canvas>

      <!-- Tooltip -->
      <v-card
        v-if="tooltip.visible"
        class="position-absolute pa-3 text-white"
        color="black"
        style="max-width: 320px; zIndex: 1000;"
        :style="{
          left: tooltip.x + 'px',
          top: tooltip.y + 'px'
        }"
        elevation="6"
      >
        <div class="text-body-2" style="white-space: pre-line;">
          {{ tooltip.content }}
        </div>
      </v-card>

    </v-container>

  `,
});
