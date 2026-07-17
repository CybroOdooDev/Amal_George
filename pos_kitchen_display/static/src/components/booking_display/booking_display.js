/** @odoo-module **/
import { Component, useState, onWillStart } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { standardActionServiceProps } from "@web/webclient/actions/action_service";
import { _t } from "@web/core/l10n/translation";

class BookingDisplay extends Component {
    static props = { ...standardActionServiceProps };
    static template = "pos_kitchen_display.BookingDisplay";

    setup() {
        super.setup();
        this.orm = useService("orm");
        this.notification = useService("notification");
        
        const urlParams = new URLSearchParams(window.location.search);
        let configId = urlParams.get("config_id");
        if (configId) {
            sessionStorage.setItem("pos_booking_config_id", configId);
        } else {
            configId = sessionStorage.getItem("pos_booking_config_id");
        }
        this.configId = configId ? parseInt(configId) : null;

        this.state = useState({
            bookings: [],
            isLoaded: false,
            currentTab: 'pending',
        });

        onWillStart(async () => {
            await this.loadBookings();
        });
    }

    async loadBookings() {
        try {
            const domain = [["state", "=", this.state.currentTab]];
            if (this.configId) {
                domain.push(["config_id", "=", this.configId]);
            }
            const records = await this.orm.searchRead(
                "restaurant.booking",
                domain,
                ["partner_id", "phone", "booking_date", "table_id", "guests", "shop_name"]
            );
            
            if (records && records.length > 0) {
                const bookingIds = records.map(rec => rec.id);
                const lines = await this.orm.searchRead(
                    "restaurant.booking.line",
                    [["booking_id", "in", bookingIds]],
                    ["booking_id", "product_id", "qty"]
                );

                const linesByBookingId = {};
                lines.forEach(line => {
                    const bId = line.booking_id[0];
                    if (!linesByBookingId[bId]) {
                        linesByBookingId[bId] = [];
                    }
                    linesByBookingId[bId].push({
                        product_name: line.product_id[1],
                        qty: line.qty
                    });
                });

                this.state.bookings = records.map(rec => {
                    return {
                        id: rec.id,
                        customer_name: rec.partner_id[1],
                        phone: rec.phone,
                        booking_date: rec.booking_date,
                        table_name: rec.table_id[1] || _t("None"),
                        shop_name: rec.shop_name || "",
                        guests: rec.guests,
                        items: linesByBookingId[rec.id] || []
                    };
                });
            } else {
                this.state.bookings = [];
            }
        } catch (error) {
            console.error("Failed to load bookings:", error);
            this.state.bookings = [];
        } finally {
            this.state.isLoaded = true;
        }
    }

    async switchTab(tab) {
        this.state.currentTab = tab;
        this.state.isLoaded = false;
        await this.loadBookings();
    }

    async confirmBooking(booking) {
        try {
            await this.orm.call("restaurant.booking", "action_confirm", [booking.id]);
            this.notification.add(`Booking for ${booking.customer_name} confirmed!`, {
                type: "success",
            });
            await this.loadBookings();
        } catch (e) {
            console.error("Failed to confirm booking:", e);
        }
    }

    async cancelBooking(booking) {
        try {
            await this.orm.call("restaurant.booking", "action_cancel", [booking.id]);
            this.notification.add(`Booking for ${booking.customer_name} cancelled.`, {
                type: "warning",
            });
            await this.loadBookings();
        } catch (e) {
            console.error("Failed to cancel booking:", e);
        }
    }

    closeDisplay() {
        window.location.href = '/odoo/point-of-sale';
    }
}

registry.category("actions").add("pos_kitchen_display.booking_display", BookingDisplay);
