Vue.component('visualization', {
    props: ["item", "i18n"],

    data: () => ({
        dlg: false,
        item: null,
        graph: null,
        graphData: {},
        loading: false,
        switchMode: false,


        // static color data
        ACTORCOLOR: '#74daa3',
        BULLETINCOLOR: '#4a9bed',
        INCIDENTCOLOR: '#f4be39',
        LOCATIONCOLOR: '#ff663366',
    }),
    mounted() {


    },

    methods: {

        switchMode() {

            this.drawGraph(this.textMode);
        },


        getAllRelations(item) {
            let br = item.bulletin_relations;
            br.map(x => x.bulletin).map(x => x.class = 'bulletin');
            let ar = item.actor_relations;
            ar.map(x => x.actor).map(x => x.class = 'actor');
            let ir = item.incident_relations;
            ir.map(x => x.incident).map(x => x.class = 'incident');
            return br.map(x => x.bulletin).concat(ar.map(x => x.actor)).concat(ir.map(x => x.incident));

        },


        generateGraph(item) {
            //console.log(this.bulletin);


            function find_relation_type(item, relation, target) {

                if (item.class == 'Bulletin' && target == 'Bulletin') {
                    if (relation.related_as) {
                        return translations.btobRelateAs[relation.related_as].en;
                    }


                }
                ;
                if ((item.class == 'Bulletin' && target == 'Actor') || (item.class == 'Actor' && target == 'Bulletin')) {
                    // relation is an array here

                    return relation.related_as.reduce((p, a) => p + translations.btoaRelateAs[a].en + ' ', '');
                }
                ;

                if (item.class == 'Actor' && target == 'Actor') {

                    if (relation.related_as) {
                        if (relation.actor.id > item.id) {
                            return translations.atoaRelateAs[relation.related_as].en.text;
                        } else {
                            return translations.atoaRelateAs[relation.related_as].en.revtext;
                        }

                    }

                }


                if (target == 'Incident') {
                    return 'default'
                }
                ;
                return '';


            }

            // generate ids based on relations
            // prepend a/b/i based on entity type (actor/bulletin/incident) to avoid clashes during graph construction
            const bulletins = item.bulletin_relations.map(x => {
                return {
                    id: 'B' + x.bulletin.id,
                    related_as: find_relation_type(item, x, 'Bulletin'),
                    title: x.bulletin.title,
                    color: this.BULLETINCOLOR,

                    type: 'Bulletin',
                    collapsed: true,
                    childLinks: []
                }
            });
            const actors = item.actor_relations.map(x => {
                return {
                    id: 'A' + x.actor.id,
                    related_as: find_relation_type(item, x, 'Actor'),
                    title: x.actor.name,
                    color: this.ACTORCOLOR,
                    type: 'Actor',
                    collapsed: x.collapsed || true,
                    childLinks: []
                }
            });
            const incidents = item.incident_relations.map(x => {
                return {
                    id: 'I' + x.incident.id,
                    related_as: find_relation_type(item, x, 'Incident'),
                    title: x.incident.title,
                    color: this.INCIDENTCOLOR,
                    type: 'Incident',
                    collapsed: x.collapsed || true,
                    childLinks: []
                }
            });
            //locations
            let locations = item.locations || [];

            locations = locations.map(x => {
                return {
                    id: 'L' + x.id,
                    related_as: 'location',
                    title: x.title,
                    color: this.LOCATIONCOLOR,
                    type: 'Location',
                    collapsed: false,
                    childLinks: []
                }
            });


            // event locations
            //helper method
            let elocations = [];
            if (item.events && item.events > 0) {
                elocations = item.events.map(x => x.location);
            }


            locations = locations.map(x => {
                return {
                    id: 'L' + x.id,
                    related_as: 'location',
                    title: x.title,
                    color: '#ff663366',
                    type: 'Location',
                    collapsed: false,
                    childLinks: []
                }
            });

            let nodes = bulletins.concat(actors).concat(incidents).concat(locations).concat(elocations);


            // generate links
            // item class will always be one of (Bulletin, Actor, Incident)
            const links = nodes.map(x => {

                return {source: item.class.substring(0, 1) + item.id, target: x.id, type: x.related_as}

            });

            // console.log(links);

            //lastly add the root node
            nodes.unshift({
                id: item.class.substring(0, 1) + item.id,
                title: item.title || item.name,
                color: '#000',
                type: item.class,
                collapsed: false
            });
            // console.log(nodes);

            return {nodes: nodes, links: links};


        },


        visualize(item) {
            this.show();
            this.item = item;
            // wait one tick for the component to render
            this.$nextTick(() => {
                // always set data to the graph data attribute to be used later when we add more data
                this.graphData = this.generateGraph(this.item);
                this.drawGraph();

                // also generate first level
                const lvl1 = this.getAllRelations(this.item);

                lvl1.forEach((item, index) => {
                    setTimeout(() => {
                        this.loadNode({
                            id: 'x' + item.id,
                            type: item.class
                        })

                    }, index * 0.1)
                })

            })


        },

        show() {
            this.dlg = true;
        },
        hide() {
            this.dlg = false;
        },

        mergeGraphData(graphData) {
            // this will merge additional graph data into existing graph
            // merge only nodes that don't already exist

            graphData.nodes.forEach(x => {
                    if (!this.graphData.nodes.some(e => (e.id == x.id))) {
                        this.graphData.nodes.push(x);
                    }
                }
            );
            this.graphData = {nodes: this.graphData.nodes, links: this.graphData.links.concat(graphData.links)};
        },
        loadNode(node) {
            this.loading = true;
            const id = node.id.substring(1);

            const type = node.type.toLowerCase();
            if (type == 'bulletin') {
                axios.get(`/admin/api/${type}/${id}`).then(res => {
                    const bulletin = res.data;
                    const extraGraph = this.generateGraph(bulletin)
                    this.mergeGraphData(extraGraph);

                    //console.log(this.graph);
                    this.drawGraph();

                }).catch(err => {
                    console.log(err);
                }).finally(() => {
                    this.loading = false;
                    node.collapsed = false;
                    node.color = node.color + '66';
                })
            } else if (type == 'actor') {
                axios.get(`/admin/api/${type}/${id}`).then(res => {
                    const actor = res.data;
                    //console.log(actor);

                    const extraGraph = this.generateGraph(actor)
                    this.mergeGraphData(extraGraph);


                    //console.log(this.graph);
                    this.drawGraph();

                }).catch(err => {
                    console.log(err);
                }).finally(() => {
                    this.loading = false;
                    node.collapsed = false;
                    node.color = node.color + '66';
                })
            } else if (type == 'incident') {
                axios.get(`/admin/api/${type}/${id}`).then(res => {
                    const actor = res.data;
                    //console.log(actor);

                    const extraGraph = this.generateGraph(actor)
                    this.mergeGraphData(extraGraph);


                    //console.log(this.graph);
                    this.drawGraph();

                }).catch(err => {
                    console.log(err);
                }).finally(() => {
                    this.loading = false;
                    node.collapsed = false;
                    node.color = node.color + '66';
                })
            }
        },

        drawGraph(textNodes = false) {

            // console.log(this.graphData.links);
            const elem = document.getElementById('graph');
            if (!this.graph) {
                this.graph = ForceGraph()(this.$el.querySelector('#graph'));
            }
            this.graph.graphData(this.graphData)
                .nodeLabel('title')
                // implement custom link text

                .linkCanvasObjectMode(() => 'after')
                .linkCanvasObject((link, ctx) => {
                    const MAX_FONT_SIZE = 1.2;
                    const LABEL_NODE_MARGIN = this.graph.nodeRelSize() * 1.5;

                    const start = link.source;
                    const end = link.target;

                    // ignore unbound links
                    if (typeof start !== 'object' || typeof end !== 'object') return;

                    // calculate label positioning
                    const textPos = Object.assign(...['x', 'y'].map(c => ({
                        [c]: start[c] + (end[c] - start[c]) / 4 // calc  point so its closer to source node !
                    })));

                    const relLink = {x: end.x - start.x, y: end.y - start.y};

                    const maxTextLength = Math.sqrt(Math.pow(relLink.x, 2) + Math.pow(relLink.y, 2)) - LABEL_NODE_MARGIN * 2;

                    let textAngle = Math.atan2(relLink.y, relLink.x);
                    // maintain label vertical orientation for legibility
                    if (textAngle > Math.PI / 2) textAngle = -(Math.PI - textAngle);
                    if (textAngle < -Math.PI / 2) textAngle = -(-Math.PI - textAngle);

                    const label = `${link.type}`;
                    if (!label) {
                        return
                    }

                    // estimate fontSize to fit in link length
                    ctx.font = '1px Sans-Serif';
                    const fontSize = Math.min(MAX_FONT_SIZE, maxTextLength / ctx.measureText(label).width);
                    ctx.font = `${fontSize}px monospace, 'Courier New', sans-serif`;
                    const textWidth = ctx.measureText(label).width;
                    const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.3); // some padding

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
                }).cooldownTime(800)

                .linkColor(()=>{
                    return __settings__.dark ? 'rgba(100,100,100,0.9)': '#ddd'
                })

                // .linkDirectionalParticles(1)
                // .linkCurvature(0.07)
                // .linkDirectionalParticleWidth(1.5)

                // .onNodeHover(node => elem.style.cursor = node && node.childLinks.length ? 'pointer' : null)
                .onNodeClick((node, event) => {

                    if (event.ctrlKey || event.metaKey) {
                        console.log(node);
                        // command click or ctrl click
                        const id = node.id.substring(1);
                        const type = node.type.toLowerCase();
                        if (['bulletin', 'actor', 'incident'].includes(type)) {
                            this.$root.previewItem(`/admin/api/${type}/${node.id.substring(1)}`);
                        }

                    } else if (node.collapsed) {
                        this.loadNode(node);
                    }


                    //    Graph.graphData([]);

                }).nodeCanvasObjectMode(node => 'replace').onZoomEnd(this.zoomHandler);






            // responsive
            // elementResizeDetectorMaker().listenTo(
            //     this.$el.querySelector('#graph'),
            //     el => {
            //         this.graph.width(el.offsetWidth);
            //         this.graph.height(el.offsetHeight);
            //
            //
            //     }
            // );


            this.graph.onEngineStop(() => {
                this.graph.zoomToFit(1200);
                // better way to disable automatic fitting after first invoke
                this.graph.onEngineStop(() => {
                });


            });


        },


        textMode() {
            this.graph.nodeCanvasObject((node, ctx, globalScale) => {
                const label = node.title;
                const fontSize = 14 / globalScale;
                ctx.font = `${fontSize}px Sans-Serif`;
                const textWidth = ctx.measureText(label).width;
                const bckgDimensions = [textWidth, fontSize].map(n => n + fontSize * 0.3); // some padding

                ctx.fillStyle = __settings__.dark ? 'rgba(10,10,10,0.5)' : 'rgba(255, 255, 255, 0.8)';
                ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);

                ctx.textAlign = 'center';
                ctx.textBaseline = 'middle';
                ctx.fillStyle = node.color;
                ctx.fillText(label, node.x, node.y);

                node.__bckgDimensions = bckgDimensions; // to re-use in nodePointerAreaPaint
            })
                .nodePointerAreaPaint((node, color, ctx) => {
                    ctx.fillStyle = color;
                    const bckgDimensions = node.__bckgDimensions;
                    bckgDimensions && ctx.fillRect(node.x - bckgDimensions[0] / 2, node.y - bckgDimensions[1] / 2, ...bckgDimensions);
                })
        },

        circleMode() {

            this.graph.nodeCanvasObject((node, ctx, globalScale) => {
                ctx.fillStyle = node.color;
                ctx.beginPath();
                ctx.arc(node.x, node.y, 5, 0, 2 * Math.PI, false);
                ctx.fill();
            })

        },
        zoomHandler(){
            if(this.graph.zoom() > 5){
                this.textMode();
            }else {
                this.circleMode();
            }
        }


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
              <v-icon small :color="this.BULLETINCOLOR" left> mdi-checkbox-blank-circle</v-icon>
              {{ i18n.bulletins_ }}
            </div>

            <div class="caption mr-3">
              <v-icon small :color="this.ACTORCOLOR" left> mdi-checkbox-blank-circle</v-icon>
              {{ i18n.actors_ }}
            </div>

            <div class="caption mr-3">
              <v-icon small :color="this.INCIDENTCOLOR" left> mdi-checkbox-blank-circle</v-icon>
              {{ i18n.incidents_ }}
            </div>

            <div class="caption mr-3">
              <v-icon small :color="this.LOCATIONCOLOR" left> mdi-checkbox-blank-circle</v-icon>
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
    `
})
