const actionSections = () => ({
  suspend: {
    title: (name) => window.translations.youAreAboutToSuspendTheAccountForUser_(name),
    confirmationText: (name) => window.translations.byEnteringUsernameYouConfirmSuspendForUser_(name),
    acceptButtonText: window.translations.suspendAccount_,
    acceptButtonColor: "warning",
    confirmationType: 'username',
    blocks: [
      {
        icon: "mdi-account-circle",
        title: window.translations.intendedFor_,
        description: window.translations.temporarySuspensionsInternalInvestigationsOrOnLeave_,
      },
      {
        icon: "mdi-account-key",
        title: window.translations.rolesAndAccessRemoval_,
        bullets: [
          window.translations.userCanNoLongerLoginToBayanat_,
          window.translations.rolesAccessAndAssignmentsRemainUnchanged_,
        ],
      },
    ],
  },
  reactivate: {
    title: (name) => window.translations.youAreAboutToReactivateUser_(name),
    confirmationText: (name) => window.translations.byEnteringYourPasswordYouConfirmReactivationForUser_(name),
    acceptButtonText: window.translations.reactivateAccount_,
    acceptButtonColor: "success",
    confirmationType: 'password',
    blocks: [
      {
        icon: "mdi-account",
        title: window.translations.rolesAndAccessRestoration_,
        bullets: [
          window.translations.previousRolesAndAccessPermissionsWillBeRestored_,
          window.translations.userCanLoginAndPerformRoleActions_,
        ],
      },
      {
        icon: "mdi-key",
        title: window.translations.profileAndContributions_,
        bullets: [
          window.translations.theUserWillBeAbleToViewAndEditItemsTheyPreviouslyHadAccessTo_,
        ],
      },
    ],
  },
  disable: {
    title: (name) => window.translations.youAreAboutToDisableTheAccountForUser_(name),
    confirmationText: (name) => window.translations.byEnteringUsernameYouConfirmDisableForUser_(name),
    acceptButtonText: window.translations.disableAccount_,
    acceptButtonColor: "error",
    confirmationType: 'username',
    blocks: [
      {
        icon: "mdi-account-circle",
        title: window.translations.intendedFor_,
        description: window.translations.permanentlyEndingUserAccessToBayanat_,
      },
      {
        icon: "mdi-account-key",
        title: window.translations.accessRemoval_,
        bullets: [window.translations.userCanNoLongerLoginToBayanat_],
      },
      {
        icon: "mdi-briefcase-clock-outline",
        title: window.translations.profileAndContributions_,
        bullets: [
          window.translations.userProfileRetainedForArchivalPurposes_,
          window.translations.itemsCreatedOrUpdatedByUserWillRemainInBayanat_,
          window.translations.activityHistoryWillContinueToReflectUserContributions_,
        ],
      },
    ],
  },
  enable: {
    title: (name) => window.translations.youAreAboutToEnableTheAccountForUser_(name),
    confirmationText: (name) => window.translations.byEnteringYourPasswordYouConfirmEnablingTheAccountForUser_(name),
    acceptButtonText: window.translations.enableAccount_,
    acceptButtonColor: "success",
    confirmationType: 'password',
    blocks: [
      {
        icon: "mdi-account",
        title: window.translations.accessRestoration_,
        bullets: [window.translations.userCanUseExistingPasswordToAccessBayanat_],
      },
      {
        icon: "mdi-key",
        title: window.translations.profileAndContributions_,
        bullets: [window.translations.previousProfileAndContributionsRemainIntact_],
      },
    ],
  },
});

const UserCard = Vue.defineComponent({
  props: ['user', 'closable'],
  emits: ['close', 'edit', 'resetPassword', 'revoke2fa', 'logoutAll', 'changePassword', 'showHistory'],
  components: { ConfirmDialog },
  data() {
    return {
      translations: window.translations,
      show: false,
      sessions: [],
      page: 1,
      perPage: 5,
      more: true,
      username: '',
      password: '',
      showPassword: false,
    };
  },
  computed: {
    logAllowed() {
      return this.$root.currentUser.view_simple_history;
    },
    actionSections() {
      return actionSections();
    },
    isUserActive() {
      return this.user?.status === 'active';
    },
    isUserSuspended() {
      return this.user?.status === 'suspended';
    },
    isUserDisabled() {
      return this.user?.status === 'disabled';
    },
    isUserEnabled() {
      return !this.isUserDisabled;
    },
    permissions() {
      // [permissionKey, translationIfAllowed, translationIfDenied]
      const rows = [
        ['view_usernames', 'canViewUsernames_', 'cannotViewUsernames_'],
        ['view_simple_history', 'canViewSimpleHistory_', 'cannotViewSimpleHistory_'],
        ['view_full_history', 'canViewFullHistory_', 'cannotViewFullHistory_'],
        ['can_edit_locations', 'canEditLocations_', 'cannotEditLocations_'],
        ['can_export', 'canExport_', 'cannotExport_'],
        ['can_self_assign', 'canSelfAssign_', 'cannotSelfAssign_'],
      ];

      return rows.map(([key, yes, no]) => ({
        value: this.user[key],
        label: this.user[key] ? this.translations[yes] : this.translations[no],
      }));
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
    getTwoFactorDeviceMeta(device) {
      return { icon: device.type === 'authenticator' ? 'mdi-lock-clock' : 'mdi-usb-flash-drive', color: 'success', text: device.name };
    },
    displayAccountStatusUpdatedMessage(action) {
      switch (action) {
        case 'suspend':
          return this.$root.showSnack(this.translations.userHasBeenSuspended_(this.user.name));
        case 'reactivate':
          return this.$root.showSnack(this.translations.userHasBeenReactivated_(this.user.name));
        case 'enable':
          return this.$root.showSnack(this.translations.userHasBeenEnabled_(this.user.name));
        case 'disable':
          return this.$root.showSnack(this.translations.userHasBeenDisabled_(this.user.name));
      }
    },
    openAccountDialog(mode) {
      this.$refs.accountActionDialog.show({
        dialogProps: { width: 691 },
        data: { mode },
        acceptProps: { text: this.actionSections[mode].acceptButtonText, color: this.actionSections[mode].acceptButtonColor },
        onAccept: async () => {
          const payload = {};
          if (this.actionSections[mode].confirmationType === 'password') {
            payload.password = this.password;
          }
          await api.post(`/admin/api/user/${this.user.id}/${mode}`, payload);
          await this.$root.refreshUser(this.user.id);
          this.username = '';
          this.password = '';
          this.showPassword = false;
          this.displayAccountStatusUpdatedMessage(mode);
        },
        onReject: () => {
          this.username = '';
          this.password = '';
          this.showPassword = false;
        }
      })
    },

    suspendAccount() {
      this.openAccountDialog("suspend");
    },
    disableAccount() {
      this.openAccountDialog("disable");
    },
    reactivateAccount() {
      this.openAccountDialog("reactivate");
    },
    enableAccount() {
      this.openAccountDialog("enable");
    },
    parseUserAgent(ua) {
      const uaLower = ua.toLowerCase();

      // ---- Device ----
      let device = 'desktop';
      if (/mobile|iphone|android|ipad/.test(uaLower)) {
        device = /ipad/.test(uaLower) ? 'tablet' : 'mobile';
      }

      // ---- OS ----
      let os = 'unknown';
      if (/mac os x/.test(uaLower)) os = 'macos';
      else if (/windows nt/.test(uaLower)) os = 'windows';
      else if (/android/.test(uaLower)) os = 'android';
      else if (/iphone|ipad|ipod/.test(uaLower)) os = 'ios';
      else if (/linux/.test(uaLower)) os = 'linux';

      // ---- Browser (family, not flavor) ----
      let browser = 'unknown';
      if (uaLower.includes('firefox')) {
        browser = 'firefox';
      } else if (
        /safari/.test(uaLower) &&
        !uaLower.includes('chrome') &&
        !uaLower.includes('crios') &&
        !uaLower.includes('fxios')
      ) {
        browser = 'safari';
      } else if (uaLower.includes('chrome') || uaLower.includes('chromium')) {
        browser = 'chrome'; // Chrome, Brave, Edge, Opera
      }

      // ---- Display label ----
      const OS_LABEL = {
        macos: 'Mac',
        windows: 'Windows',
        linux: 'Linux',
        ios: 'iPhone',
        android: 'Android',
        unknown: window.translations.unknownOS_
      };

      const BROWSER_LABEL = {
        chrome: 'Chrome',
        firefox: 'Firefox',
        safari: 'Safari',
        unknown: window.translations.unknownBrowser_
      };

      const DEVICE_LABEL = {
        desktop: window.translations.desktop_,
        mobile: window.translations.mobile_,
        tablet: window.translations.tablet_
      };

      return {
        deviceLabel: `${OS_LABEL[os]} (${DEVICE_LABEL[device]})`,
        device,   // desktop | mobile | tablet
        os,       // macos | windows | linux | ios | android
        browser,  // chrome | firefox | safari
        browserLabel: BROWSER_LABEL[browser]
      };
    }
  },
  watch: {
    user(val, old) {
      this.resetSessions();
      this.fetchSessions();
    },
  },
  template: `
      <confirm-dialog ref="accountActionDialog" :disabled-accept="username !== user.username && !password">
        <template #title="{ data }">
          {{ actionSections[data?.mode]?.title(user.name) }}
        </template>
        <template #default="{ data }">
          <div class="text-body-2 mb-6 mt-3">{{ translations.whatYouShouldKnow_ }}</div>
          <div class="d-flex flex-column ga-6">
            <div v-for="(block, index) in actionSections[data?.mode]?.blocks" :key="index" class="d-flex">
              <v-avatar color="white">
                <v-icon color="primary" size="x-large">{{ block.icon }}</v-icon>
              </v-avatar>
    
              <div class="ml-3">
                <h4 class="text-primary">{{ block.title }}</h4>
                <div v-if="block?.description" class="text-body-2">{{ block.description }}</div>
                <ul v-if="block?.bullets" class="text-body-2 pl-5">
                  <li v-for="(bullet, index) in block.bullets" :key="index">{{ bullet }}</li>
                </ul>
              </div>
            </div>
          </div>
          <div class="text-body-2 mt-6">
            {{ actionSections[data?.mode]?.confirmationText(user.username) }}
            <v-text-field
              v-if="actionSections[data?.mode]?.confirmationType === 'username'"
              v-model="username"
              :label="translations.enterUsernameToConfirm_"
              variant="filled"
              class="mt-3"
            ></v-text-field>
            <v-text-field
              v-else
              v-model="password"
              :label="translations.confirmWithYourPassword_"
              variant="filled"
              class="mt-3"
              :append-inner-icon="showPassword ? 'mdi-eye' : 'mdi-eye-off'"
              :type="showPassword ? 'text' : 'password'"
              @click:append-inner="showPassword = !showPassword"
            ></v-text-field>
          </div>
        </template>
      </confirm-dialog>

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
  
                  <v-chip :color="$root.getUserStatusMeta(user)?.color">
                    <v-icon class="mr-1" size="x-large">{{ $root.getUserStatusMeta(user)?.icon }}</v-icon>
                    {{ $root.getUserStatusMeta(user)?.text }}
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

              <template v-if="$root.userId !== user.id">
                <v-chip
                  v-if="user.force_reset && isUserEnabled"
                  color="error"
                  variant="text"
                  class="font-weight-medium"
                >
                  <v-icon size="x-large">mdi-exclamation</v-icon>
                  {{ translations.passwordResetRequested_ }}
                </v-chip>
              </template>
  
              <div class="d-flex justify-space-between ga-2 align-center">
                <v-tooltip
                  v-if="logAllowed"
                  location="bottom"
                  :text="translations.revisionHistory_"
                >
                  <template #activator="{props}">
                    <div v-bind="props">
                      <v-btn
                        density="comfortable"
                        icon="mdi-history"
                        @click="$emit('showHistory', user)"
                      ></v-btn>
                    </div>
                  </template>
                </v-tooltip>

                <template v-if="isUserEnabled">
                  <template v-if="$root.userId !== user.id">
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
                  </template>

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
                </template>

                <v-btn v-if="closable" size="small" variant="flat" icon="mdi-close" @click="$emit('close')"></v-btn>
              </div>
            </div>
          </v-toolbar-title>
        </v-sheet>
        <v-divider></v-divider>

        <v-card v-if="isUserEnabled" variant="flat">
          <v-card-text class="px-6">
            <v-row>
              <v-col cols="12" sm="6" md="4">
                <div class="mb-3 text-body-1">{{ translations.systemRole_ }}</div>
                <div v-if="$root.userSystemRoles.length" class="d-flex flex-wrap ga-3">
                  <toggle-button
                    v-for="(role, index) in $root.userSystemRoles"
                    :key="index"
                    read-only
                    hide-left-icon
                    :model-value="true"
                    rounded="xl"
                  >
                    {{ $root.systemRoles.find(r => r.value === role.name.toLowerCase())?.name ?? role.name }}
                  </toggle-button>
                </div>
                <v-btn v-else @click="$emit('edit', user)" variant="plain" class="d-flex align-center text-disabled" style="padding: 0;">
                  <v-icon class="mr-1">mdi-alert-circle-outline</v-icon> {{ this.translations.assignSystemRole_ }}
                </v-btn>
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <div class="mb-3 text-body-1">{{ translations.accessRole_ }}</div>
                <div v-if="$root.userAccessRoles.length" class="d-flex flex-wrap ga-3">
                  <toggle-button
                    v-for="(role, index) in $root.userAccessRoles"
                    :key="index"
                    read-only
                    hide-left-icon
                    :model-value="true"
                    rounded="xl"
                  >
                    {{ role.name }}
                  </toggle-button>
                </div>
                <v-btn v-else @click="$emit('edit', user)" variant="plain" class="d-flex align-center text-disabled" style="padding: 0;">
                  <v-icon class="mr-1">mdi-alert-circle-outline</v-icon> {{ this.translations.assignAccessRole_ }}
                </v-btn>
              </v-col>
              <v-col cols="12" sm="6" md="4">
                <div class="mb-3 text-body-1">{{ translations.twoFactorAuthentication_ }}</div>
                <div class="d-flex flex-wrap ga-3">
                  <div
                    v-if="user?.two_factor_devices?.length > 0"
                    class="d-flex flex-column ga-2 font-weight-medium text-success"
                  >
                    <v-chip v-for="device in user.two_factor_devices" :key="device.id" :color="getTwoFactorDeviceMeta(device)?.color" variant="text" class="font-weight-medium">
                      <v-icon start size="large">{{ getTwoFactorDeviceMeta(device)?.icon }}</v-icon>
                      {{ getTwoFactorDeviceMeta(device)?.text }}
                    </v-chip>
                  </div>

                  <v-chip
                    v-else
                    color="warning"
                    variant="text"
                    class="font-weight-medium"
                  >
                    <v-icon start size="large">mdi-lock-open-alert</v-icon>
                    {{ translations.twoFaInactive_ }}
                  </v-chip>
                </div>
              </v-col>
            </v-row>
          </v-card-text>
        </v-card>

        <v-card v-if="isUserEnabled" variant="flat">
          <v-card-text class="px-6">
            <div class="mb-3 text-body-1">{{ translations.userPermissions_ }}</div>
            <div v-if="permissions.some(p => p.value)" class="d-flex flex-wrap ga-3">
              <toggle-button
                v-for="(permission, index) in permissions"
                :key="index"
                read-only
                :model-value="permission.value"
              >
                {{ permission.label }}
              </toggle-button>
            </div>
            <v-btn v-else @click="$emit('edit', user)" variant="plain" class="d-flex align-center text-disabled" style="padding: 0;">
              <v-icon class="mr-1">mdi-alert-circle-outline</v-icon> {{ this.translations.assignUserPermissions_ }}
            </v-btn>
          </v-card-text>
        </v-card>

        <v-card v-if="$root.userId !== user.id" variant="flat">
          <v-card-text class="px-6">
            <div class="mb-3 text-body-1">{{ translations.manageAccount_ }}</div>
            <div class="d-flex flex-wrap ga-3">
              <template v-if="isUserEnabled">
                <v-tooltip v-if="isUserSuspended" location="bottom" :disabled="Boolean(user.roles.length)" :text="translations.pleaseAssignASystemRoleToReactivateUser_">
                    <template #activator="{ props }">
                      <div v-bind="props">
                        <v-btn :disabled="!Boolean(user.roles.length)" @click="reactivateAccount()" variant="outlined" color="success" prepend-icon="mdi-play-circle">{{ translations.reactivateAccount_ }}</v-btn>
                      </div>
                    </template>
                  </v-tooltip>
                <v-btn v-if="isUserActive" @click="suspendAccount()" variant="outlined" color="warning" prepend-icon="mdi-pause-circle">{{ translations.suspendAccount_ }}</v-btn>
              </template>
              <v-btn v-if="isUserDisabled" @click="enableAccount()" variant="outlined" color="success" prepend-icon="mdi-arrow-down-thin-circle-outline">{{ translations.enableAccount_ }}</v-btn>
              <v-btn v-if="isUserEnabled" @click="disableAccount()" variant="outlined" color="error" prepend-icon="mdi-minus-circle">{{ translations.disableAccount_ }}</v-btn>
            </div>
          </v-card-text>
        </v-card>

        <v-card v-if="isUserEnabled" class="mt-2" variant="flat">
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
                <th class="text-left">{{ translations.device_ }}</th>
                <th class="text-left">{{ translations.browser_ }}</th>
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
                <td class="text-caption">
                  {{ parseUserAgent(session.meta.device)?.deviceLabel }}
                </td>
                <td class="text-caption">
                  {{ parseUserAgent(session.meta.device)?.browserLabel }}
                </td>
                <td class="text-caption">{{ $root.formatDate(session.created_at, $root.dateFormats.standardDatetime, $root.dateOptions.local) }}</td>
                <td>
                  <v-btn
                    icon="mdi-logout"
                    variant="plain" v-if="session.details?._fresh"
                    @click="openLogoutSessionDialog(session.id)" :disabled="!session.is_active"
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
