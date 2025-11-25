const MobilityMap = Vue.defineComponent({
  props: {
    locations: { type: Array, required: true },
    flows: { type: Array, required: true },
  },

  data() {
    return {
      canvas: null,
      ctx: null,
      frameRequested: false,
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
      minWeight: null,
      maxWeight: null,

      // Tooltip data
      tooltip: {
        visible: false,
        x: 0,
        y: 0,
        type: null,
        data: null,
      },
    };
  },

  mounted() {
    // IMPORTANT: do NOT define `map` inside data()
    // Leaflet map objects must stay non-reactive or Vue will break internal state (e.g. during zoom).
    // This keeps it as a runtime-only property instead of a Vue-tracked one.
    this.map = null;
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

      const worldBounds = L.latLngBounds(L.latLng(MobilityMapUtils.CONFIG.map.bounds.south, MobilityMapUtils.CONFIG.map.bounds.west), L.latLng(MobilityMapUtils.CONFIG.map.bounds.north, MobilityMapUtils.CONFIG.map.bounds.east));

      this.map = L.map(el, {
        minZoom: MobilityMapUtils.CONFIG.map.minZoom,
        maxBoundsViscosity: MobilityMapUtils.CONFIG.map.maxBoundsViscosity,
        worldCopyJump: MobilityMapUtils.CONFIG.map.worldCopyJump,
        maxBounds: worldBounds,
      }).setView(geoMapDefaultCenter, MobilityMapUtils.CONFIG.map.defaultZoom);

      const osmLayer = L.tileLayer(MobilityMapUtils.CONFIG.map.osm.url, { attribution: MobilityMapUtils.CONFIG.map.osm.attribution }).addTo(this.map);

      // If Google maps api key exists then add google layer and control
      if (window.__GOOGLE_MAPS_API_KEY__) {
        const googleLayer = L.tileLayer(MobilityMapUtils.CONFIG.map.google.url, {
          attribution: MobilityMapUtils.CONFIG.map.google.attribution,
          maxZoom: MobilityMapUtils.CONFIG.map.google.maxZoom,
          subdomains: MobilityMapUtils.CONFIG.map.google.subdomains,
        });
        const baseMaps = { OpenStreetMap: osmLayer, 'Google Satellite': googleLayer };
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
        this.map.setView(geoMapDefaultCenter, 2);
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

      const rawClusters = MobilityMapUtils.clusterPoints(pixels);

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
        const dotSizes = MobilityMapUtils.CONFIG.sizes.dotSizes;
        if (this.minWeight === this.maxWeight) {
          radius = dotSizes[Math.floor(dotSizes.length / 2)];
        } else {
          const ranges = dotSizes;
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

        const spacing = MobilityMapUtils.CONFIG.sizes.bidirectionalArrowSpacing;
        const { offsetA1, offsetB1, offsetA2, offsetB2 } = MobilityMapUtils.computeOffsets(
          A,
          B,
          spacing,
        );

        // forward direction (clusterFrom -> clusterTo)
        group.flows.forEach((f) => {
          arrowSegments.push({
            from: offsetA1,
            to: offsetB1,
            weight: f.weight,
            width: MobilityMapUtils.getArrowWidth(f.weight, this.minWeight, this.maxWeight),
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
              width: MobilityMapUtils.getArrowWidth(f.weight, this.minWeight, this.maxWeight),
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
        ctx.fillStyle = MobilityMapUtils.CONFIG.colors.dot.fill;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = MobilityMapUtils.CONFIG.colors.dot.stroke;
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
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.strokeStyle = 'rgba(255,255,255,1)'; // your chosen shadow color
      ctx.lineWidth = 2;
      ctx.stroke();

      // --- Fill arrow ---
      ctx.fillStyle = MobilityMapUtils.getArrowColor(weight, minW, maxW);
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
        if (MobilityMapUtils.pointInCircle(p.x, p.y, dot)) {
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
        if (MobilityMapUtils.pointOnArrow(p.x, p.y, arrow)) {
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

      // Check DOTS
      for (const dot of this.dotShapes) {
        if (MobilityMapUtils.pointInCircle(p.x, p.y, dot)) {
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

          this.tooltip.type = 'dot';
          this.tooltip.data = {
            title: this.translations.locationDetails_,
            name: names.join(', '),
            totalIn: incoming,
            totalOut: outgoing,
          };

          break;
        }
      }

      // Check ARROWS if no dot match
      if (!hovering) {
        for (const arrow of this.arrowShapes) {
          if (MobilityMapUtils.pointOnArrow(p.x, p.y, arrow)) {
            hovering = true;

            const { clusterFrom, clusterTo } = arrow;
            const { total, fromMembers, toMembers } = this.getClusterArrowDetails(
              clusterFrom,
              clusterTo,
            );

            const fromNames = fromMembers.map((id) => this.points[id]?.label || id);
            const toNames = toMembers.map((id) => this.points[id]?.label || id);

            this.tooltip.type = 'arrow';
            this.tooltip.data = {
              title: this.translations.flowDetails_,
              from: fromNames.join(', '),
              to: toNames.join(', '),
              total,
            };

            break;
          }
        }
      }

      // Update cursor
      this.$refs.mapContainer.style.cursor = hovering ? 'pointer' : 'grab';

      // Tooltip handling
      if (hovering) {
        const container = this.$refs.mapContainer;
        const mapRect = container.getBoundingClientRect();

        const tooltipWidth = 220;   // same as your v-card width
        const tooltipHeight = 110;  // approx height of your tooltip
        const padding = 12;

        let x = p.x + padding;
        let y = p.y + padding;

        // Flip horizontally if overflowing right
        if (x + tooltipWidth > mapRect.width) {
          x = p.x - tooltipWidth - padding;
        }

        // Flip vertically if overflowing bottom
        if (y + tooltipHeight > mapRect.height) {
          y = p.y - tooltipHeight - padding;
        }

        // Clamp to left/top just in case
        x = Math.max(padding, x);
        y = Math.max(padding, y);

        this.tooltip.visible = true;
        this.tooltip.x = x;
        this.tooltip.y = y;
      } else {
        this.tooltip.visible = false;
        this.tooltip.data = null;
        this.tooltip.type = null;
      }
    },

    clearFilter() {
      this.selectedPoint = null;
      this.rebuildShapes();
    },
  },

  template: `
    <v-container fluid class="pa-0 fill-height position-relative overflow-hidden">

      <!-- Map -->
      <div ref="mapContainer" class="w-100 h-100 position-relative"></div>

      <!-- Canvas Overlay -->
      <canvas
        ref="overlay"
        class="position-absolute top-0 left-0 w-100 h-100 pointer-events-none"
        style="zIndex: 999;"
      ></canvas>

      <!-- Tooltip -->
      <v-card
        v-if="tooltip.visible && tooltip.data"
        class="position-absolute pa-3"
        style="width: 220px; zIndex: 9999; border-radius: 10px;"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
        elevation="4"
      >

        <!-- Title -->
        <div class="text-subtitle-2 font-weight-bold mb-1">
          {{ tooltip.data.title }}
        </div>

        <v-divider class="mb-2"></v-divider>

        <!-- DOT TOOLTIP -->
        <template v-if="tooltip.type === 'dot'">
          <div class="text-subtitle-2 font-weight-bold">
            {{ translations.name_ }}
          </div>
          <div class="text-body-2 mb-2">
            {{ tooltip.data.name }}
          </div>
          <div class="text-subtitle-2 font-weight-bold">
            {{ translations.totalIn_ }}
          </div>
          <div class="text-body-2 mb-2">
            {{ tooltip.data.totalIn }}
          </div>
          <div class="text-subtitle-2 font-weight-bold">
            {{ translations.totalOut_ }}
          </div>
          <div class="text-body-2 mb-2">
            {{ tooltip.data.totalOut }}
          </div>
        </template>

        <!-- ARROW TOOLTIP -->
        <template v-if="tooltip.type === 'arrow'">
          <div class="text-subtitle-2 font-weight-bold">
            {{ translations.origin_ }}
          </div>
          <div class="text-body-2 mb-2">
            {{ tooltip.data.from }}
          </div>
          <div class="text-subtitle-2 font-weight-bold">
            {{ translations.destination_ }}
          </div>
          <div class="text-body-2 mb-2">
            {{ tooltip.data.to }}
          </div>
          
          <div class="text-subtitle-2 font-weight-bold">
            {{ translations.count_ }}
          </div>
          <div class="text-body-2 mb-2">
            {{ tooltip.data.total }}
          </div>
        </template>
      </v-card>


    </v-container>

  `,
});
