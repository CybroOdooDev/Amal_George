import { ControlButtons } from "@point_of_sale/app/screens/product_screen/control_buttons/control_buttons";
import { patch } from "@web/core/utils/patch";
import { BookingPopup } from "@pos_kitchen_display/pos/booking_popup/booking_popup";
import { AlertDialog } from "@web/core/confirmation_dialog/confirmation_dialog";
import { _t } from "@web/core/l10n/translation";

patch(ControlButtons.prototype, {
    async clickBooking() {
        this.dialog.closeAll();
        if (!this.partner) {
            this.dialog.add(AlertDialog, {
                title: _t("Customer Required"),
                body: _t("Please select a customer before booking."),
            });
            return;
        }
        await this.dialog.add(BookingPopup, {});
    },
    async clickViewBookings() {
        this.dialog.closeAll();
        window.location.href = '/odoo/action-pos_kitchen_display.action_restaurant_booking_display_client';
    }
});

