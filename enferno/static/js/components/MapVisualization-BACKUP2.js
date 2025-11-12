const MapVisualization = Vue.defineComponent({
  props: {
    open: Boolean,
    visualizeEndpoint: { type: String, default: '/admin/api/flowmap/visualize' },
    statusEndpoint: { type: String, default: '/admin/api/flowmap/status' },
    dataEndpoint: { type: String, default: '/admin/api/flowmap/data' },
    query: { type: Array, default: () => [{}] },
  },
  emits: ['update:open', 'advancedSearch'],
  data() {
    return {
      translations: window.translations,
      mapId: 'map-' + this.$.uid,
      map: null,
      canvas: null,
      ctx: null,
      points: {},
      selectedPoint: null,
      hoveredArrow: null,
      dotShapes: [],
      arrowShapes: [],
      debug: {
        selected: 'none',
        entities: 0,
        segments: 0,
        arrows: 0,
      },
      arrowWidths: [2, 5, 7, 12],
      dotSizes: [4, 6, 8, 10, 12, 14],
      data: {
        locations: [
          { id: '1000', name: 'New York', lat: 40.7128, lon: -74.006 },
          { id: '1001', name: 'Los Angeles', lat: 34.0522, lon: -118.2437 },
          { id: '1002', name: 'Chicago', lat: 41.8781, lon: -87.6298 },
          { id: '1003', name: 'Houston', lat: 29.7604, lon: -95.3698 },
          { id: '1004', name: 'Phoenix', lat: 33.4484, lon: -112.074 },
          { id: '1005', name: 'Philadelphia', lat: 39.9526, lon: -75.1652 },
          { id: '1006', name: 'San Antonio', lat: 29.4241, lon: -98.4936 },
          { id: '1007', name: 'San Diego', lat: 32.7157, lon: -117.1611 },
          { id: '1008', name: 'Dallas', lat: 32.7767, lon: -96.797 },
          { id: '1009', name: 'San Jose', lat: 37.3382, lon: -121.8863 },
        ],
        entities: [
          { id: 'e1', path: ['1000', '1001'], weight: 5 },
          { id: 'e2', path: ['1001', '1000'], weight: 3 },
          { id: 'e3', path: ['1000', '1002'], weight: 4 },
          { id: 'e4', path: ['1002', '1000'], weight: 2 },
          { id: 'e5', path: ['1001', '1003'], weight: 6 },
          { id: 'e6', path: ['1003', '1001'], weight: 4 },
          { id: 'e7', path: ['1002', '1003'], weight: 2 },
          { id: 'e8', path: ['1003', '1002'], weight: 3 },
          { id: 'e9', path: ['1004', '1005'], weight: 1 },
          { id: 'e10', path: ['1005', '1004'], weight: 2 },
          { id: 'e11', path: ['1006', '1007'], weight: 4 },
          { id: 'e12', path: ['1007', '1006'], weight: 3 },
          { id: 'e13', path: ['1008', '1009'], weight: 5 },
          { id: 'e14', path: ['1009', '1008'], weight: 2 },
          { id: 'e15', path: ['1000', '1005', '1008'], weight: 2 },
          { id: 'e16', path: ['1008', '1005', '1000'], weight: 3 },
          { id: 'e17', path: ['1001', '1004', '1007'], weight: 4 },
          { id: 'e18', path: ['1007', '1004', '1001'], weight: 2 },
          { id: 'e19', path: ['1002', '1006', '1009'], weight: 3 },
          { id: 'e20', path: ['1009', '1006', '1002'], weight: 1 },
        ],
      },
    };
  },
  mounted() {},
  methods: {
    initMap() {
      this.map = L.map(this.mapId).setView([45.52, -73.57], 12);
      L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; OpenStreetMap contributors',
      }).addTo(this.map);

      const bounds = L.latLngBounds(this.data.locations.map((loc) => [loc.lat, loc.lon]));
      this.map.fitBounds(bounds);

      this.map.on('click', this.onMapClick);
      this.map.on('zoomanim', this.drawFlows);
      this.map.on('zoom move resize', this.drawFlows);
      window.addEventListener('resize', this.resizeCanvas);
    },
    initPoints() {
      this.data.locations.forEach(
        (loc) =>
          (this.points[loc.id] = {
            latlng: L.latLng(loc.lat, loc.lon),
            label: loc.name,
          }),
      );
    },
    initCanvas() {
      this.canvas = this.$refs.overlay;
      this.ctx = this.canvas.getContext('2d');
      this.resizeCanvas();
    },
    resizeCanvas() {
      this.canvas.width = window.innerWidth;
      this.canvas.height = window.innerHeight;
      this.drawFlows();
    },
    clearFilter() {
      this.selectedPoint = null;
      this.drawFlows();
    },
    getFilteredFlows() {
      return this.data.entities.flatMap((entity) => {
        if (this.selectedPoint && !entity.path.some((id) => this.selectedPoint.includes(id)))
          return [];
        const flows = [];
        for (let i = 0; i < entity.path.length - 1; i++) {
          flows.push({ from: entity.path[i], to: entity.path[i + 1], weight: entity.weight });
        }
        return flows;
      });
    },
    getArrowWidth(weight) {
      const allFlows = this.getFilteredFlows();
      const weights = allFlows.map((f) => f.weight);
      const min = Math.min(...weights);
      const max = Math.max(...weights);
      const idx = Math.round(((weight - min) / (max - min)) * (this.arrowWidths.length - 1));
      return this.arrowWidths[idx] || 1;
    },
    getArrowColor(weight, minW, maxW) {
      if (minW === maxW) return 'hsl(174, 49%, 50%)';
      const t = (weight - minW) / (maxW - minW);
      const lightness = 80 - t * 50;
      return `hsl(174, 49%, ${lightness}%)`;
    },
    clusterPoints(pixelPoints) {
      const threshold = 50;
      const clusters = [];
      const visited = new Set();
      const keys = Object.keys(pixelPoints);
      for (let i = 0; i < keys.length; i++) {
        if (visited.has(keys[i])) continue;
        const p1 = pixelPoints[keys[i]];
        let cluster = { keys: [keys[i]], x: p1.x, y: p1.y };
        visited.add(keys[i]);
        for (let j = i + 1; j < keys.length; j++) {
          if (visited.has(keys[j])) continue;
          const p2 = pixelPoints[keys[j]];
          const dx = p2.x - p1.x,
            dy = p2.y - p1.y;
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
    computeOffsets(p1, p2, offset) {
      const dx = p2.x - p1.x,
        dy = p2.y - p1.y;
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len === 0) return { offsetA1: p1, offsetB1: p2, offsetA2: p1, offsetB2: p2 };
      const ox = -(dy / len) * offset,
        oy = (dx / len) * offset;
      return {
        offsetA1: { x: p1.x + ox, y: p1.y + oy },
        offsetB1: { x: p2.x + ox, y: p2.y + oy },
        offsetA2: { x: p1.x - ox, y: p1.y - oy },
        offsetB2: { x: p2.x - ox, y: p2.y - oy },
      };
    },
    drawArrowRect(p1, p2, width, fromKey, toKey, weight, minW, maxW) {
      const dx = p2.x - p1.x,
        dy = p2.y - p1.y,
        len = Math.sqrt(dx * dx + dy * dy);
      const tipW = Math.max(width * 6, 25);
      const bodyLen = Math.max(len - tipW, 0);
      const angle = Math.atan2(dy, dx);
      this.ctx.save();
      this.ctx.translate(p1.x, p1.y);
      this.ctx.rotate(angle);
      const isHover =
        this.hoveredArrow &&
        this.hoveredArrow.fromKey === fromKey.join(',') &&
        this.hoveredArrow.toKey === toKey.join(',');
      this.ctx.fillStyle = isHover ? 'orange' : this.getArrowColor(weight, minW, maxW);
      this.ctx.fillRect(0, -width / 2, bodyLen, width);
      this.ctx.beginPath();
      this.ctx.moveTo(bodyLen, -width / 2);
      this.ctx.lineTo(bodyLen + tipW, -width / 2);
      this.ctx.lineTo(bodyLen, width + 3);
      this.ctx.closePath();
      this.ctx.fill();
      this.ctx.restore();

      const pStart = p1;
      const pTip = {
        x: p1.x + Math.cos(angle) * (bodyLen + tipW),
        y: p1.y + Math.sin(angle) * (bodyLen + tipW),
      };
      this.arrowShapes.push({
        pStart,
        pTip,
        width,
        fromKey: fromKey.join(','),
        toKey: toKey.join(','),
      });
    },
    drawFlows(zoomAnimEvent) {
      this.ctx.clearRect(0, 0, this.canvas.width, this.canvas.height);
      this.dotShapes = [];
      this.arrowShapes = [];

      const allFlows = this.getFilteredFlows();
      if (allFlows.length === 0) return;

      const weights = allFlows.map((f) => f.weight);
      const minW = Math.min(...weights);
      const maxW = Math.max(...weights);

      const pixelPoints = {};
      for (const key in this.points) {
        const latlng = this.points[key]?.latlng;
        pixelPoints[key] = this.map.latLngToContainerPoint(latlng);
      }

      const clusters = this.clusterPoints(pixelPoints);
      const keyToCluster = {};
      clusters.forEach((c) => c.keys.forEach((k) => (keyToCluster[k] = c)));

      // Group flows by their from-to clusters
      const flows = allFlows
        .map((f) => ({
          fromCluster: keyToCluster[f.from],
          toCluster: keyToCluster[f.to],
          weight: f.weight,
          fromKey: f.from,
          toKey: f.to,
        }))
        .sort((a, b) => a.weight - b.weight);

      const flowGroups = {};
      flows.forEach((f) => {
        const key = `${f.fromCluster.x}-${f.fromCluster.y}|${f.toCluster.x}-${f.toCluster.y}`;
        if (!flowGroups[key]) flowGroups[key] = [];
        flowGroups[key].push(f);
      });

      const drawnPairs = new Set();
      Object.keys(flowGroups).forEach((key) => {
        if (drawnPairs.has(key)) return;

        const group = flowGroups[key];
        const f = group[0];
        const fromP = { x: f.fromCluster.x, y: f.fromCluster.y };
        const toP = { x: f.toCluster.x, y: f.toCluster.y };

        const oppositeKey = `${f.toCluster.x}-${f.toCluster.y}|${f.fromCluster.x}-${f.fromCluster.y}`;
        const opposite = flowGroups[oppositeKey];

        // compute spacing offsets for parallel arrows
        const spacing = 4;
        const { offsetA1, offsetB1, offsetA2, offsetB2 } = this.computeOffsets(fromP, toP, spacing);

        group.forEach((flow) => {
          this.drawArrowRect(
            offsetA1,
            offsetB1,
            this.getArrowWidth(flow.weight),
            [flow.fromKey],
            [flow.toKey],
            flow.weight,
            minW,
            maxW,
          );
        });

        if (opposite) {
          opposite.forEach((flow) => {
            this.drawArrowRect(
              offsetB2,
              offsetA2,
              this.getArrowWidth(flow.weight),
              [flow.fromKey],
              [flow.toKey],
              flow.weight,
              minW,
              maxW,
            );
          });
          drawnPairs.add(oppositeKey);
        }

        drawnPairs.add(key);
      });

      // Draw the cluster dots
      clusters.forEach((c) => {
        const totalWeight = c.keys.reduce((sum, k) => {
          return (
            sum +
            allFlows.filter((f) => f.from === k || f.to === k).reduce((s, f) => s + f.weight, 0)
          );
        }, 0);
        const radiusIdx = Math.round(
          ((totalWeight - 1) / (totalWeight + 1)) * (this.dotSizes.length - 1),
        );
        const radius = this.dotSizes[radiusIdx] || 6;
        this.ctx.beginPath();
        this.ctx.arc(c.x, c.y, radius, 0, Math.PI * 2);
        this.ctx.fillStyle = '#28726c';
        this.ctx.fill();
        this.ctx.lineWidth = 2;
        this.ctx.strokeStyle = '#fff';
        this.ctx.stroke();
        this.dotShapes.push({ center: { x: c.x, y: c.y }, radius, key: c.keys.join(',') });
      });

      // Update debug
      this.debug = {
        selected: this.selectedPoint ? this.selectedPoint.join(',') : 'none',
        entities: allFlows.length,
        segments: Object.keys(flowGroups).length,
        arrows: this.arrowShapes.length,
      };
    },
    pointInCircle(x, y, circle) {
      const dx = x - circle.center.x,
        dy = y - circle.center.y;
      return dx * dx + dy * dy <= circle.radius * circle.radius;
    },

    pointOnArrow(x, y, arrow) {
      const { pStart, pTip, width } = arrow;
      const dx = pTip.x - pStart.x,
        dy = pTip.y - pStart.y;
      const len = Math.sqrt(dx * dx + dy * dy);
      if (len === 0) return false;
      const ux = dx / len,
        uy = dy / len;
      const px = x - pStart.x,
        py = y - pStart.y;
      const proj = px * ux + py * uy;
      if (proj < 0 || proj > len) return false;
      const perp = Math.abs(-uy * px + ux * py);
      return perp <= width / 2 + 4;
    },

    getClusterTraffic(clusterKey) {
      const keys = [clusterKey]; // single key
      const flows = this.getFilteredFlows();
      let outgoing = 0,
        incoming = 0;
      flows.forEach((f) => {
        const fromIn = keys.includes(f.from);
        const toIn = keys.includes(f.to);
        if (fromIn && !toIn) outgoing += f.weight;
        if (!fromIn && toIn) incoming += f.weight;
      });
      return { outgoing, incoming };
    },

    getClusterArrowTraffic(fromClusterKey, toClusterKey) {
      const fromKeys = [fromClusterKey];
      const toKeys = [toClusterKey];
      const flows = this.getFilteredFlows();
      let total = 0;
      flows.forEach((f) => {
        if (fromKeys.includes(f.from) && toKeys.includes(f.to)) total += f.weight;
      });
      return total;
    },
    onMapClick(e) {
      const p = this.map.latLngToContainerPoint(e.latlng);
      for (const dot of this.dotShapes) {
        if (this.pointInCircle(p.x, p.y, dot)) {
          selectedPoint = dot.key.split(','); // <--- key fix
          const keys = dot.key.split(',');
          const names = keys.map((k) => this.points[k]?.label || k).join(', ');
          let totalOutgoing = 0,
            totalIncoming = 0;
          keys.forEach((k) => {
            const { outgoing, incoming } = this.getClusterTraffic(k);
            totalOutgoing += outgoing;
            totalIncoming += incoming;
          });
          this.drawFlows();
          alert(
            `Clicked city/cluster: ${names}\nOutgoing trips: ${totalOutgoing}\nIncoming trips: ${totalIncoming}`,
          );
          return;
        }
      }

      for (const arrow of this.arrowShapes) {
        if (this.pointOnArrow(p.x, p.y, arrow)) {
          const fromKeys = arrow.fromKey.split(',');
          const toKeys = arrow.toKey.split(',');
          let totalTrips = 0;
          fromKeys.forEach((fk) => {
            toKeys.forEach((tk) => {
              totalTrips += this.getClusterArrowTraffic(fk, tk);
            });
          });
          const fromNames = fromKeys.map((k) => this.points[k]?.label || k).join(', ');
          const toNames = toKeys.map((k) => this.points[k]?.label || k).join(', ');
          alert(`Clicked arrow from ${fromNames} to ${toNames}\nTotal trips: ${totalTrips}`);
          return;
        }
      }
    },
  },
  watch: {
    open(isOpen) {
      if (isOpen) {
        setTimeout(() => {
          this.initMap();
          this.initPoints();
          this.initCanvas();
          this.drawFlows();
        }, 2000);
      }
    },
  },

  template: `
    <v-dialog fullscreen :model-value="open">
      <v-toolbar color="primary" dark>
        <v-toolbar-title>{{ translations.mapVisualization_ }}</v-toolbar-title>
        <v-spacer></v-spacer>
        <v-btn prepend-icon="mdi-ballot" variant="elevated" @click="$emit('advancedSearch')">Advanced search</v-btn>
        <v-btn icon="mdi-close" @click="$emit('update:open', false)"></v-btn>
      </v-toolbar>

      <v-sheet class="relative">
        <div id="map-visualization" class="relative">
          <div style="height: 100%; position: relative;">
            <div ref="mapContainer"
                 :id="mapId"
                 class="leaflet-map"
                 :style="{ height: 'calc(100vh - 64px)' }"></div>
            <canvas ref="overlay" id="flow-overlay" style="position:absolute; top:0; left:0; pointer-events:none; z-index:1000; width: 100%;"></canvas>
            <div id="debug-panel" style="position:absolute; top:10px; right:10px; background: rgba(0,0,0,0.7); color:#0f0; font-family:monospace; font-size:12px; padding:8px 10px; border-radius:6px; max-width:220px; line-height:1.4; z-index:1000;">
              <b>Debug Info</b><br/>
              Selected: {{ debug.selected }}<br/>
              Entities drawn: {{ debug.entities }}<br/>
              Segments drawn: {{ debug.segments }}<br/>
              Arrows drawn: {{ debug.arrows }}
            </div>
            <div id="clear-filter" @click="clearFilter" style="position:absolute; bottom:10px; left:10px; background:#fff; color:#000; font-family:monospace; font-size:12px; padding:6px 10px; border-radius:6px; cursor:pointer; z-index:1000; box-shadow:0 2px 4px rgba(0,0,0,0.3);">
              Clear Filter
            </div>
          </div>

          <!-- Tooltip -->
          <!-- <v-card
            v-if="menu"
            class="absolute h-fit"
            :style="{ left: tooltip.x + 'px', top: tooltip.y + 'px', maxWidth: '250px', zIndex: 50 }"
          >
            <v-card-text v-html="tooltip.content"></v-card-text>
          </v-card> -->

          <!-- Loading Overlay -->
          <!-- <v-overlay v-model="loading" persistent class="d-flex align-center justify-center" content-class="d-flex flex-column align-center justify-center">
            <v-progress-circular indeterminate color="primary" size="64"></v-progress-circular>
            <div class="mt-4 text-h6">{{ loadingMessage }}</div>
          </v-overlay> -->

          <!-- Error Message -->
          <!-- <v-container>
            <v-card
              v-if="errorMessage"
              class="d-flex flex-column align-center justify-center text-center pa-6"
              style="inset:0; z-index:100;"
            >
              <v-icon color="error" size="64">mdi-alert-circle-outline</v-icon>
              <div class="text-h6 mt-2">{{ errorMessage }}</div>
              <v-btn class="mt-4" color="primary" @click="retry">Retry</v-btn>
            </v-card>
          </v-container> -->
        </div>
      </v-sheet>
    </v-dialog>
    
  `,
});
