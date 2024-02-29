Vue.component('visualization', {
  props: ['item', 'i18n'],

  data() {
    return {
      dlg: false,
      loading: false,
      graph: null,
      graphData: { nodes: [], links: [] }, // Initialize with empty arrays
      switchMode: false,
      initRendered: false, // initial zoom to fit flag
    };
  },

  methods: {
    show() {
      this.dlg = true;
    },

    hide() {
      this.dlg = false;
    },

    getGraphData(id, type, expanded = true) {
      this.loading = true;

      return axios
        .get('/admin/api/graph/json', {
          params: { id, type, expanded },
        })
        .then((res) => {
          this.graphData = res.data; // Return the data for further processing
        })
        .catch((err) => {
          console.error(err);
          return null; // Return null to indicate an error
        })
        .finally(() => {
          this.loading = false;
        });
    },

    visualize(item) {
      this.show();
      this.getGraphData(item.id, item.class).then(() => {
        this.drawGraph();
      });
    },

    visualizeQuery() {
      this.show();
      this.loading = true;

      axios
        .get('/admin/api/graph/data')
        .then((response) => {
          this.graphData = response.data;
          this.drawGraph(); // Call drawGraph to render the graph with new data
        })
        .catch((error) => {
          console.error('Error fetching graph data from Redis:', error);
          this.$emit('error', 'Failed to load graph data');
        })
        .finally(() => {
          this.loading = false;
        });
    },

    drawGraph() {
      if (!this.graph) {
        this.graph = ForceGraph()(document.querySelector('#graph'));
      }

      this.graph
        .cooldownTime(800)
        .nodeId('id')
        .nodeLabel('title')
        .linkSource('source')
        .linkTarget('target')
        .linkColor(() => '#444')
        .linkCanvasObjectMode(() => 'after')

        .linkCanvasObject((link, ctx) => {
          const MAX_FONT_SIZE = 1.2;
          const LABEL_NODE_MARGIN = this.graph.nodeRelSize() * 1.5;

          const start = link.source;
          const end = link.target;

          // ignore unbound links
          if (typeof start !== 'object' || typeof end !== 'object') return;

          // calculate label positioning
          const textPos = Object.assign(
            ...['x', 'y'].map((c) => ({
              [c]: start[c] + (end[c] - start[c]) / 4, // calc  point so its closer to source node !
            })),
          );

          const relLink = { x: end.x - start.x, y: end.y - start.y };

          const maxTextLength =
            Math.sqrt(Math.pow(relLink.x, 2) + Math.pow(relLink.y, 2)) - LABEL_NODE_MARGIN * 2;

          let textAngle = Math.atan2(relLink.y, relLink.x);
          // maintain label vertical orientation for legibility
          if (textAngle > Math.PI / 2) textAngle = -(Math.PI - textAngle);
          if (textAngle < -Math.PI / 2) textAngle = -(-Math.PI - textAngle);

          const label = `${link.type}`;
          if (!label) {
            return;
          }

          // estimate fontSize to fit in link length
          ctx.font = '1px Sans-Serif';
          const fontSize = Math.min(MAX_FONT_SIZE, maxTextLength / ctx.measureText(label).width);
          ctx.font = `${fontSize}px monospace, 'Courier New', sans-serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map((n) => n + fontSize * 0.3); // some padding

          // draw text label (with background rect)
          ctx.save();
          ctx.translate(textPos.x, textPos.y);
          ctx.rotate(textAngle);

          ctx.fillStyle = __settings__.dark ? 'rgba(10,10,10,0.5)' : 'rgba(255, 255, 255, 0.8)';
          ctx.fillRect(-bckgDimensions[0] / 2, -bckgDimensions[1] / 2, ...bckgDimensions);

          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = __settings__.dark ? '#ddd' : 'darkgrey';
          ctx.fillText(label, 0, 0);
          ctx.restore();
        })

        .linkColor(() => {
          return __settings__.dark ? 'rgba(100,100,100,0.9)' : '#ddd';
        })

        .nodeCanvasObjectMode((node) => 'replace')

        .onNodeClick((node, event) => {
          if (event.ctrlKey || event.metaKey) {
            // command click or ctrl click
            const id = node.id.substring(1);
            const type = node.type.toLowerCase();
            if (['bulletin', 'actor', 'incident'].includes(type)) {
              this.$root.previewItem(`/admin/api/${type}/${node._id}`);
            }
          } else if (node.collapsed) {
            this.loadNode(node);
          }

          //    Graph.graphData([]);
        })
        .onEngineStop(() => {
          if (!this.initRendered) {
          this.graph.zoomToFit(500);
          this.initRendered = true; // Update the flag
        }

        })
        .graphData(this.graphData);
    },

    switchMode() {
      this.drawGraph(this.textMode);
    },

    loadNode(node) {
      const id = node._id;
      const type = node.type.toLowerCase();
      if (!['bulletin', 'actor', 'incident'].includes(type)) {
        return;
      }
      this.loading = true;
      axios
        .get(`/admin/api/graph/json`, { params: { id, type, expanded: false } })
        .then((res) => {
          this.mergeGraphData(res.data);
          this.drawGraph();
        })
        .catch((err) => {
          console.error(err);
        })
        .finally(() => {
          this.loading = false;
        });
    },

    mergeGraphData(newGraphData) {
      // Merge nodes
      const existingNodeIds = new Set(this.graphData.nodes.map((n) => n.id));
      newGraphData.nodes.forEach((newNode) => {
        if (!existingNodeIds.has(newNode.id)) {
          this.graphData.nodes.push(newNode);
          existingNodeIds.add(newNode.id);
        }
      });

      // Merge links (ensure your link data structure matches this logic)
      const existingLinkPairs = new Set(this.graphData.links.map((l) => `${l.source}-${l.target}`));
      newGraphData.links.forEach((newLink) => {
        const linkPair = `${newLink.source}-${newLink.target}`;
        if (!existingLinkPairs.has(linkPair)) {
          this.graphData.links.push(newLink);
          existingLinkPairs.add(linkPair);
        }
      });
    },

    textMode() {
      this.graph
        .nodeCanvasObject((node, ctx, globalScale) => {
          const label = node.title;
          const fontSize = 14 / globalScale;
          ctx.font = `${fontSize}px Sans-Serif`;
          const textWidth = ctx.measureText(label).width;
          const bckgDimensions = [textWidth, fontSize].map((n) => n + fontSize * 0.3); // some padding

          ctx.fillStyle = __settings__.dark ? 'rgba(10,10,10,0.5)' : 'rgba(255, 255, 255, 0.8)';
          ctx.fillRect(
            node.x - bckgDimensions[0] / 2,
            node.y - bckgDimensions[1] / 2,
            ...bckgDimensions,
          );

          ctx.textAlign = 'center';
          ctx.textBaseline = 'middle';
          ctx.fillStyle = node.color;
          ctx.fillText(label, node.x, node.y);

          node.__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
        })
        .nodePointerAreaPaint((node, color, ctx) => {
          ctx.fillStyle = color;
          const bckgDimensions = node.__bckgDimensions;
          bckgDimensions &&
            ctx.fillRect(
              node.x - bckgDimensions[0] / 2,
              node.y - bckgDimensions[1] / 2,
              ...bckgDimensions,
            );
        });
    },

    circleMode() {
      this.graph.nodeCanvasObject((node, ctx, globalScale) => {
        ctx.fillStyle = node.color;
        ctx.beginPath();
        ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
        ctx.fill();
      });
    },
  },

  template: `
         <v-dialog fullscreen v-model="dlg">


        <v-card>
          <v-btn icon loading v-show="loading" style="z-index: 900">
            <v-icon></v-icon>
          </v-btn>
          <v-btn style="z-index: 10000" @click="hide" icon absolute right top>
            <v-icon>mdi-close</v-icon>

          </v-btn>
          <div class="graph-wrap">
            <div class="graph-legend">

              <div class="caption mr-3">
                <v-icon small color="blue" left> mdi-checkbox-blank-circle</v-icon>
                {{ i18n.bulletins_ }}
              </div>

              <div class="caption mr-3">
                <v-icon small color="green" left> mdi-checkbox-blank-circle</v-icon>
                {{ i18n.actors_ }}
              </div>

              <div class="caption mr-3">
                <v-icon small color="yellow" left> mdi-checkbox-blank-circle</v-icon>
                {{ i18n.incidents_ }}
              </div>

              <div class="caption mr-3">
                <v-icon small color="ff4433" left> mdi-checkbox-blank-circle</v-icon>
                {{ i18n.locations_ }}
              </div>
              <div>
              </div>
            </div>

            <div id="graph"></div>

            <div class="graph-tip">
              <v-icon left>mdi-information-outline</v-icon>
              {{ i18n.visInfo_ }}
            </div>
          </div>
        </v-card>

      </v-dialog>

  `,
});