const InlineMediaRenderer = Vue.defineComponent({
    props: {
      media: {
        type: Object,
      },
      useMetadata: {
        type: Boolean,
      },
      mediaType: {
        type: String,
      },
      contentStyle: {
        type: String,
        default: 'height: 450px;'
      },
    },
    data: () => ({
      translations: window.translations,
      iconMap: {
        image: 'mdi-image',
        video: 'mdi-video',
        pdf: 'mdi-file-pdf-box',
        audio: 'mdi-music-box',
        unknown: 'mdi-file-download'
      },
    }),
    template: `
      <div v-if="media">
        <v-toolbar density="compact" class="px-2">
          <div v-if="useMetadata" class="w-100 d-flex justify-space-between align-center">
            <div class="d-flex align-center">
              <v-icon
                :icon="iconMap[mediaType]"
                :color="mediaType === 'pdf' ? 'red' : 'primary'"
              ></v-icon>
              <v-divider vertical class="mx-2"></v-divider>
              <v-chip prepend-icon="mdi-identifier" variant="text" class="font-weight-bold"
                >{{ media.id }}</v-chip
              >
              <v-divider vertical class="mx-2"></v-divider>
              <v-tooltip location="bottom">
                <template v-slot:activator="{ props }">
                  <v-chip
                    prepend-icon="mdi-tag"
                    variant="plain"
                    v-if="media.category"
                    size="small"
                    v-bind="props"
                  >
                    {{ media.category.title }}
                  </v-chip>
                </template>
                <span>{{ translations.category_ }}</span>
              </v-tooltip>
              <uni-field
                class="text-truncate"
                :english="media.title || 'Untitled'"
                :arabic="media.title_ar || ''"
                disable-spacing
              ></uni-field>
              <div class="cursor-pointer">
                <v-list-item class="text-caption ml-1 py-0">
                  <template v-slot:prepend>
                    <v-tooltip location="bottom">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" icon="mdi-file-outline"></v-icon>
                      </template>
                      <div class="d-flex flex-column align-center">
                        <span><strong>{{ translations.filename_ }}</strong></span>
                        <span>{{ translations.clickToCopy_ }}</span>
                      </div>
                    </v-tooltip>
                  </template>
                  <v-tooltip location="bottom">
                    <template v-slot:activator="{ props }">
                      <div v-bind="props" class="text-truncate">{{ media.filename }}</div>
                    </template>
                    {{ translations.filename_ }}
                  </v-tooltip>
                </v-list-item>
              </div>
              <div class="d-flex align-center cursor-pointer">
                <v-list-item class="text-caption ml-1 py-0 text-truncate">
                  <template v-slot:prepend>
                    <v-tooltip location="bottom">
                      <template v-slot:activator="{ props }">
                        <v-icon v-bind="props" icon="mdi-fingerprint"></v-icon>
                      </template>
                      <div class="d-flex flex-column align-center">
                        <span><strong>{{ translations.hash_ }}</strong></span>
                        <span>{{ translations.clickToCopy_ }}</span>
                      </div>
                    </v-tooltip>
                  </template>
                  <v-tooltip location="bottom">
                    <template v-slot:activator="{ props }">
                      <div v-bind="props" class="text-truncate">{{ media.etag }}</div>
                    </template>
                    {{ media.etag }}
                  </v-tooltip>
                </v-list-item>
              </div>
            </div>
          </div>
          <v-spacer></v-spacer>
          <v-btn @click="mediaPlayer?.requestFullscreen()" icon="mdi-fullscreen" class="ml-2" size="small"></v-btn>
          <v-btn icon="mdi-close" class="ml-2" size="small" @click="closeExpandedMedia()"></v-btn>
        </v-toolbar>

        <div :style="contentStyle">
          <div
            v-if="['video', 'audio'].includes(mediaType)"
            id="playerContainer"
            ref="playerContainer"
            class="inner-video-full-height"
            style="height: 100%"
          ></div>
          <object v-if="mediaType === 'pdf'" :data="media.s3url" class="w-100" style="height: 100%"></object>
          <v-img v-if="mediaType === 'image'" :src="media.s3url" class="bg-grey-lighten-2" style="height: 100%"></v-img>
        </div>
      </div>
    `,
  });
  