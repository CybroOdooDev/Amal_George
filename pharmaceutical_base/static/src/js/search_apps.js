/** @odoo-module */

import { NavBar } from "@web/webclient/navbar/navbar";
import { computeAppsAndMenuItems } from "@web/webclient/menus/menu_helpers";
import { useBus, useService } from "@web/core/utils/hooks";
import { useRef, onMounted, useEffect } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";

patch(NavBar.prototype, {
    setup() {
        super.setup()
        this.sidebarRef = useRef("sidebar");
        this.menu_sectionsRef = useRef("menu_sections")
        this.busService = useService("bus_service");
        const { apps } = computeAppsAndMenuItems(this.menuService.getMenuAsTree("root"));
        this._apps = apps;

        // Always start with the rail visible; it is only hidden by the toggle
        // or the home menu.
        const currentAppId = this.currentApp ? this.currentApp.id : null;
        Object.assign(this.state, {
            activeApp: currentAppId || parseInt(sessionStorage.getItem("activeApp")) || null,
            isSidebarHidden: false,
        });
        sessionStorage.setItem("isSidebarHidden", "false");

        useBus(this.env.bus, "app-selected", (event) => {
            this.onAppClick(event.detail.activeApp);
        });

        useBus(this.env.bus, "HOME-MENU:TOGGLED", () => {
            this.applySidebarState();
        });

        // Watch active app changes to update state & sidebar visibility.
        useEffect(
            () => {
                if (this.currentApp) {
                    this.state.activeApp = this.currentApp.id;
                    sessionStorage.setItem("activeApp", this.currentApp.id);
                    this.state.isSidebarHidden = false;
                    sessionStorage.setItem("isSidebarHidden", "false");
                }
                this.applySidebarState();
            },
            () => [this.currentApp?.id]
        );

        onMounted(() => {
            this.applySidebarState();
        });
    },

    applySidebarState() {
        // Only toggle the rail's visibility; the content margin is handled in CSS.
        const sidebarElement = this.sidebarRef.el;
        const sectionsElement = this.menu_sectionsRef?.el || this.appSubMenus?.el;
        if (sidebarElement) {
            const isHomeMenu = this.hm?.hasHomeMenu || document.querySelector(".app_container") !== null;
            if (this.state.isSidebarHidden || isHomeMenu) {
                sidebarElement.classList.add("o_hidden");
                sectionsElement?.classList.add("o_hidden");
            } else {
                sidebarElement.classList.remove("o_hidden");
                sectionsElement?.classList.remove("o_hidden");
            }
        }
    },

    onAppClick(app) {
        const sidebarElement = this.sidebarRef.el;
        const sectionsElement = this.menu_sectionsRef?.el || this.appSubMenus?.el;
        sidebarElement?.classList.remove("o_hidden");
        sectionsElement?.classList.remove("o_hidden");
        this.state.isSidebarHidden = false;
        sessionStorage.setItem("isSidebarHidden", "false");
        this.state.activeApp = app.id;
        sessionStorage.setItem("activeApp", this.state.activeApp);
        this.onNavBarDropdownItemSelection(app);
    },

    async _onClickMenusPanel() {
        if (this.state.isSidebarHidden) {
            const lastAppId = parseInt(sessionStorage.getItem("activeApp"));
            const lastApp = this._apps.find(app => app.id == lastAppId);
            if (lastApp) {
                this.onAppClick(lastApp);
            } else if (this._apps.length > 0) {
                this.onAppClick(this._apps[0]);
            }
            return;
        }
        const sidebarElement = this.sidebarRef.el;
        const sectionsElement = this.menu_sectionsRef?.el || this.appSubMenus?.el;
        sidebarElement?.classList.add("o_hidden");
        sectionsElement?.classList.add("o_hidden");
        this.state.isSidebarHidden = true;
        sessionStorage.setItem("isSidebarHidden", "true");
        if (this.hm) {
            await this.hm.toggle(true);
        } else {
            await this.actionService.doAction({
                type: 'ir.actions.client',
                tag: 'theme_diwy.homemenus',
                params: {
                    apps: this._apps,
                },
            });
        }
    }
})