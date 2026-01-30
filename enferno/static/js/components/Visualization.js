const Visualization = Vue.defineComponent({
  data() {
    return {
      mainNodeId: null,
      translations: window.translations,
      dlg: false,
      loading: false,
      graph: null,
      graphData: { nodes: [], links: [], legend: [] }, // Initialize with empty arrays
      initRendered: false, // initial zoom to fit flag
    };
  },

  methods: {
    async loadLibraries() {
      await loadAsset('/static/js/force-graph.min.js');
    },
    show() {
      this.dlg = true;
    },

    hide() {
      this.graph = null;
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
          this.$emit('error', handleRequestError(err));
          this.hide();
          return null; // Return null to indicate an error
        })
        .finally(() => {
          this.loading = false;
        });
    },

    visualize(item) {

        this.mainNodeId = `${item.class.charAt(0).toUpperCase()}${item.class.slice(1)}${item.id}`;


      this.resetGraph();
      this.show();
      this.getGraphData(item.id, item.class).then(async () => {
        await this.drawGraph();
      });
    },
    resetGraph() {
      this.graph = null;
      this.initRendered = false;
    },

    visualizeQuery() {
      this.show();
      this.loading = true;

      axios
        .get('/admin/api/graph/data')
        .then(async (response) => {
          this.graphData = response.data;

          await this.drawGraph(); // Call drawGraph to render the graph with new data
        })
        .catch((error) => {
          console.error('Error fetching graph data from Redis:', error);
          this.hide();
          this.$emit('error', handleRequestError(error));
        })
        .finally(() => {
          this.loading = false;
        });
    },

    async drawGraph() {
      await this.loadLibraries();

      if (!this.graph) {
        this.graph = ForceGraph()(document.querySelector('#graph'));
      }

      // if graph has a start item, Set the color of the main node to black


      if (!!this.mainNodeId) {
        this.graphData.nodes.forEach((node) => {

          if (node.id === this.mainNodeId) {
            node.color = 'black'; // Set the main node color to black
          }
        });
      }

      this.graph
        .cooldownTime(800)
        .nodeId('id')
        .nodeLabel('title')
        .linkSource('source')
        .linkTarget('target')
        .linkCanvasObjectMode(() => 'after')

        .linkCanvasObject(this.drawLink)

        .linkColor(() => {
          return __settings__.dark ? 'rgba(100,100,100,0.9)' : '#ddd';
        })

        .nodeCanvasObjectMode((node) => 'replace')

        .onNodeClick(this.handleNodeClick)
        .onEngineStop(() => {
          if (!this.initRendered) {
            this.graph.zoomToFit(500);
            this.initRendered = true;
          }
        })
        .graphData(this.graphData);
    },


drawLink(link, ctx) {
  const { source: start, target: end, type } = link;
  if (!start || !end) return;

  const text = String(type || ''); // Ensure type is a string
  if (!text) return; // Do nothing if the text is empty

  const FONT_SIZE = 0.6; // Fixed font size
  const PADDING = 0.5;
  const LETTER_SPACING = 0.05; // Desired letter spacing

  // Calculate label position and angle
  const textPos = {
    x: start.x + (end.x - start.x) / 2  + 0.7,
    y: start.y + (end.y - start.y) / 2 ,
  };
  const dx = end.x - start.x;
  const dy = end.y - start.y;
  let textAngle = Math.atan2(dy, dx);

  // Adjust angle for readability
  if (Math.abs(textAngle) > Math.PI / 2) {
    textAngle = textAngle > 0 ? -(Math.PI - textAngle) : -(-Math.PI - textAngle);
  }

  // Set fixed font size and style
  ctx.font = `${FONT_SIZE}px monospace, 'Courier New', sans-serif`;

  // Recalculate text width based on letter spacing
  const individualCharWidth = FONT_SIZE;
  const textWidth = (individualCharWidth * text.length) + (LETTER_SPACING * (text.length - 1));
  const bgWidth = textWidth ;
  const bgHeight = FONT_SIZE ;

  // Draw background
  ctx.save();
  ctx.translate(textPos.x, textPos.y);
  ctx.rotate(textAngle);
  ctx.fillStyle = __settings__.dark ? 'rgba(10,10,10,0.5)' : 'rgba(255,255,255,0.8)';
  ctx.fillRect(-bgWidth / 2, -bgHeight / 2, bgWidth, bgHeight);

  // Draw text with letter spacing
  ctx.fillStyle = __settings__.dark ? '#ddd' : 'darkgrey';
  ctx.textAlign = 'center';
  ctx.textBaseline = 'middle';

  const startX = -textWidth / 2 + 0.8;
  for (let i = 0; i < text.length; i++) {
    ctx.fillText(text[i], startX + i * (individualCharWidth + LETTER_SPACING), 0);
  }

  ctx.restore();
}







,


    handleNodeClick(node, event) {
      if (node.restricted) {
      return; // Do nothing if the node is restricted
    }
      if (event.ctrlKey || event.metaKey) {

        const id = node.id.substring(1);
        const type = node.type.toLowerCase();
        if (['bulletin', 'actor', 'incident'].includes(type)) {
          this.$root.previewItem(`/admin/api/${type}/${node._id}`);
        }
      } else if (node.collapsed) {
        this.loadNode(node);
      }
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
        .then(async (res) => {
          this.mergeGraphData(res.data);
          await this.drawGraph();
        })
        .catch(console.error)
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


        <div id="graph-layout">
          <div class="graph-header">
          <v-toolbar density="compact">
            <v-toolbar-title class="align-center">
              <div class="d-flex align-center">

                <div class="text-caption mr-3">
                  <v-icon size="small" :color="graphData.legend.bulletin" left> mdi-checkbox-blank-circle</v-icon>
                  {{ translations.bulletins_ }}
                </div>

                <div class="text-caption mr-3">
                  <v-icon size="small" :color="graphData.legend.actor" left> mdi-checkbox-blank-circle</v-icon>
                  {{ translations.actors_ }}
                </div>

                <div class="text-caption mr-3">
                  <v-icon size="small" :color="graphData.legend.incident" left> mdi-checkbox-blank-circle</v-icon>
                  {{ translations.incidents_ }}
                </div>

                <div class="text-caption mr-3">
                  <v-icon size="small" :color="graphData.legend.location" left> mdi-checkbox-blank-circle</v-icon>
                  {{ translations.locations_ }}
                </div>
                <v-spacer></v-spacer>
                <v-btn size="small" icon="mdi-close" @click="hide"></v-btn>

              </div>

            </v-toolbar-title>
          </v-toolbar>
          </div>


            <div id="graph"></div>
          
          

            <div class="graph-footer">
              <v-chip variant="text" prepend-icon="mdi-information-outline">
                {{ translations.visInfo_ }}
              </v-chip>

            </div>


          


        </div>

      </v-dialog>

    `,
});
