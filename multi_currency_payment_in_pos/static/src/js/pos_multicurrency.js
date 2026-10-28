/** @odoo-module **/
/** It allows users to accept payments in multiple currencies, view
 * currency conversion rates, and add payment lines in the selected currency. */
import { PaymentScreen } from "@point_of_sale/app/screens/payment_screen/payment_screen";
import { onWillStart, proxy } from "@odoo/owl";
import { patch } from "@web/core/utils/patch";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";


patch(PaymentScreen.prototype, {
    setup() {
        super.setup(...arguments);
        this.pos = usePos();
        this.orm = useService("orm");

        this.current_currency = proxy({
            rate: 1,
            display_name: '',
            symbol: '',
        });

        this.multi_currency = proxy({
            currencies: [],
            usd_val: '',
            name: '',
            total: '',
            symbol: '',
            rate: ''
        });

        onWillStart(async () => {
            if (this.pos.config.enable_multicurrency) {
                const settings = await this.orm.call(
                    'pos.config',
                    'get_config_settings',
                    [this.pos.config.id],
                    {}
                );

                if (settings && settings.length > 0) {
                    this.multi_currency.currencies = settings;
                }
            }
        });
    },

    /**
     * Toggle the visibility of the multi-currency container.
     *
     * @param {Event} event - Input change event from checkbox.
     */
    async show_options(event) {
        const isChecked = event.target.checked;
        const multiCurrencyContainer = document.getElementById("multicurrency_container");

        if (multiCurrencyContainer) {
            multiCurrencyContainer.style.display = isChecked ? "block" : "none";
        }
    },

    /**
     * Compute exchange conversion for the selected currency.
     *
     * @param {Event} event - Dropdown selection change event.
     */
    async compute_currency(event) {
        const ConvContainer = document.getElementById("conversion_container");
        const selectedCurrency = event.target.value;
        if (selectedCurrency === 'selected disabled') {
            if (ConvContainer) {
                ConvContainer.style.display = "none";
            }
            return;
        }
        const selectedId = event.target.selectedOptions[0]?.id;
        if (!selectedId) {
            if (ConvContainer) {
                ConvContainer.style.display = "none";
            }
            return;
        }

        const multiCurInput = document.getElementsByClassName("multicurrency_input")[0];

        if (ConvContainer) {
            ConvContainer.style.display = "block";
        }
        if (multiCurInput) {
            multiCurInput.style.border = "1px solid black";
        }

        const totalDiv = document.getElementsByClassName("total")[0];
        let totalValue = 0;
        if (totalDiv) {
            const totalText = totalDiv.textContent.trim();
            totalValue = parseFloat(totalText.replace(/[^0-9.-]+/g, '')) || 0;
        }

        const currency = await this.orm.call(
            'pos.config',
            'get_selected_currency',
            [selectedId],
            {}
        );

        if (currency && currency.length > 0) {
            this.multi_currency.usd_val = currency[0].usd_val;
            this.multi_currency.name = currency[0].name;
            this.multi_currency.symbol = currency[0].symbol;
            this.multi_currency.rate = currency[0].rate;
            this.multi_currency.total = Math.round(currency[0].rate * totalValue * 100) / 100;
        }
    },

    /**
     * Add a payment line using the selected foreign currency and amount.
     *
     * @param {Object} ev - Payment method configuration object.
     */
    async multi_currency_payment_line(ev) {
        if (this.pos.config.enable_multicurrency) {
            let amountVal = document.getElementsByClassName("multicurrency_input")[0]?.value;
            if (!amountVal) {
                return;
            }
            amountVal = parseFloat(amountVal);
            let totalVal = 0;
            let remainingVal = 0;
            const total = document.getElementsByClassName("total");
            if (total.length) {
                totalVal = parseFloat(total[0].innerText.replace(/[^\d.]/g, '')) || 0;
            }
            const remaining = document.getElementsByClassName("payment-status-remaining");
            if (remaining.length && remaining[0].children[1]) {
                const parts = remaining[0].children[1].innerText.split(" ");
                remainingVal = parseFloat(parts[1]) || 0;
            }
            if (totalVal > 0 || remainingVal > 0) {
                if (amountVal && this.multi_currency.rate) {
                    const paymentMethod =
                        (ev && ev.id ? ev : null) ||
                        this.payment_methods_from_config?.find((m) => m.type === "cash") ||
                        this.payment_methods_from_config?.[0];
                    if (!paymentMethod) {
                        return;
                    }
                    await this.addNewPaymentLine(paymentMethod);
                    const updateAmount = amountVal / this.multi_currency.rate;
                    const selectedLine = this.selectedPaymentLine;
                    if (selectedLine) {
                        selectedLine.setAmount(updateAmount);
                        selectedLine.converted_currency = {
                            name: this.multi_currency.name,
                            symbol: this.multi_currency.symbol,
                            amount: amountVal,
                        };
                        selectedLine.payment_currency = this.multi_currency.name;
                        selectedLine.currency_amount = amountVal;
                        selectedLine.update?.({
                            payment_currency: this.multi_currency.name,
                            currency_amount: amountVal,
                        });
                    }
                    const order = this.currentOrder || this.pos.getOrder();
                    if (order) {
                        order.converted_currency = {
                            name: this.multi_currency.name,
                            symbol: this.multi_currency.symbol,
                            rate: this.multi_currency.rate,
                            amount: amountVal,
                            converted_total: this.multi_currency.total,
                        };
                    }

                    const el = document.getElementById("conversion_container");
                    if (el) {
                        el.style.display = 'none';
                    }
                } else {
                    const ref = document.getElementsByClassName("multicurrency_input")[0];
                    if (ref) {
                        ref.style.border = "1.5px solid red";
                    }
                }
            }
        }
    },

    /**
     * Recalculate converted currency values when selected payment line is updated.
     *
     * @override
     * @param {number|boolean} [amount=false]
     */
    updateSelectedPaymentline(amount = false) {
        super.updateSelectedPaymentline(...arguments);
        if (this.pos.config.enable_multicurrency) {
            if (this.selectedPaymentLine && this.multi_currency.rate && this.selectedPaymentLine.converted_currency) {
                const changeAmount = this.selectedPaymentLine.amount * this.multi_currency.rate;
                this.selectedPaymentLine.converted_currency = {
                    name: this.multi_currency.name,
                    symbol: this.multi_currency.symbol,
                    amount: changeAmount,
                };
                this.selectedPaymentLine.payment_currency = this.multi_currency.name;
                this.selectedPaymentLine.currency_amount = changeAmount;
                this.selectedPaymentLine.update?.({
                    payment_currency: this.multi_currency.name,
                    currency_amount: changeAmount,
                });
            }
        }
    },

    /**
     * Compatibility alias for _updateSelectedPaymentline.
     */
    _updateSelectedPaymentline() {
        return this.updateSelectedPaymentline(...arguments);
    },

    /**
     * Sync payment line multi-currency data when validate button is clicked.
     *
     * @override
     * @param {Object} [args={}] - Validation arguments.
     * @returns {Promise<any>}
     */
    async onClickValidate(args = {}) {
        const order = this.currentOrder || this.pos.getOrder();
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
        return await super.onClickValidate(...arguments);
    },

    /**
     * Sync payment line multi-currency data before order validation is finalized.
     *
     * @override
     * @param {boolean} isForceValidate - Flag indicating forced validation.
     */
    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.getOrder();
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
        if (super.validateOrder) {
            await super.validateOrder(...arguments);
        }
    },
});
