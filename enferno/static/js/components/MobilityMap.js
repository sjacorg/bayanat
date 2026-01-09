const MobilityMap = Vue.defineComponent({
  props: {
    locations: { type: Array, required: true },
    flows: { type: Array, required: true },
    viewportPadding: {
      type: Object,
      default: () => ({}),
    },
    disableClustering: { type: Boolean, default: false },
    mode: { type: String, default: () => null }
  },
  data() {
    return {
      canvas: null,
      ctx: null,
      frameRequested: false,
      translations: window.translations,

      // Location id -> { latlng, label }
      points: {},

      selectedPoint: null,

      // Hit-test shapes
      dotShapes: [],
      arrowShapes: [],

      // Precomputed
      clusterDefs: [],
      flowGroups: {},
      currentFlows: [],

      minWeight: null,
      maxWeight: null,

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
    this.map = null;

    this.$nextTick(() => {
      this.initMap();
      this.initPoints();
      this.initCanvas();

      this.map.once('moveend', () => {
        this.rebuildShapes();
        this.scheduleFrame();
      });
    });
  },
  beforeUnmount() {
    window.removeEventListener('resize', this.resizeCanvas);
    if (this.map) {
      this.map.off();
      this.map.remove();
      this.map = null;
    }
  },
  watch: {
    locations: {
      handler() {
        this.resetSelectionAndRebuild();
        this.initPoints();
      },
    },

    flows: {
      handler() {
        this.resetSelectionAndRebuild();
        this.$nextTick(() => this.zoomToFlows());
      },
    },
  },
  methods: {
    resetSelectionAndRebuild() {
      this.selectedPoint = null;
      this.minWeight = null;
      this.maxWeight = null;
      this.rebuildShapes();
    },
    initMap() {
      const el = this.$refs.mapContainer;
      if (!el) return this.$nextTick(() => this.initMap());

      const worldBounds = L.latLngBounds(
        L.latLng(MobilityMapUtils.CONFIG.map.bounds.south, MobilityMapUtils.CONFIG.map.bounds.west),
        L.latLng(MobilityMapUtils.CONFIG.map.bounds.north, MobilityMapUtils.CONFIG.map.bounds.east),
      );

      this.map = L.map(el, {
        minZoom: MobilityMapUtils.CONFIG.map.minZoom,
        maxBoundsViscosity: MobilityMapUtils.CONFIG.map.maxBoundsViscosity,
        worldCopyJump: MobilityMapUtils.CONFIG.map.worldCopyJump,
        maxBounds: worldBounds,
        zoomAnimation: false,
      }).setView(geoMapDefaultCenter, MobilityMapUtils.CONFIG.map.defaultZoom);

      const osmLayer = L.tileLayer(MobilityMapUtils.CONFIG.map.osm.url, {
        attribution: MobilityMapUtils.CONFIG.map.osm.attribution,
      }).addTo(this.map);

      if (window.__GOOGLE_MAPS_API_KEY__) {
        const googleLayer = L.tileLayer(MobilityMapUtils.CONFIG.map.google.url, {
          attribution: MobilityMapUtils.CONFIG.map.google.attribution,
          maxZoom: MobilityMapUtils.CONFIG.map.google.maxZoom,
          subdomains: MobilityMapUtils.CONFIG.map.google.subdomains,
        });
        L.control
          .layers({ OpenStreetMap: osmLayer, 'Google Satellite': googleLayer })
          .addTo(this.map);
      }

      this.map.addControl(
        new L.Control.Fullscreen({
          title: {
            false: this.translations.enterFullscreen_,
            true: this.translations.exitFullscreen_,
          },
        }),
      );

      const validLocs = this.locations.filter(
        (loc) => Number.isFinite(loc.lat) && Number.isFinite(loc.lon),
      );

      if (validLocs.length) {
        const bounds = L.latLngBounds(validLocs.map((loc) => [loc.lat, loc.lon]));
        this.map.fitBounds(bounds);
      }

      this.map.on('click', this.onMapClick);
      this.map.on('mousemove', this.onMapHover);

      this.map.on('move', this.scheduleFrame);
      this.map.on('zoom', this.scheduleFrame);
      this.map.on('zoomanim', this.scheduleFrame);

      this.map.on('zoomend', () => requestAnimationFrame(() => this.rebuildShapes()));

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
          label: loc.name ?? loc.full_string,
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

      this.ctx.setTransform(1, 0, 0, 1, 0, 0);

      const { clientWidth, clientHeight } = this.$refs.mapContainer;
      const dpr = window.devicePixelRatio || 1;

      this.canvas.width = clientWidth * dpr;
      this.canvas.height = clientHeight * dpr;
      this.canvas.style.width = clientWidth + 'px';
      this.canvas.style.height = clientHeight + 'px';

      this.ctx.scale(dpr, dpr);

      this.rebuildShapes();
    },

    /* =============================================
     HEAVY REBUILD (CLUSTERS & GROUPS)
     Runs when: flows change, locations change, zoom, selection change
    ============================================= */
    rebuildShapes() {
      if (!this.map || !this.ctx) return;

      const flows = MobilityMapUtils.filterFlows(this.flows, this.selectedPoint);
      if (this.selectedPoint && flows.length === 0) {
        console.warn('Selection produced no flows, resetting filter');
        this.selectedPoint = null;

        return this.rebuildShapes(); // retry with no filter
      }

      this.currentFlows = flows;

      this.dotShapes = [];
      this.arrowShapes = [];
      this.clusterDefs = [];
      this.flowGroups = {};

      if (!flows.length) {
        this.drawFrame();
        return;
      }

      const result = MobilityMapUtils.buildClusters({
        points: this.points,
        flows,
        map: this.map,
        minWeight: this.minWeight,
        maxWeight: this.maxWeight,
        disableClustering: this.disableClustering,
      });

      this.clusterDefs = result.clusters;
      this.flowGroups = result.flowGroups;
      this.minWeight = result.minWeight;
      this.maxWeight = result.maxWeight;

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

      // Map cluster → screen coords
      const clusterPixels = this.getClusterPixels();

      // Merge flows by direction
      const mergedArrows = this.mergeArrows(clusterPixels);

      // Compute min/max for MERGED arrows
      const weights = Object.values(mergedArrows).map(s => s.weight);
      const arrowMin = weights.length ? Math.min(...weights) : 0;
      const arrowMax = weights.length ? Math.max(...weights) : 0;

      // Compute final widths (using merged range)
      Object.values(mergedArrows).forEach((seg) => {
        seg.width = MobilityMapUtils.getArrowWidth(
          seg.weight,
          arrowMin, // ✅ merged min
          arrowMax, // ✅ merged max
          seg.rawPairs,
        );
      });

      this.applyBidirectionalSpacing(mergedArrows);
      this.drawArrows(Object.values(mergedArrows), arrowMin, arrowMax);
      this.drawClusters(ctx, clusterPixels);

      this.arrowShapes.sort((a, b) => a.weight - b.weight);
    },

    /* ARROW DRAWING (per arrow, used by drawFrame) */
    drawArrowRect(p1, p2, width, clusterFrom, clusterTo, weight, minW, maxW, rawPairs = []) {
      const ctx = this.ctx;

      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len === 0) return;

      const angle = Math.atan2(dy, dx);

      const tipW = Math.max(width * 6, 25);
      const bodyLen = Math.max(len - tipW, 0);
      const overlap = 1;

      // ✅ Build arrow as a Path2D
      const path = new Path2D();

      path.moveTo(0, -width / 2);
      path.lineTo(bodyLen, -width / 2);
      path.lineTo(bodyLen + tipW, -width / 2);
      path.lineTo(bodyLen - overlap, width + 10);
      path.lineTo(bodyLen - overlap, width / 2);
      path.lineTo(0, width / 2);
      path.closePath();

      ctx.save();
      ctx.translate(p1.x, p1.y);
      ctx.rotate(angle);

      // Stroke first
      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.strokeStyle = 'rgba(255,255,255,1)';
      ctx.lineWidth = 2;
      ctx.stroke(path);

      // Fill
      ctx.fillStyle = MobilityMapUtils.getArrowColor(weight, minW, maxW);
      ctx.fill(path);

      ctx.restore();

      // ✅ Store actual shape for hit-testing
      this.arrowShapes.push({
        origin: p1,
        angle,
        hitPath: path,
        clusterFrom,
        clusterTo,
        rawPairs,
        weight,
      });
    },

    getClusterPixels() {
      const pixels = {};
      this.clusterDefs.forEach(c => {
        pixels[c.id] = this.map.latLngToContainerPoint(
          L.latLng(c.centerLat, c.centerLon)
        );
      });
      return pixels;
    },

    mergeArrows(clusterPixels) {
      const merged = {};
      Object.values(this.flowGroups).forEach(group => {
        const fromPx = clusterPixels[group.fromClusterId];
        const toPx = clusterPixels[group.toClusterId];
        if (!fromPx || !toPx) return;

        const key = `${group.fromClusterId}->${group.toClusterId}`;

        const entry = merged[key] ??= {
          fromCluster: group.fromClusterId,
          toCluster: group.toClusterId,
          start: fromPx,
          end: toPx,
          rawPairs: [],
          weight: 0,
        };

        group.flows.forEach(f => {
          const fromId = f.fromKey ?? f.from ?? f.origin;
          const toId = f.toKey ?? f.to ?? f.dest;
          const weight = f.weight ?? f.count ?? 1;

          entry.weight += weight;
          entry.rawPairs.push({ fromId, toId, weight });
        });
      });

      return merged;
    },

    drawArrows(segments, min, max) {
      segments
        .sort((a, b) => a.width - b.width)
        .forEach(seg => this.drawArrowRect(
          seg.from,
          seg.to,
          seg.width,
          seg.fromCluster,
          seg.toCluster,
          seg.weight,
          min,
          max,
          seg.rawPairs,
        ));
    },

    drawClusters(ctx, clusterPixels) {
      this.clusterDefs.forEach((c) => {
        const p = clusterPixels[c.id];
        if (!p) return;

        ctx.beginPath();
        ctx.arc(p.x, p.y, c.radius, 0, Math.PI * 2);
        ctx.fillStyle = MobilityMapUtils.CONFIG.colors.dot.fill;
        ctx.fill();
        ctx.lineWidth = 2;
        ctx.strokeStyle = MobilityMapUtils.CONFIG.colors.dot.stroke;
        ctx.stroke();

        // 🟡 Draw label if cluster has more than 1 location
        if (c.memberIds.length > 1) {
          const label = c.memberIds.length;
          const fontSize = Math.max(10, c.radius);

          ctx.font = `${fontSize}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';

          // Stroke first (for sharp edge)
          ctx.lineWidth = 2;
          ctx.strokeStyle = 'rgba(0,0,0,0.85)';
          ctx.strokeText(label, p.x, p.y);

          // Fill on top
          ctx.fillStyle = '#fff';
          ctx.fillText(label, p.x, p.y);
        }

        this.dotShapes.push({
          center: { x: p.x, y: p.y },
          radius: c.radius,
          key: c.memberIds.join(','),
          clusterId: c.id,
        });
      });
    },

    applyBidirectionalSpacing(mergedArrows) {
      const baseSpacing = MobilityMapUtils.CONFIG.sizes.bidirectionalArrowSpacing;
      const comp = MobilityMapUtils.CONFIG.sizes.arrowPaddingCompensation;

      Object.values(mergedArrows).forEach(seg => {
        const opposite = mergedArrows[`${seg.toCluster}->${seg.fromCluster}`];

        const thisHalf = seg.width * comp;
        const oppositeHalf = opposite ? opposite.width * comp : 0;
        const offset = thisHalf + oppositeHalf + baseSpacing;

        const { offsetA1, offsetB1 } =
          MobilityMapUtils.computeOffsets(seg.start, seg.end, offset);

        seg.from = offsetA1;
        seg.to = offsetB1;
      });
    },

    /* CLICK HANDLING HELPERS */
    getClusterTraffic(targetCluster) {
      let outgoing = 0;
      let incoming = 0;

      const targetMembers = new Set(targetCluster.memberIds);
      const noSelection = !this.selectedPoint;
      const isSelectedCluster =
        this.selectedPoint?.type === "cluster" &&
        this.selectedPoint.memberIds.some(id => targetMembers.has(id));

       // No selection OR hovering the selected cluster → show full totals
      if (noSelection || isSelectedCluster) {
        this.currentFlows.forEach((f) => {
          if (targetMembers.has(f.from)) outgoing += f.weight;
          if (targetMembers.has(f.to))   incoming += f.weight;
        });

        return { outgoing, incoming };
      }

      // Directional logic for other clusters
      if (this.selectedPoint.type === 'cluster') {
        const selectedMembers = new Set(this.selectedPoint.memberIds);

        this.currentFlows.forEach((f) => {
          const fromInSelected = selectedMembers.has(f.from);
          const toInSelected = selectedMembers.has(f.to);

          const fromInTarget = targetMembers.has(f.from);
          const toInTarget = targetMembers.has(f.to);

          // Flow from selected → target
          if (fromInSelected && toInTarget) incoming += f.weight;

          // Flow from target → selected
          if (fromInTarget && toInSelected) outgoing += f.weight;
        });

        return { outgoing, incoming };
      }

      return { outgoing: 0, incoming: 0 };
    },

    /* CLICK HANDLING */
    onMapClick(e) {
      const p = this.map.latLngToContainerPoint(e.latlng);

      for (const dot of this.dotShapes) {
        if (MobilityMapUtils.pointInCircle(p.x, p.y, dot)) {
          const cluster = this.clusterDefs[dot.clusterId];
          if (!cluster) return;

          if (this.mode === 'event') {
            const { lat, lon } = this.tooltip.data;
            MobilityMapUtils.copyCoordinates({ lat, lon })
              .then(() => this.$root?.showSnack?.(this.translations.copiedToClipboard_))
              .catch(() => this.$root?.showSnack?.(this.translations.failedToCopyCoordinates_));;
            return;
          }

          // NEW: select cluster instead of random member
          this.selectedPoint = {
            type: 'cluster',
            clusterId: dot.clusterId,
            memberIds: [...cluster.memberIds],
          };

          this.rebuildShapes();

          // Force tooltip refresh at current cursor (click doesn't trigger hover)
          this.$nextTick(() => {
            this.onMapHover(e);
          });
          return;
        }
      }

      // 2️⃣ Arrow clicks
      for (const arrow of this.arrowShapes) {
        if (MobilityMapUtils.pointOnArrow(p.x, p.y, arrow, this.ctx)) {
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

          if (this.mode === 'event') {
            const locationIds = dot.key.split(',').map(Number);
            const locId = locationIds[0];

            const loc = this.locations.find(l => l.id === locId);
            if (!loc) return;

            const event = loc.events?.[loc.events.length - 1] || {};

            this.tooltip.type = 'event';
            this.tooltip.data = {
              // Title / Identity
              title: loc.title || '',
              number: event?.number ?? null,
              parentId: event?.parentId ?? null,  // let UI decide to hide, not force "—"

              // Coordinates (keep naming consistent)
              lat: Number.isFinite(loc.lat) ? loc.lat : null,
              lon: Number.isFinite(loc.lon) ? loc.lon : null,

              // Location display
              displayName: loc.full_string || '',

              // Event type label
              eventType: event?.eventtype?.title || event?.eventType || '',

              // Dates
              fromDate: event?.from_date || null,
              toDate: event?.to_date || null,

              // Flags
              estimated: Boolean(event?.estimated),
              main: Boolean(event?.main),
            };
          } else {
            const ids = dot.key.split(',').map(Number);
            const names = ids.map((id) => this.points[id]?.label || id);

            const { outgoing, incoming } = this.getClusterTraffic(this.clusterDefs[dot.clusterId]);

            this.tooltip.type = 'dot';
            this.tooltip.data = {
              title: this.translations.locationDetails_,
              name: MobilityMapUtils.tooltipCityNames(names),
              totalIn: incoming,
              totalOut: outgoing,
            };
          }

          break;
        }
      }

      // Check ARROWS if no dot match
      if (!hovering) {
        // ✅ Check thick arrows first
        for (let i = this.arrowShapes.length - 1; i >= 0; i--) {
          const arrow = this.arrowShapes[i];

          if (MobilityMapUtils.pointOnArrow(p.x, p.y, arrow, this.ctx)) {
            hovering = true;

            const pairs = arrow.rawPairs || [];

            if (pairs.length === 1) {
              const pair = pairs[0];
              this.tooltip.type = 'arrow';
              this.tooltip.data = {
                title: this.translations.flowDetails_,
                from: this.points[pair.fromId]?.label,
                to: this.points[pair.toId]?.label,
                total: pair.weight,
                mode: 'direct',
              };
            } else {
              const fromNames = [...new Set(pairs.map((p) => this.points[p.fromId]?.label))];
              const toNames = [...new Set(pairs.map((p) => this.points[p.toId]?.label))];
              const total = pairs.reduce((sum, p) => sum + p.weight, 0);

              this.tooltip.type = 'arrow';
              this.tooltip.data = {
                title: this.translations.flowDetails_,
                from: MobilityMapUtils.tooltipCityNames(fromNames),
                to: MobilityMapUtils.tooltipCityNames(toNames),
                total,
                mode: 'clustered',
              };
            }

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

        const tooltipWidth = 320; // same as your v-card width
        const tooltipHeight = 110; // approx height of your tooltip
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

    zoomToFlows({ padding = 40, maxZoom = 12 } = {}) {
      if (!this.map || !this.currentFlows?.length) return;

      const points = [];

      this.currentFlows.forEach((flow) => {
        const from = this.points[flow.from]?.latlng;
        const to = this.points[flow.to]?.latlng;

        if (from) points.push(from);
        if (to) points.push(to);
      });

      if (!points.length) return;

      const bounds = L.latLngBounds(points);
      if (!bounds.isValid()) return;

      // ✅ Normalize missing keys safely
      const { top = 0, right = 0, bottom = 0, left = 0 } = this.viewportPadding || {};

      this.map.fitBounds(bounds, {
        paddingTopLeft: [left + padding, top + padding],
        paddingBottomRight: [right + padding, bottom + padding],
        maxZoom,
        animate: true,
        duration: 0.6,
      });
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
        style="width: 320px; zIndex: 9999; border-radius: 10px;"
        :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px' }"
        elevation="4"
      >
        <!-- EVENT TOOLTIP -->
        <template v-if="tooltip.type === 'event'">
          <div class="d-flex flex-column ga-1 text-caption">
            <div class="d-flex ga-2 align-center">
              <div v-if="tooltip.data.number" class="d-flex align-center">
                #{{ tooltip.data.number }}
              </div>
              <div v-if="tooltip.data.parentId && tooltip.data.parentId !== '—'" class="d-flex align-center">
                <v-icon size="16" class="mr-1">mdi-link</v-icon>
                {{ tooltip.data.parentId }}
              </div>
              <div v-if="tooltip.data.eventType" class="d-flex align-center">
                <v-icon size="16" class="mr-1">mdi-calendar-range</v-icon>
                {{ tooltip.data.eventType }}
              </div>
            </div>

            <h4>
              {{ tooltip.data.title || '' }}
            </h4>

            <div class="d-flex align-center">
              <v-icon size="18" class="mr-1">mdi-map-marker-outline</v-icon>

              {{ tooltip.data.displayName || '' }}
            </div>

            <div v-if="tooltip.data.main">
              {{ translations.mainIncident_ }}
            </div>
            
            <div v-if="tooltip.data.fromDate || tooltip.data.toDate" class="d-flex align-center">
              <v-icon
                size="16"
                class="mr-1"
                :title="tooltip.data.estimated 
                  ? translations.timingForThisEventIsEstimated_ 
                  : ''"
              >
                {{ tooltip.data.estimated ? 'mdi-calendar-question' : 'mdi-calendar-clock' }}
              </v-icon>

              <span v-if="tooltip.data.fromDate" class="chip mr-1">
                {{ $root.formatDate(tooltip.data.fromDate, tooltip.data.fromDate.includes('T00:00') ? this.$root.dateFormats.standardDate : this.$root.dateFormats.standardDatetime) }}
              </span>

              <v-icon v-if="tooltip.data.fromDate && tooltip.data.toDate" size="14" class="mr-1">
                mdi-arrow-right
              </v-icon>

              <span v-if="tooltip.data.toDate" class="chip">
                {{ $root.formatDate(tooltip.data.toDate, tooltip.data.toDate.includes('T00:00') ? this.$root.dateFormats.standardDate : this.$root.dateFormats.standardDatetime) }}
              </span>
            </div>

          </div>
        </template>

        <!-- DOT TOOLTIP -->
        <template v-if="tooltip.type === 'dot'">
          <div class="text-caption font-weight-bold mb-1">
            {{ tooltip.data.title }}
          </div>

          <v-divider class="mb-1"></v-divider>

          <div class="text-caption font-weight-bold">
            {{ translations.name_ }}
          </div>
          <div class="text-caption mb-1">
            {{ tooltip.data.name }}
          </div>
          <div class="text-caption font-weight-bold">
            {{ translations.totalIn_ }}
          </div>
          <div class="text-caption mb-1">
            {{ tooltip.data.totalIn }}
          </div>
          <div class="text-caption font-weight-bold">
            {{ translations.totalOut_ }}
          </div>
          <div class="text-caption">
            {{ tooltip.data.totalOut }}
          </div>
        </template>

        <!-- ARROW TOOLTIP -->
        <template v-if="tooltip.type === 'arrow'">
          <div class="text-caption font-weight-bold mb-1">
            {{ tooltip.data.title }}
          </div>

          <v-divider class="mb-1"></v-divider>

          <div class="text-caption font-weight-bold">
            {{ translations.origin_ }}
          </div>
          <div class="text-caption mb-1">
            {{ tooltip.data.from }}
          </div>
          <div class="text-caption font-weight-bold">
            {{ translations.destination_ }}
          </div>
          <div class="text-caption mb-1">
            {{ tooltip.data.to }}
          </div>
          
          <div class="text-caption font-weight-bold">
            {{ translations.count_ }}
          </div>
          <div class="text-caption">
            {{ tooltip.data.total }}
          </div>
        </template>
      </v-card>
    </v-container>
  `,
});
