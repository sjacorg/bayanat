const notificationMixin = {
  components: {
    'NotificationsList': NotificationsList,
  },
  computed: {
    hasUnreadNotifications() {
      return Boolean(this.notifications.unreadCount)
    },
  },
  data: () => ({
    // New state
    notifications: {
      items: null,
      importantItems: [],
      unreadCount: 0,
      total: 0,
      hasMore: false,
      pagination: {
        page: 1,
        per_page: 10
      },
      intervalId: null,
      status: {
        initialLoading: false,
        loadingMore: false,
        markingImportantAsRead: false,
        loadError: false
      },
      ui: {
        drawerVisible: false,
        dialogVisible: false,
        importantDialogVisible: false,
        dialogFullscreen: false,
        currentTab: 'all'
      }
    },
  }),

  async mounted() {
    // If user is not authenticated exit
    if (!window.__username__) return

    this.refetchNotifications(); // Initial fetch
    this.startPolling();
    document.addEventListener('visibilitychange', this.handleVisibilityChange);
  },
  beforeUnmount() {
    this.stopPolling();
    document.removeEventListener('visibilitychange', this.handleVisibilityChange);
  },

  methods: {
    handleVisibilityChange() {
        if (document.visibilityState === 'visible') {
            this.refetchNotifications(); // Fetch immediately on becoming visible
            this.startPolling();
        } else {
            this.stopPolling();
        }
    },
    startPolling() {
        if (this.notifications.intervalId) return; // Prevent multiple intervals
        this.notifications.intervalId = setInterval(this.refetchNotifications, 60000);
    },
    stopPolling() {
        clearInterval(this.notifications.intervalId);
        this.notifications.intervalId = null;
    },
    async markAsReadImportantNotifications() {
      try {
        this.notifications.status.markingImportantAsRead = true;
        await Promise.all(this.notifications.importantItems.map(async notification => {
          await this.readNotification(notification)
        }))
      } catch (error) {
        console.error(error);
        this.showSnack(handleRequestError(error))
      } finally {
        this.notifications.status.markingImportantAsRead = false;
        this.notifications.ui.importantDialogVisible = false;
      }
    },
    toggleNotificationsDialog() {
      // Toggle the notifications dialog
      this.notifications.ui.dialogVisible = !this.notifications.ui.dialogVisible;

      // Close the settings dialog if the notifications dialog is open
      if (this.notifications.ui.dialogVisible) {
        this.settingsDrawer = false;
        this.notifications.ui.drawerVisible = false;

        // Load notifications if not already loaded
        if (!this.notifications.items) {
          this.loadNotifications({ page: 1 });
        }
      }
    },
    toggleNotificationsDrawer() {
      // Toggle the notifications drawer
      this.notifications.ui.drawerVisible = !this.notifications.ui.drawerVisible;

      // Close the settings drawer if the notifications drawer is open
      if (this.notifications.ui.drawerVisible) {
        this.settingsDrawer = false;

        // Load notifications if not already loaded
        if (!this.notifications.items) {
          this.loadNotifications({ page: 1 });
        }
      }
    },
    async loadImportantNotifications() {
      try {
        if (this.notifications.ui.importantDialogVisible) return;

        // Construct query parameters
        const response = await axios.get(`/admin/api/notifications?is_urgent=true&status=unread&per_page=30`);

        if (response?.data?.items?.length) {
          this.notifications.importantItems = response.data.items;
          this.notifications.ui.importantDialogVisible = true;
          this.notifications.status.loadError = false;
        }

        return response
      } catch (error) {
        const errorMessage = error?.response?.data?.message || error.message || "Failed to load notifications";
        this.showSnack(errorMessage);
        this.notifications.status.loadError = true;
      }
    },
    async loadNotifications(options) {
      const isFirstPage = options?.page === 1;
      const status = this.notifications.status;

      if (status.isLoadingMore || status.isLoadingInitial) return;

      try {
        // Set loading flags
        if (isFirstPage) {
          status.isLoadingInitial = true;
          this.notifications.pagination = {
            page: 1,
            per_page: 10
          }
        } else {
          status.isLoadingMore = true;
        }

        const query = {
          ...this.notifications.pagination,
          ...options,
        };

        if (this.notifications.ui.currentTab !== 'all') {
          query.status = this.notifications.ui.currentTab;
        }

        const queryParams = new URLSearchParams(query);
        const { data } = await axios.get(`/admin/api/notifications?${queryParams.toString()}`);

        if (!data) return;

        if (isFirstPage) {
          this.notifications.items = [];
          this.notifications.hasMore = false;
        }

        const {
          items: newItems = [],
          total = 0,
          hasMore = false,
          unreadCount = 0,
          hasUnreadUrgentNotifications = false
        } = data;

        this.notifications.unreadCount = unreadCount;

        if (hasUnreadUrgentNotifications) {
          this.loadImportantNotifications();
        }

        this.notifications.items = [...(this.notifications.items || []), ...newItems];

        if (this.notifications.ui.currentTab === 'all') {
          this.notifications.total = total;
        }

        this.notifications.hasMore = hasMore;

        if (hasMore) {
          this.notifications.pagination.page += 1;
        }

        status.hasLoadError = false;
      } catch (error) {
        console.error(error);
        this.showSnack(error?.response?.data?.message || error.message || "Failed to load notifications");
        status.hasLoadError = true;
      } finally {
        status.isLoadingInitial = false;
        status.isLoadingMore = false;
      }
    },
    async readNotification(notification) {
      if (!notification?.id || notification.read_status) return;
    
      const setReadStatusMatchingNotification = (list, isRead) => {
        const match = list?.find(n => n.id === notification.id);
        if (match) match.read_status = isRead;
        return Boolean(match);
      };
    
      const updatedInList = setReadStatusMatchingNotification(this.notifications.items, true);
      const updatedInImportant = setReadStatusMatchingNotification(this.notifications.importantItems, true);
    
      const unreadWasDecremented = updatedInList || updatedInImportant;
      const previousUnreadCount = this.notifications.unreadCount;
    
      if (unreadWasDecremented) this.decrementNotificationsCount();
    
      try {
        await axios.post(`/admin/api/notifications/${notification.id}/read`);
      } catch (error) {
        console.error(error);
        this.showSnack(handleRequestError(error));
    
        // Revert state if request failed
        setReadStatusMatchingNotification(this.notifications.items, false);
        setReadStatusMatchingNotification(this.notifications.importantItems, false);
        this.notifications.unreadCount = previousUnreadCount;
      }
    },    
    async refetchNotifications() {
      this.loadNotifications({ page: 1 });
    },
    decrementNotificationsCount() {
      if (this.notifications.unreadCount > 0) {
        this.notifications.unreadCount -= 1;
      }
    }
  },
  watch: {
    'notifications.ui.currentTab'() {
      this.loadNotifications({ page: 1 });
    }
  },
};
