const MobilityMap = Vue.defineComponent({
  props: {
    clickToZoomCluster: { type: Boolean, default: false },
    minZoom: { type: Number, default: () => MobilityMapUtils.CONFIG.map.minZoom },
    scrollWheelZoom: { type: Boolean, default: () => MobilityMapUtils.CONFIG.map.scrollWheelZoom },
    locations: { type: Array, required: true },
    flows: { type: Array, required: true },
    viewportPadding: { type: Object, default: () => ({}) },
    disableClustering: { type: Boolean, default: false },
    mode: { type: String, default: () => null },
  },

  data() {
    return {
      canvas: null,
      ctx: null,
      frameRequested: false,
      translations: window.translations,
      measureControls: null,

      points: {},
      selectedPoint: null,

      dotShapes: [],
      arrowShapes: [],

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
      this.initResizeObserver();

      this.map.once('moveend', () => {
        this.rebuildShapes();
        this.scheduleFrame();
      });
    });
  },

  beforeUnmount() {
    window.removeEventListener('resize', this.resizeCanvas);

    if (this._resizeObserver) {
      this._resizeObserver.disconnect();
      this._resizeObserver = null;
    }

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
        this.$nextTick(() => this.zoomToAll());
      },
    },
  },

  computed: {
    measuringActive() {
      return this.measureControls?._measuring === true;
    },
  },

  methods: {
    // =============================================
    // INITIALIZATION
    // =============================================

    initResizeObserver() {
      const el = this.$refs.mapContainer;
      if (!el) return;

      this._resizeObserver = new ResizeObserver(() => {
        if (!this.map) return;
        this.map.invalidateSize({ animate: false });
        this.resizeCanvas();
        this.scheduleFrame();
      });

      this._resizeObserver.observe(el);
    },

    initMap() {
      const el = this.$refs.mapContainer;
      if (!el) return this.$nextTick(() => this.initMap());

      const worldBounds = L.latLngBounds(
        L.latLng(MobilityMapUtils.CONFIG.map.bounds.south, MobilityMapUtils.CONFIG.map.bounds.west),
        L.latLng(MobilityMapUtils.CONFIG.map.bounds.north, MobilityMapUtils.CONFIG.map.bounds.east)
      );

      this.map = L.map(el, {
        minZoom: this.minZoom,
        maxBoundsViscosity: MobilityMapUtils.CONFIG.map.maxBoundsViscosity,
        worldCopyJump: MobilityMapUtils.CONFIG.map.worldCopyJump,
        maxBounds: worldBounds,
        zoomAnimation: false,
        scrollWheelZoom: this.scrollWheelZoom,
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
        })
      );

      const validLocs = this.locations.filter(
        (loc) => Number.isFinite(loc.lat) && Number.isFinite(loc.lon)
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

    initPoints() {
      this.points = {};
      this.locations.forEach((loc) => {
        this.points[loc.id] = {
          latlng: L.latLng(loc.lat, loc.lon),
          label: loc.name ?? loc.full_string,
          markerType: loc.markerType || null,
          main: loc.main ?? false,
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

    // =============================================
    // RENDERING
    // =============================================

    resetSelectionAndRebuild() {
      this.selectedPoint = null;
      this.minWeight = null;
      this.maxWeight = null;
      this.rebuildShapes();
    },

    rebuildShapes() {
      if (!this.map || !this.ctx) return;

      const flows = MobilityMapUtils.filterFlows(this.flows, this.selectedPoint);

      if (this.selectedPoint && flows.length === 0) {
        console.warn('Selection produced no flows, resetting filter');
        this.selectedPoint = null;
        return this.rebuildShapes();
      }

      this.currentFlows = flows;
      this.dotShapes = [];
      this.arrowShapes = [];
      this.clusterDefs = [];
      this.flowGroups = {};

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

      this.drawFrame();
    },

    scheduleFrame() {
      if (this.frameRequested) return;
      this.frameRequested = true;

      requestAnimationFrame(() => {
        this.drawFrame();
        this.frameRequested = false;
      });
    },

    drawFrame() {
      if (!this.ctx || !this.map) return;

      const ctx = this.ctx;
      ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);

      this.arrowShapes = [];
      this.dotShapes = [];

      if (!this.clusterDefs.length) return;

      const clusterPixels = MobilityMapUtils.getClusterPixels(this.clusterDefs, this.map);

      // Draw arrows
      const { segments, arrowMin, arrowMax } = MobilityMapUtils.prepareArrowSegments(
        this.flowGroups,
        clusterPixels
      );

      segments
        .sort((a, b) => a.width - b.width)
        .forEach((seg) => this.drawArrow(seg, arrowMin, arrowMax));

      // Draw clusters
      this.clusterDefs.forEach((c) => {
        const p = clusterPixels[c.id];
        if (!p) return;

        const markerTypes = new Set(c.memberIds.map((id) => this.points[id]?.markerType));
        const { fillColor, strokeStyle, strokeWidth, dotSize } = MobilityMapUtils.getClusterVisualStyle(
          c,
          markerTypes,
          this.clickToZoomCluster
        );

        ctx.beginPath();
        ctx.arc(p.x, p.y, dotSize, 0, Math.PI * 2);
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.lineWidth = strokeWidth;
        ctx.strokeStyle = strokeStyle;
        ctx.stroke();

        // Draw count label for multi-member clusters
        if (c.memberIds.length > 1) {
          const fontSize = Math.max(10, c.radius);
          ctx.font = `${fontSize}px sans-serif`;
          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.lineWidth = 2;
          ctx.strokeStyle = 'rgba(0,0,0,0.85)';
          ctx.strokeText(c.memberIds.length, p.x, p.y);
          ctx.fillStyle = '#fff';
          ctx.fillText(c.memberIds.length, p.x, p.y);
        }

        this.dotShapes.push({
          center: { x: p.x, y: p.y },
          radius: c.radius,
          key: c.memberIds.join(','),
          clusterId: c.id,
        });
      });

      this.arrowShapes.sort((a, b) => a.weight - b.weight);
    },

    drawArrow(seg, minW, maxW) {
      const ctx = this.ctx;
      const { from: p1, to: p2, width, fromCluster, toCluster, weight, rawPairs } = seg;

      const dx = p2.x - p1.x;
      const dy = p2.y - p1.y;
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len === 0) return;

      const angle = Math.atan2(dy, dx);
      const tipW = Math.max(width * 6, 25);
      const bodyLen = Math.max(len - tipW, 0);

      const path = new Path2D();
      path.moveTo(0, -width / 2);
      path.lineTo(bodyLen, -width / 2);
      path.lineTo(bodyLen + tipW, -width / 2);
      path.lineTo(bodyLen - 1, width + 10);
      path.lineTo(bodyLen - 1, width / 2);
      path.lineTo(0, width / 2);
      path.closePath();

      ctx.save();
      ctx.translate(p1.x, p1.y);
      ctx.rotate(angle);

      ctx.lineJoin = 'round';
      ctx.lineCap = 'round';
      ctx.strokeStyle = 'rgba(255,255,255,1)';
      ctx.lineWidth = 2;
      ctx.stroke(path);

      ctx.fillStyle = MobilityMapUtils.getArrowColor(weight, minW, maxW);
      ctx.fill(path);

      ctx.restore();

      this.arrowShapes.push({
        origin: p1,
        angle,
        hitPath: path,
        clusterFrom: fromCluster,
        clusterTo: toCluster,
        rawPairs,
        weight,
      });
    },

    // =============================================
    // INTERACTION
    // =============================================

    onMapClick(e) {
      if (this.measuringActive) return;

      const p = this.map.latLngToContainerPoint(e.latlng);

      // Check dots
      for (const dot of this.dotShapes) {
        if (MobilityMapUtils.pointInCircle(p.x, p.y, dot)) {
          const cluster = this.clusterDefs[dot.clusterId];
          if (!cluster) return;

          // Multi-member cluster: zoom in
          if (cluster.memberIds.length > 1 && this.clickToZoomCluster) {
            this.zoomToCluster(cluster.memberIds);
            return;
          }

          // Event mode: copy coordinates
          if (this.mode === 'event') {
            const { lat, lon } = this.tooltip.data;
            MobilityMapUtils.copyCoordinates({ lat, lon })
              .then(() => this.$root?.showSnack?.(this.translations.copiedToClipboard_))
              .catch(() => this.$root?.showSnack?.(this.translations.failedToCopyCoordinates_));
            return;
          }

          // Select cluster
          this.selectedPoint = {
            type: 'cluster',
            clusterId: dot.clusterId,
            memberIds: [...cluster.memberIds],
          };

          this.rebuildShapes();
          this.$nextTick(() => this.onMapHover(e));
          return;
        }
      }

      // Check arrows
      for (const arrow of this.arrowShapes) {
        if (MobilityMapUtils.pointOnArrow(p.x, p.y, arrow, this.ctx)) {
          return;
        }
      }

      // Nothing hit: clear selection
      if (this.selectedPoint !== null) {
        this.clearFilter();
      }
    },

    onMapHover(e) {
      if (this.measuringActive) return;
      if (!this.map || !this.canvas) return;

      const p = this.map.latLngToContainerPoint(e.latlng);
      let hovering = false;

      // Check dots
      for (const dot of this.dotShapes) {
        if (MobilityMapUtils.pointInCircle(p.x, p.y, dot)) {
          hovering = true;
          const cluster = this.clusterDefs[dot.clusterId];

          // Event mode: no tooltip for multi-member clusters
          if (this.mode === 'event' && cluster.memberIds.length > 1) {
            this.$refs.mapContainer.style.cursor = 'pointer';
            this.tooltip.visible = false;
            this.tooltip.data = null;
            this.tooltip.type = null;
            return;
          }

          if (this.mode === 'event') {
            const locId = Number(dot.key.split(',')[0]);
            const loc = this.locations.find((l) => l.id === locId);
            if (!loc) return;

            const event = loc.events?.[loc.events.length - 1] || {};

            this.tooltip.type = 'event';
            this.tooltip.data = {
              title: loc.title || '',
              number: loc?.number ?? event?.number ?? null,
              parentId: loc?.parentId ?? event?.parentId ?? null,
              lat: Number.isFinite(loc.lat) ? loc.lat : null,
              lon: Number.isFinite(loc.lon) ? loc.lon : null,
              displayName: loc.full_string || '',
              eventType: event?.eventtype?.title || event?.eventType || '',
              fromDate: event?.from_date || null,
              toDate: event?.to_date || null,
              estimated: Boolean(event?.estimated),
              main: Boolean(loc?.main ?? event?.main),
            };
          } else {
            const ids = dot.key.split(',').map(Number);
            const names = ids.map((id) => this.points[id]?.label || id);
            const { outgoing, incoming } = this.getClusterTraffic(cluster);

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

      // Check arrows
      if (!hovering) {
        for (let i = this.arrowShapes.length - 1; i >= 0; i--) {
          const arrow = this.arrowShapes[i];

          if (MobilityMapUtils.pointOnArrow(p.x, p.y, arrow, this.ctx)) {
            hovering = true;
            const pairs = arrow.rawPairs || [];

            if (pairs.length === 1) {
              this.tooltip.type = 'arrow';
              this.tooltip.data = {
                title: this.translations.flowDetails_,
                from: this.points[pairs[0].fromId]?.label,
                to: this.points[pairs[0].toId]?.label,
                total: pairs[0].weight,
                mode: 'direct',
              };
            } else {
              const fromNames = [...new Set(pairs.map((p) => this.points[p.fromId]?.label))];
              const toNames = [...new Set(pairs.map((p) => this.points[p.toId]?.label))];

              this.tooltip.type = 'arrow';
              this.tooltip.data = {
                title: this.translations.flowDetails_,
                from: MobilityMapUtils.tooltipCityNames(fromNames),
                to: MobilityMapUtils.tooltipCityNames(toNames),
                total: pairs.reduce((sum, p) => sum + p.weight, 0),
                mode: 'clustered',
              };
            }

            break;
          }
        }
      }

      this.$refs.mapContainer.style.cursor = hovering ? 'pointer' : 'grab';

      if (hovering) {
        this.positionTooltip(p);
      } else {
        this.tooltip.visible = false;
        this.tooltip.data = null;
        this.tooltip.type = null;
      }
    },

    positionTooltip(p) {
      const container = this.$refs.mapContainer;
      const mapRect = container.getBoundingClientRect();
      const padding = 12;

      let x = p.x + padding;
      let y = p.y + padding;

      this.tooltip.visible = true;
      this.tooltip.x = x;
      this.tooltip.y = y;

      this.$nextTick(() => {
        const card = this.$refs.tooltipCard;
        if (!card) return;

        const cardRect = card.$el ? card.$el.getBoundingClientRect() : card.getBoundingClientRect();

        if (x + cardRect.width > mapRect.width) x = p.x - cardRect.width - padding;
        if (y + cardRect.height > mapRect.height) y = p.y - cardRect.height - padding;

        this.tooltip.x = Math.max(padding, x);
        this.tooltip.y = Math.max(padding, y);
      });
    },

    getClusterTraffic(targetCluster) {
      let outgoing = 0;
      let incoming = 0;

      const targetMembers = new Set(targetCluster.memberIds);
      const noSelection = !this.selectedPoint;
      const isSelectedCluster =
        this.selectedPoint?.type === 'cluster' &&
        this.selectedPoint.memberIds.some((id) => targetMembers.has(id));

      if (noSelection || isSelectedCluster) {
        this.currentFlows.forEach((f) => {
          if (targetMembers.has(f.from)) outgoing += f.weight;
          if (targetMembers.has(f.to)) incoming += f.weight;
        });
        return { outgoing, incoming };
      }

      if (this.selectedPoint.type === 'cluster') {
        const selectedMembers = new Set(this.selectedPoint.memberIds);

        this.currentFlows.forEach((f) => {
          if (selectedMembers.has(f.from) && targetMembers.has(f.to)) incoming += f.weight;
          if (targetMembers.has(f.from) && selectedMembers.has(f.to)) outgoing += f.weight;
        });

        return { outgoing, incoming };
      }

      return { outgoing: 0, incoming: 0 };
    },

    clearFilter() {
      this.selectedPoint = null;
      this.rebuildShapes();
    },

    // =============================================
    // ZOOMING
    // =============================================

    zoomToCluster(memberIds, { padding = 60, maxZoom = 12 } = {}) {
      if (!this.map) return;

      const pts = memberIds.map((id) => this.points[id]?.latlng).filter(Boolean);
      if (!pts.length) return;

      if (pts.length === 1) {
        this.map.setView(pts[0], maxZoom, { animate: true, duration: 0.6 });
        return;
      }

      this.map.fitBounds(L.latLngBounds(pts), {
        padding: [padding, padding],
        maxZoom,
        animate: true,
        duration: 0.6,
      });
    },

    zoomToAll({ padding = 60, maxZoom = 12 } = {}) {
      if (!this.map) return;

      const allIds = Object.keys(this.points).map(Number);
      if (!allIds.length) return;

      this.zoomToCluster(allIds, { padding, maxZoom });
    },
  },

  template: `
    <v-container fluid class="pa-0 fill-height position-relative overflow-hidden">
      <div ref="mapContainer" class="w-100 h-100 position-relative"></div>

      <canvas
        ref="overlay"
        class="position-absolute top-0 left-0 w-100 h-100 pointer-events-none"
        :style="{ zIndex: 999, opacity: measuringActive ? 0.5 : 1 }"
      ></canvas>

      <v-card
        v-if="tooltip.visible && tooltip.data"
        ref="tooltipCard"
        class="position-absolute pa-3"
        style="zIndex: 9999; border-radius: 10px;"
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

            <h4>{{ tooltip.data.title || '' }}</h4>

            <div class="d-flex align-center">
              <v-icon size="18" class="mr-1">mdi-map-marker-outline</v-icon>
              {{ tooltip.data.displayName || '' }}
            </div>

            <div v-if="tooltip.data.main">{{ translations.mainIncident_ }}</div>

            <div v-if="tooltip.data.fromDate || tooltip.data.toDate" class="d-flex align-center">
              <v-icon
                size="16"
                class="mr-1"
                :title="tooltip.data.estimated ? translations.timingForThisEventIsEstimated_ : ''"
              >
                {{ tooltip.data.estimated ? 'mdi-calendar-question' : 'mdi-calendar-clock' }}
              </v-icon>

              <span v-if="tooltip.data.fromDate" class="chip mr-1">
                {{ $root.formatDate(tooltip.data.fromDate, tooltip.data.fromDate.includes('T00:00') ? $root.dateFormats.standardDate : $root.dateFormats.standardDatetime) }}
              </span>

              <v-icon v-if="tooltip.data.fromDate && tooltip.data.toDate" size="14" class="mr-1">
                mdi-arrow-right
              </v-icon>

              <span v-if="tooltip.data.toDate" class="chip">
                {{ $root.formatDate(tooltip.data.toDate, tooltip.data.toDate.includes('T00:00') ? $root.dateFormats.standardDate : $root.dateFormats.standardDatetime) }}
              </span>
            </div>
          </div>
        </template>

        <!-- DOT TOOLTIP -->
        <template v-if="tooltip.type === 'dot'">
          <div class="text-caption font-weight-bold mb-1">{{ tooltip.data.title }}</div>
          <v-divider class="mb-1"></v-divider>
          <div class="text-caption font-weight-bold">{{ translations.name_ }}</div>
          <div class="text-caption mb-1">{{ tooltip.data.name }}</div>
          <div class="text-caption font-weight-bold">{{ translations.totalIn_ }}</div>
          <div class="text-caption mb-1">{{ tooltip.data.totalIn }}</div>
          <div class="text-caption font-weight-bold">{{ translations.totalOut_ }}</div>
          <div class="text-caption">{{ tooltip.data.totalOut }}</div>
        </template>

        <!-- ARROW TOOLTIP -->
        <template v-if="tooltip.type === 'arrow'">
          <div class="text-caption font-weight-bold mb-1">{{ tooltip.data.title }}</div>
          <v-divider class="mb-1"></v-divider>
          <div class="text-caption font-weight-bold">{{ translations.origin_ }}</div>
          <div class="text-caption mb-1">{{ tooltip.data.from }}</div>
          <div class="text-caption font-weight-bold">{{ translations.destination_ }}</div>
          <div class="text-caption mb-1">{{ tooltip.data.to }}</div>
          <div class="text-caption font-weight-bold">{{ translations.count_ }}</div>
          <div class="text-caption">{{ tooltip.data.total }}</div>
        </template>
      </v-card>
    </v-container>
  `,
});