import { registry } from "@web/core/registry";
import { Component, onWillStart, proxy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";

class SalonDashboard extends Component {
    static template = "salon_management_saas.SalonDashboard";
    static props = ["*"];

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.state = proxy({
            today_bookings: 0,
            monthly_revenue: 0,
            active_chairs: 0,
            vip_bookings: [],
        });

        onWillStart(async () => {
            await this.loadData();
        });
    }

    async loadData() {
        try {
            const today = new Date().toISOString().split("T")[0];

            const todayCount = await this.orm.searchCount("x_appointment", [
                ["x_studio_date", "=", today],
                ["x_studio_selection_1", "=", "Confirmed"],
            ]);

            const startOfMonth = new Date();
            startOfMonth.setDate(1);
            const startOfMonthStr = startOfMonth.toISOString().split("T")[0];
            const monthlyRevenueGroup = await this.orm.readGroup(
                "x_appointment",
                [
                    ["x_studio_date", ">=", startOfMonthStr],
                    ["x_studio_selection_1", "=", "Confirmed"],
                ],
                ["x_studio_value:sum"],
                []
            );
            const monthlyRevenue = monthlyRevenueGroup[0] && monthlyRevenueGroup[0].x_studio_value
                ? monthlyRevenueGroup[0].x_studio_value
                : 0;

            const activeChairs = await this.orm.searchCount("x_chair", []);

            const vipBookings = await this.orm.searchRead(
                "x_appointment",
                [["x_studio_value", ">", 0]],
                ["x_name", "x_studio_partner_id", "x_studio_time_slot", "x_studio_chair_num", "x_studio_value"],
                { limit: 5, order: "x_studio_value desc" }
            );

            this.state.today_bookings = todayCount;
            this.state.monthly_revenue = monthlyRevenue;
            this.state.active_chairs = activeChairs;
            this.state.vip_bookings = vipBookings;
        } catch (e) {
            console.error("[SalonDashboard] Failed to load dashboard data", e);
        }
    }
}

registry.category("actions").add("salon_dashboard_client_action", SalonDashboard);
