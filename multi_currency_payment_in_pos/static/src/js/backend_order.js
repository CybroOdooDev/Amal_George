/** @odoo-module **/
import { patch } from "@web/core/utils/patch";
import { PosPayment } from "@point_of_sale/app/models/pos_payment";

/**
 * Patch for PosPayment to include converted currency information
 * when exporting payment data for receipt printing and serialization.
 */

patch(PosPayment.prototype, {
    setup(vals) {
        super.setup(...arguments);
        if (vals) {
            if (vals.payment_currency) {
                this.payment_currency = vals.payment_currency;
            }
            if (vals.currency_amount) {
                this.currency_amount = vals.currency_amount;
            }
        }
    },

    export_for_printing(baseUrl, headerData) {
        const result = super.export_for_printing ? super.export_for_printing(...arguments) : {};
        if (this.converted_currency) {
            result.converted_currency_amount = this.converted_currency.amount;
            result.converted_currency_name = this.converted_currency.name;
            result.converted_currency_symbol = this.converted_currency.symbol;
            this.currency_amount = this.converted_currency.amount;
            this.payment_currency = this.converted_currency.name;
        }
        return result;
    },
});
