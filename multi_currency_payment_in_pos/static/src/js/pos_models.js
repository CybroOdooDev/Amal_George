/** @odoo-module */
/** Loading all currencies and its parameters.*/
import { patch } from "@web/core/utils/patch";
import { PosStore } from "@point_of_sale/app/services/pos_store";

/**
 * Patch PosStore to process configuration settings and ensure
 * multi-currency payment attributes are synchronized on order validation.
 */
patch(PosStore.prototype, {
    /**
     * Process data received from server on POS startup.
     *
     * @override
     * @param {Object} data - Server data payload.
     */
    async processServerData(data) {
        await super.processServerData(...arguments);
        this.res_settings = this.data.models["res.config.settings"]?.getFirst?.();
    },

    /**
     * Ensure multi-currency values are assigned to payment lines before order validation.
     *
     * @override
     * @param {Object} [args={}] - Order validation options.
     * @returns {Promise<any>}
     */
    async validateOrder(args = {}) {
        const order = args.order || this.getOrder();
        if (order && order.payment_ids) {
            order.payment_ids.forEach((line) => {
                if (line.converted_currency) {
                    const cName = line.converted_currency.name;
                    const cAmount = line.converted_currency.amount;
                    line.payment_currency = cName;
                    line.currency_amount = cAmount;
                    line.update?.({
                        payment_currency: cName,
                        currency_amount: cAmount,
                    });
                }
            });
        }
        return await super.validateOrder(...arguments);
    },
});
