const UserCard = Vue.defineComponent({
  props: ['user', 'closable'],
  emits: ['close', 'edit', 'resetPassword', 'revoke2fa', 'logoutAll', 'changePassword'],
  watch: {
    user: function (val, old) {
      this.resetSessions();
      this.fetchSessions();
    },
  },
  computed: {
    permissions() {
      return [
        {
          value: this.user.view_usernames,
          label: this.user.view_usernames ? this.translations.canViewUsernames_ : this.translations.cannotViewUsernames_
        },
        {
          value: this.user.view_simple_history,
          label: this.user.view_simple_history ? this.translations.canViewSimpleHistory_ : this.translations.cannotViewSimpleHistory_
        },
        {
          value: this.user.view_full_history,
          label: this.user.view_full_history ? this.translations.canViewFullHistory_ : this.translations.cannotViewFullHistory_
        },
        {
          value: this.user.can_edit_locations,
          label: this.user.can_edit_locations ? this.translations.canEditLocations_ : this.translations.cannotEditLocations_
        },
        {
          value: this.user.can_export,
          label: this.user.can_export ? this.translations.canExport_ : this.translations.cannotExport_
        },
        {
          value: this.user.can_self_assign,
          label: this.user.can_self_assign ? this.translations.canSelfAssign_ : this.translations.cannotSelfAssign_
        }
      ];
    }
  },
  mounted() {
    this.fetchSessions();
  },

  methods: {
    resetSessions() {
      this.sessions = [];
      this.page = 1;
      this.more = true;
    },

    fetchSessions(page = this.page, perPage = this.perPage) {
      if (!this.more) return;

      axios
        .get(`/admin/api/user/${this.user.id}/sessions`, {
          params: {
            page: page,
            per_page: perPage,
          },
        })
        .then((response) => {
          if (response.data.items.length) {
            this.sessions = this.sessions.concat(response.data.items);
            this.page++;
            this.more = response.data.more;
          } else {
            this.more = false;
          }
        })
        .catch((err) => {
          if (err.response && err.response.status === 401) {
            alert(this.translations.loggedOut_);
            window.location.href = '/login'; // Redirect to login page
          } else {
            console.error('Error fetching sessions', err);
          }
        });
    },

    openLogoutSessionDialog(id) {
      this.$root.$confirm({
        title: translations.youreAboutToEndThisSession_,
        message: `${translations.afterThisActionTheUserWillBeSignedOut_}\r\n\r\n${translations.doYouWantToContinue_}`,
        acceptProps: { text: translations.endSession_, color: 'error' },
        dialogProps: { width: 780 },
        onAccept: () => {
          axios
            .delete('/admin/api/session/logout', {
              data: { sessid: id },
            })
            .then((response) => {
              console.log('Logged out session');
              if (response.data.redirect) {
                window.location.href = '/';
              } else {
                this.resetSessions();
                this.fetchSessions();
              }
            })
            .catch((err) => {
              console.error('Error logging out session', err);
            });
        },
      });
    },
  },

  data: function () {
    return {
      translations: window.translations,
      show: false,
      sessions: [],
      page: 1,
      perPage: 5,
      more: true,
    };
  },

  template: `
      <v-card class="mx-auto">
        <v-sheet class="px-6 py-5 d-flex align-center">
          <v-toolbar-title>
            <div class="d-flex justify-space-between ga-2 align-center">
              <div class="d-flex flex-column">
                <div class="d-flex align-center ga-2">
                  {{ user.name }}
      
                  <v-chip color="primary">
                    <v-icon size="x-large">mdi-identifier</v-icon>
                    {{ user.id }}
                  </v-chip>
  
                  <v-chip :color="user.active ? 'success' : null">
                    <v-icon class="mr-1" size="x-large">{{ user.active ? 'mdi-account-check' : 'mdi-account-cancel'}}</v-icon>
                    {{ user.active ? translations.active_ : translations.inactive_ }}
                  </v-chip>
                </div>
    
                <div>
                  <v-chip prepend-icon="mdi-account-circle-outline" variant="plain" class="text-body-2">
                    {{ user.username }}
                  </v-chip>
      
                  <v-chip v-if="user.email" prepend-icon="mdi-email-outline" variant="plain" class="text-body-2">
                    {{ user.email }}
                  </v-chip>
                </div>
              </div>

              <v-chip
                v-if="user.force_reset"
                color="error"
                variant="text"
                class="font-weight-medium"
              >
                <v-icon size="x-large">mdi-exclamation</v-icon>
                {{ translations.passwordResetRequested_ }}
              </v-chip>
  
              <div class="d-flex justify-space-between ga-2 align-center">
                <v-tooltip
                  location="bottom"
                  :text="user.force_reset ? translations.passwordResetAlreadyRequested_ : translations.forcePasswordReset_"
                >
                  <template #activator="{props}">
                    <div v-bind="props">
                      <v-btn
                        :disabled="user.force_reset != null"
                        color="error"
                        density="comfortable"
                        icon="mdi-lock-reset"
                        @click="$emit('resetPassword', user)"
                      ></v-btn>
                    </div>
                  </template>
                </v-tooltip>

                <v-tooltip
                  location="bottom"
                  :text="translations.changePassword_"
                >
                  <template #activator="{props}">
                    <div v-bind="props">
                      <v-btn
                        :disabled="user.force_reset != null"
                        color="warning"
                        density="comfortable"
                        icon="mdi-form-textbox-password"
                        @click="$emit('changePassword', user)"
                      ></v-btn>
                    </div>
                  </template>
                </v-tooltip>

                <v-tooltip
                  v-if="user.two_factor_devices && user.two_factor_devices.length > 0"
                  location="bottom"
                  :text="translations.revoke2fa_"
                >
                  <template #activator="{props}">
                    <div v-bind="props">
                      <v-btn
                        
                        @click.stop="$emit('revoke2fa', user.id)"
                        variant="outlined"
                        color="warning"
                        density="comfortable"
                        icon="mdi-lock-remove"
                      ></v-btn>
                    </div>
                  </template>
                </v-tooltip>

                <v-tooltip
                  location="bottom"
                  :text="translations.editUser_"
                >
                  <template #activator="{props}">
                    <div v-bind="props">
                      <v-btn
                        variant="outlined"
                        density="comfortable"
                        icon="mdi-pencil"
                        @click="$emit('edit', user)"
                      ></v-btn>
                    </div>
                  </template>
                </v-tooltip>

                <v-btn v-if="closable" size="small" variant="flat" icon="mdi-close" @click="$emit('close')"></v-btn>
              </div>
            </div>
          </v-toolbar-title>
        </v-sheet>
        <v-divider></v-divider>

        <v-card variant="flat">
          <v-card-text class="px-6">
            <v-row>
              <v-col cols="12" md="6">
                <div class="mb-3 text-body-1">{{ translations.userRole_ }}</div>
                <div class="d-flex flex-wrap ga-3">
                  <toggle-button
                    v-for="(role, index) in user.roles"
                    :key="index"
                    read-only
                    hide-icon
                    :model-value="true"
                  >
                    {{ role.name }}
                  </toggle-button>
                </div>
              </v-col>
              <v-col cols="12" md="6">
                <div class="mb-3 text-body-1">{{ translations.twoFactorAuthentication_ }}</div>
                <div class="d-flex flex-wrap ga-3">
                  <div
                    v-if="user?.two_factor_devices?.length > 0"
                    class="d-flex flex-column ga-2 font-weight-medium text-success"
                  >
                    <div
                      v-for="device in user.two_factor_devices"
                      :key="device.id"
                      class="d-flex align-center ga-2"
                    >
                      <v-icon
                        :icon="device.type === 'authenticator' ? 'mdi-lock-clock' : 'mdi-usb-flash-drive'"
                        color="success"
                        size="small"
                      />
                      {{ device.name }}
                    </div>
                  </div>

                  <div
                    v-else
                    class="d-flex align-center ga-2 font-weight-medium text-warning"
                  >
                    <v-icon color="warning" size="small">mdi-lock-open-alert</v-icon>
                    {{ translations.noTwoFactorMethods_ }}
                  </div>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <v-card variant="flat">
          <v-card-text class="px-6">
            <div class="mb-3 text-body-1">{{ translations.userPermissions_ }}</div>
            <div class="d-flex flex-wrap ga-3">
              <toggle-button
                v-for="(permission, index) in permissions"
                :key="index"
                read-only
                :model-value="permission.value"
              >
                {{ permission.label }}
              </toggle-button>
            </div>
          </v-card-text>
        </v-card>

        <v-card class="mt-2" variant="flat">
          <v-card-text class="px-6">
            <div class="d-flex justify-space-between align-center mb-2">
              <div class="text-body-1">{{ translations.userSessions_ }}</div>
              <v-btn
                v-if="sessions.length"
                @click.stop="$emit('logoutAll', user.id)"
                variant="outlined"
                prepend-icon="mdi-logout"
                color="error"
              >
                {{ translations.logoutAll_ }}
              </v-btn>
            </div>

            <v-table fluid>
              <thead>
              <tr>
                <th class="text-left">{{ translations.session_ }}</th>
                <th class="text-left">{{ translations.ip_ }}</th>
                <th class="text-left">{{ translations.userAgent_ }}</th>
                <th class="text-left">{{ translations.started_ }}</th>
                <th class="text-left">{{ translations.logOffThisDevice_ }}</th>
              </tr>
              </thead>
              <tbody>
              <tr v-for="session in sessions"
                  
                  :class="session.active ? 'bg-yellow-lighten-5':'' ">
                <td>
                  
                  <v-tooltip v-if="session.details?._fresh">
                    <template #activator="{ props }">
                      <v-icon v-bind="props" color="green">
                        mdi-circle
                      </v-icon>
                    </template>
                    {{ translations.active_ }}
                  </v-tooltip>

                  <v-tooltip v-else>
                    <template #activator="{ props }">
                      <v-icon color="grey-darken-5" v-bind="props">mdi-circle</v-icon>
                    </template>
                    {{ translations.inactive_ }}
                  </v-tooltip>


                </td>
                <td>
                  <v-chip label>{{ session.ip_address }}</v-chip>
                </td>
                <td class="text-caption">
                  {{ session.meta.device }}
                </td>
                <td class="text-caption">{{ $root.formatDate(session.created_at, $root.dateFormats.standardDatetime, $root.dateOptions.local) }}</td>
                <td>
                  <v-btn
                    icon="mdi-logout"
                    variant="plain" v-if="session.details?._fresh"
                    @click.once="openLogoutSessionDialog(session.id)" :disabled="!session.is_active"
                    color="error"
                  ></v-btn>
                </td>
              </tr>
              </tbody>
            </v-table>
          </v-card-text>
          <v-card-text class="text-center">
            <v-btn variant="outlined" v-if="more" @click="fetchSessions(page, perPage)">{{ translations.loadMore_ }}</v-btn>
          </v-card-text>
        </v-card>
      </v-card>
    `,
});
