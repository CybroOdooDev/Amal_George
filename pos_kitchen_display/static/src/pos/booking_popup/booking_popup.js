import { Component, useState } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";

export class BookingPopup extends Component {
    static template = "pos_kitchen_display.BookingPopup";
    static components = { Dialog };
    static props = {
        close: Function,
    };

    setup() {
        this.pos = usePos();
        this.orm = useService("orm");
        
        // Find default table
        const currentOrder = this.pos.getOrder();
        const defaultTableId = currentOrder?.table_id?.id || (this.tables[0]?.id || "");

        // Set default booking time to 1 hour from now
        const defaultDate = new Date();
        defaultDate.setHours(defaultDate.getHours() + 1);
        const tzoffset = (new Date()).getTimezoneOffset() * 60000;
        const localISOTime = (new Date(defaultDate - tzoffset)).toISOString().slice(0, 16);

        const partner = currentOrder?.getPartner();
        const defaultPartnerId = partner ? partner.id : "";
        const defaultPartnerName = partner ? partner.name : "";
        const defaultPhone = partner ? partner.phone || partner.mobile || "" : "";

        const initialProducts = [];
        if (currentOrder && currentOrder.lines) {
            for (const line of currentOrder.lines) {
                if (line.product_id) {
                    initialProducts.push({
                        product_id: line.product_id.id,
                        product_name: line.product_id.display_name,
                        qty: Math.max(1, Math.round(line.qty)),
                    });
                }
            }
        }

        this.state = useState({
            formData: {
                partner_id: defaultPartnerId,
                partner_name: defaultPartnerName,
                phone: defaultPhone,
                table_id: defaultTableId,
                guests: 2,
                booking_date: localISOTime,
            },
            productSearchQuery: "",
            selectedProducts: initialProducts,
            errors: {},
        });
    }

    get tables() {
        return this.pos.models["restaurant.table"] ? this.pos.models["restaurant.table"].getAll() : [];
    }

    get searchedProducts() {
        const query = this.state.productSearchQuery.trim().toLowerCase();
        if (!query) return [];
        return (this.pos.models["product.product"]?.getAll() || [])
            .filter(p => p.display_name.toLowerCase().includes(query))
            .slice(0, 5);
    }

    getTableDisplay(tableId) {
        if (!tableId) return _t("None");
        const id = typeof tableId === 'object' ? tableId.id : tableId;
        const table = this.pos.models["restaurant.table"] ? this.pos.models["restaurant.table"].get(id) : null;
        if (!table) return _t("Table #") + id;
        const floorName = table.floor_id ? table.floor_id.name : "";
        return floorName ? `${floorName} - Table ${table.table_number}` : `Table ${table.table_number}`;
    }

    addProduct(product) {
        const existing = this.state.selectedProducts.find(p => p.product_id === product.id);
        if (existing) {
            existing.qty += 1;
        } else {
            this.state.selectedProducts.push({
                product_id: product.id,
                product_name: product.display_name,
                qty: 1,
            });
        }
        this.state.productSearchQuery = "";
    }

    updateQty(productId, amount) {
        const item = this.state.selectedProducts.find(p => p.product_id === productId);
        if (item) {
            item.qty = Math.max(1, item.qty + amount);
        }
    }

    removeProduct(productId) {
        this.state.selectedProducts = this.state.selectedProducts.filter(p => p.product_id !== productId);
    }

    validateForm() {
        const errors = {};
        if (!this.state.formData.booking_date) {
            errors.booking_date = _t("Booking Date & Time is required.");
        }
        if (this.state.formData.guests <= 0) {
            errors.guests = _t("Number of guests must be positive.");
        }
        this.state.errors = errors;
        return Object.keys(errors).length === 0;
    }

    async saveBooking() {
        if (!this.validateForm()) {
            return;
        }

        try {
            const localDate = new Date(this.state.formData.booking_date);
            const utcDateStr = localDate.toISOString().replace("T", " ").slice(0, 19);

            const lines = this.state.selectedProducts.map(p => [0, 0, {
                product_id: p.product_id,
                qty: p.qty,
            }]);

            await this.orm.create("restaurant.booking", [{
                config_id: this.pos.config.id,
                partner_id: parseInt(this.state.formData.partner_id) || false,
                phone: this.state.formData.phone.trim() || false,
                booking_date: utcDateStr,
                table_id: parseInt(this.state.formData.table_id) || false,
                guests: parseInt(this.state.formData.guests) || 2,
                booking_line_ids: lines,
            }]);

            this.close();
            // Redirect to the pending bookings client action screen with shop config context
            window.location.href = `/odoo/action-pos_kitchen_display.action_restaurant_booking_display_client?config_id=${this.pos.config.id}`;
        } catch (error) {
            console.error("Error creating booking:", error);
            this.state.errors = { server: _t("Failed to save booking. Please check connection.") };
        }
    }

    close() {
        this.props.close();
    }
}
