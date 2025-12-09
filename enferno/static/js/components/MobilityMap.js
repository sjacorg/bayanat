const MobilityMap = Vue.defineComponent({
  props: {
    clickToZoomCluster: { type: Boolean, default: false },
    minZoom: { type: Number, default: () => MobilityMapUtils.CONFIG.map.minZoom },
    scrollWheelZoom: { type: Boolean, default: () => MobilityMapUtils.CONFIG.map.scrollWheelZoom },
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
      measureControls: null,
      zooming: false,

      // Morphing state
      morphing: false,
      morphProgress: 1,
      morphFrom: null,
      morphTo: null,

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

      // observe parent resizing
      this.initResizeObserver();

      this.map.once('moveend', () => {
        this.rebuildShapes();
        this.scheduleFrame();
      });
    });
  },

  beforeUnmount() {
    this.morphing = false;
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
        this.selectedPoint = null;
        this.minWeight = null;
        this.maxWeight = null;
        this.initPoints();
        this.rebuildShapes();
      },
    },

    flows: {
      handler() {
        this.selectedPoint = null;
        this.minWeight = null;
        this.maxWeight = null;

        this.rebuildShapes();

        this.$nextTick(() => {
          this.zoomToAll();
        });
      },
    },
  },

  computed: {
    measuringActive() {
      return this.measureControls?._measuring === true;
    }
  },

  methods: {
    initResizeObserver() {
      const el = this.$refs.mapContainer;
      if (!el) return;

      this._resizeObserver = new ResizeObserver(() => {
        if (!this.map) return;

        // Update Leaflet internal size
        this.map.invalidateSize({ animate: false });

        // Resize canvas overlay
        this.resizeCanvas();

        // Redraw overlays
        this.scheduleFrame();
      });

      this._resizeObserver.observe(el);
    },
    /* ================= MAP INIT ================= */

    initMap() {
      const el = this.$refs.mapContainer;
      if (!el) return this.$nextTick(() => this.initMap());

      const worldBounds = L.latLngBounds(
        L.latLng(MobilityMapUtils.CONFIG.map.bounds.south, MobilityMapUtils.CONFIG.map.bounds.west),
        L.latLng(MobilityMapUtils.CONFIG.map.bounds.north, MobilityMapUtils.CONFIG.map.bounds.east),
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
        }),
      );

      const validLocs = this.locations.filter(
        (loc) => Number.isFinite(loc.lat) && Number.isFinite(loc.lon),
      );

      if (validLocs.length) {
        const bounds = L.latLngBounds(validLocs.map((loc) => [loc.lat, loc.lon]));
        this.map.fitBounds(bounds);
      }

      // if (!this.measureControls && L.control.polylineMeasure) {
      //   this.measureControls = L.control.polylineMeasure({
      //     position: 'topleft',
      //     unit: 'kilometres',
      //     fixedLine: {
      //       color: 'rgba(67,157,146,0.77)',
      //       weight: 2,
      //     },
      //     arrow: {
      //       color: 'rgba(67,157,146,0.77)',
      //     },
      //     showBearings: false,
      //     clearMeasurementsOnStop: false,
      //     showClearControl: true,
      //     showUnitControl: true,
      //   });
      //   this.measureControls.addTo(this.map);
      // }

      this.map.on('click', this.onMapClick);
      this.map.on('mousemove', this.onMapHover);

      this.map.on('move', this.scheduleFrame);
      this.map.on('zoom', this.scheduleFrame);
      this.map.on('zoomanim', this.scheduleFrame);

      // Morph instead of hard rebuild
      this.map.on('zoomstart', () => {
        this.zooming = true;
      });
      this.map.on('zoomend', () => {
        if (!this.zooming) return;
        this.zooming = false;

        // Allow canvas to update center points correctly
        requestAnimationFrame(() => {
          this.startMorph();
        });
      });

      window.addEventListener('resize', this.resizeCanvas);
    },

    /* ================= MORPH CORE ================= */
    startMorph() {
      if (this.morphing || !this.clusterDefs.length) return;

      const oldClusters = JSON.parse(JSON.stringify(this.clusterDefs));
      const oldFlows = JSON.parse(JSON.stringify(this.flowGroups));

      // Generate new target
      this.rebuildShapes();
      if (!this.clusterDefs.length) {
        this.morphing = false;
        return;
      }

      const newClusters = JSON.parse(JSON.stringify(this.clusterDefs));
      const newFlows = JSON.parse(JSON.stringify(this.flowGroups));

      const fullTarget = [...newClusters];
      const maxDist = 150;

      oldClusters.forEach((oldC) => {
        const match = MobilityMapUtils.findClosestCluster(oldC, newClusters, (lat, lng) =>
          this.map.latLngToContainerPoint([lat, lng]),
        );
        if (!match.cluster || match.dist > maxDist) {
          fullTarget.push({
            ...oldC,
            radius: 0,
            fadingOut: true,
          });
        }
      });

      this.morphFrom = { clusters: oldClusters, flows: oldFlows };
      this.morphTo = { clusters: fullTarget, flows: newFlows };

      this.morphProgress = 0;
      this.morphing = true;

      this.animateMorph();
    },

    animateMorph() {
      if (!this.morphing) return;

      const speed = 0.1;

      this.morphProgress += speed;

      if (this.morphProgress >= 1) {
        this.morphProgress = 1;
        this.morphing = false;

        this.clusterDefs = this.morphTo.clusters.filter((c) => !c.fadingOut);
        this.flowGroups = this.morphTo.flows;
        this.drawFrame();
        return;
      }

      const interpolated = this.morphTo.clusters.map((target) => {
        const { cluster: oldC } = MobilityMapUtils.findClosestCluster(
          target,
          this.morphFrom.clusters,
          (lat, lng) => this.map.latLngToContainerPoint([lat, lng]),
        );

        if (!oldC) return target;

        return {
          ...target,
          centerLat: MobilityMapUtils.lerp(oldC.centerLat, target.centerLat, this.morphProgress),
          centerLon: MobilityMapUtils.lerp(oldC.centerLon, target.centerLon, this.morphProgress),
          radius: MobilityMapUtils.lerp(oldC.radius, target.radius, this.morphProgress),
        };
      });

      this.clusterDefs = interpolated;
      this.flowGroups = this.morphTo.flows;

      this.drawFrame();
      requestAnimationFrame(this.animateMorph.bind(this));
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

      if (!this.clusterDefs.length) return;

      // Map cluster → screen coords
      const clusterPixels = {};
      this.clusterDefs.forEach((c) => {
        const latlng = L.latLng(c.centerLat, c.centerLon);
        clusterPixels[c.id] = this.map.latLngToContainerPoint(latlng);
      });

      const baseSpacing = MobilityMapUtils.CONFIG.sizes.bidirectionalArrowSpacing;

      // ============================
      // 1️⃣ Merge flows by direction
      // ============================
      const mergedArrows = {};

      Object.values(this.flowGroups).forEach((group) => {
        const fromPx = clusterPixels[group.fromClusterId];
        const toPx = clusterPixels[group.toClusterId];
        if (!fromPx || !toPx) return;

        const key = `${group.fromClusterId}->${group.toClusterId}`;

        if (!mergedArrows[key]) {
          mergedArrows[key] = {
            fromCluster: group.fromClusterId,
            toCluster: group.toClusterId,
            start: { x: fromPx.x, y: fromPx.y },
            end: { x: toPx.x, y: toPx.y },
            rawPairs: [],
            weight: 0,
          };
        }

        group.flows.forEach((f) => {
        // Support both normal and event flow structure
        const fromId = f.fromKey ?? f.from ?? f.origin;
        const toId = f.toKey ?? f.to ?? f.dest;
        const weight = f.weight ?? f.count ?? 1;

        mergedArrows[key].weight += weight;

        mergedArrows[key].rawPairs.push({
          fromId,
          toId,
          weight,
        });
      });
      });

      // ============================
      // 2️⃣ Compute min/max for MERGED arrows
      // ============================
      let arrowMin = Infinity;
      let arrowMax = -Infinity;

      Object.values(mergedArrows).forEach((seg) => {
        if (seg.weight < arrowMin) arrowMin = seg.weight;
        if (seg.weight > arrowMax) arrowMax = seg.weight;
      });

      if (!Number.isFinite(arrowMin) || !Number.isFinite(arrowMax)) {
        arrowMin = arrowMax = 0;
      }

      // ============================
      // 3️⃣ Compute final widths (using merged range)
      // ============================
      Object.values(mergedArrows).forEach((seg) => {
        seg.width = MobilityMapUtils.getArrowWidth(
          seg.weight,
          arrowMin, // ✅ merged min
          arrowMax, // ✅ merged max
          seg.rawPairs,
        );
      });

      // ============================
      // 3️⃣ Apply bidirectional spacing
      // ============================
      Object.values(mergedArrows).forEach((seg) => {
        const oppositeKey = `${seg.toCluster}->${seg.fromCluster}`;
        const opposite = mergedArrows[oppositeKey];

        const A = seg.start;
        const B = seg.end;

        const comp = MobilityMapUtils.CONFIG.sizes.arrowPaddingCompensation;

        const thisHalf = seg.width * comp;
        const oppositeHalf = opposite ? opposite.width * comp : 0;

        const offset = thisHalf + oppositeHalf + baseSpacing;

        const { offsetA1, offsetB1 } = MobilityMapUtils.computeOffsets(A, B, offset);

        seg.from = offsetA1;
        seg.to = offsetB1;
      });

      const finalSegments = Object.values(mergedArrows);

      // ============================
      // 4️⃣ Draw arrows
      // ============================
      finalSegments
        .sort((a, b) => a.width - b.width) // thin first, thick last
        .forEach((seg) => {
          this.drawArrowRect(
            seg.from,
            seg.to,
            seg.width,
            seg.fromCluster,
            seg.toCluster,
            seg.weight,
            arrowMin,
            arrowMax,
            seg.rawPairs,
          );
        });

      // ============================
      // 5️⃣ Draw clusters
      // ============================
      this.clusterDefs.forEach((c) => {
        const p = clusterPixels[c.id];
        if (!p) return;

        // Determine cluster color based on members
        const markerTypes = new Set(
          c.memberIds.map((id) => this.points[id]?.markerType)
        );

        const { fillColor, strokeStyle, strokeWidth, dotSize } = MobilityMapUtils.getClusterVisualStyle(c, markerTypes, this.clickToZoomCluster);

        ctx.beginPath();
        ctx.arc(p.x, p.y, dotSize, 0, Math.PI * 2);
        ctx.fillStyle = fillColor;
        ctx.fill();
        ctx.lineWidth = strokeWidth;
        ctx.strokeStyle = strokeStyle;
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

      this.arrowShapes.sort((a, b) => a.weight - b.weight);
    },

    /* =============================================
     ARROW DRAWING (per arrow, used by drawFrame)
    ============================================= */
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

    /* =============================================
     CLICK HANDLING HELPERS
    ============================================= */

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
      if (this.measuringActive) return;
      if (this.morphing) return;
      const p = this.map.latLngToContainerPoint(e.latlng);

      for (const dot of this.dotShapes) {
        if (MobilityMapUtils.pointInCircle(p.x, p.y, dot)) {
          const cluster = this.clusterDefs[dot.clusterId];
          if (!cluster) return;

          // If cluster has multiple members → zoom in
          if (cluster.memberIds.length > 1 && this.clickToZoomCluster) {
            this.zoomToCluster(cluster.memberIds);
            return;
          }

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
      if (this.measuringActive) return;
      if (!this.map || !this.canvas) return;

      const p = this.map.latLngToContainerPoint(e.latlng);
      let hovering = false;

      // Check DOTS
      for (const dot of this.dotShapes) {
        if (MobilityMapUtils.pointInCircle(p.x, p.y, dot)) {
          hovering = true;

            const cluster = this.clusterDefs[dot.clusterId];

            // 🛑 EVENT MODE: NO TOOLTIP, JUST POINTER FOR CLUSTERS WITH MORE THAN ONE MEMBER
            if (this.mode === 'event' && cluster.memberIds.length > 1) {
                // Set cursor to hand and exit (no tooltip)
                this.$refs.mapContainer.style.cursor = 'pointer';
                this.tooltip.visible = false;
                this.tooltip.data = null;
                this.tooltip.type = null;
                return;
            }

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
              number: loc?.number ?? event?.number ?? null,
              parentId: loc?.parentId ?? event?.parentId ?? null,  // let UI decide to hide, not force "—"

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
              main: Boolean(loc?.main ?? event?.main),
            };
          } else {
            const ids = dot.key.split(',').map(Number);
            const names = ids.map((id) => this.points[id]?.label || id);

            let outgoing = 0;
            let incoming = 0;

            ids.forEach((id) => {
              const cluster = this.clusterDefs[dot.clusterId];
              const traffic = this.getClusterTraffic(cluster);

              outgoing = traffic.outgoing;
              incoming = traffic.incoming;
            });

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

        const padding = 12;

        // Prepare raw coords first
        let x = p.x + padding;
        let y = p.y + padding;

        // Temporarily show tooltip so DOM size renders
        this.tooltip.visible = true;
        this.tooltip.x = x;
        this.tooltip.y = y;

        this.$nextTick(() => {
          const card = this.$refs.tooltipCard;
          if (!card) return;

          const cardRect = card.$el
            ? card.$el.getBoundingClientRect()
            : card.getBoundingClientRect();

          const tooltipWidth = cardRect.width;
          const tooltipHeight = cardRect.height;

          // Now adjust x/y to avoid overflow
          if (x + tooltipWidth > mapRect.width) {
            x = p.x - tooltipWidth - padding;
          }
          if (y + tooltipHeight > mapRect.height) {
            y = p.y - tooltipHeight - padding;
          }

          // Clamp
          x = Math.max(padding, x);
          y = Math.max(padding, y);

          this.tooltip.x = x;
          this.tooltip.y = y;
        });
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

    zoomToCluster(memberIds, { padding = 60, maxZoom = 12 } = {}) {
      if (!this.map) return;

      const pts = memberIds
        .map(id => this.points[id]?.latlng)
        .filter(Boolean);

      if (!pts.length) return;

      // If only one point → center & zoom nicely
      if (pts.length === 1) {
        this.map.setView(pts[0], maxZoom, {
          animate: true,
          duration: 0.6,
        });
        return;
      }

      const bounds = L.latLngBounds(pts);

      this.map.fitBounds(bounds, {
        padding: [padding, padding],
        maxZoom,
        animate: true,
        duration: 0.6,
      });
    },

    zoomToAll({ padding = 60, maxZoom = 12 } = {}) {
      if (!this.map) return;

      const allIds = Object.keys(this.points).map(id => Number(id));
      const uniqueIds = Array.from(new Set(allIds));

      if (!uniqueIds.length) return;

      this.zoomToCluster(uniqueIds, { padding, maxZoom });
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
        :style="{ zIndex: 999, opacity: measuringActive ? 0.5 : 1 }"
      ></canvas>

      <!-- Tooltip -->
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
          <div class="text-subtitle-2 font-weight-bold mb-1">
            {{ tooltip.data.title }}
          </div>

          <v-divider class="mb-2"></v-divider>

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
          <div class="text-subtitle-2 font-weight-bold mb-1">
            {{ tooltip.data.title }}
          </div>

          <v-divider class="mb-2"></v-divider>

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
