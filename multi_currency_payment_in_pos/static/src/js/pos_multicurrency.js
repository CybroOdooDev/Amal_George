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

    // Showing currencies in settings
    async show_options(event) {
        let isChecked = event.target.checked;
        let multiCurrencyContainer = document.getElementById("multicurrency_container");

        if (multiCurrencyContainer) {
            multiCurrencyContainer.style.display = isChecked ? "block" : "none";
        }
    },

    // Converting the currencies.
    async compute_currency(event) {
        let ConvContainer = document.getElementById("conversion_container");
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

        let multi_cur_input = document.getElementsByClassName("multicurrency_input")[0];

        if (ConvContainer) {
            ConvContainer.style.display = "block";
        }
        if (multi_cur_input) {
            multi_cur_input.style.border = "1px solid black";
        }

        let totalDiv = document.getElementsByClassName("total")[0];
        let totalValue = 0;
        if (totalDiv) {
            let totalText = totalDiv.textContent.trim();
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

    async multi_currency_payment_line(ev) {
        if (this.pos.config.enable_multicurrency) {
            let amount_val = document.getElementsByClassName("multicurrency_input")[0]?.value;
            if (!amount_val) {
                return;
            }
            amount_val = parseFloat(amount_val);
            let total_val = 0;
            let remaining_val = 0;
            let total = document.getElementsByClassName("total");
            if (total.length) {
                total_val = parseFloat(total[0].innerText.replace(/[^\d.]/g, '')) || 0;
            }
            let remaining = document.getElementsByClassName("payment-status-remaining");
            if (remaining.length && remaining[0].children[1]) {
                let parts = remaining[0].children[1].innerText.split(" ");
                remaining_val = parseFloat(parts[1]) || 0;
            }
            if (total_val > 0 || remaining_val > 0) {
                if (amount_val && this.multi_currency.rate) {
                    await this.addNewPaymentLine(ev);
                    var update_amount = amount_val / this.multi_currency.rate;
                    const selectedLine = this.selectedPaymentLine;
                    if (selectedLine) {
                        selectedLine.setAmount(update_amount);
                        selectedLine.converted_currency = {
                            name: this.multi_currency.name,
                            symbol: this.multi_currency.symbol,
                            amount: amount_val,
                        };
                        selectedLine.payment_currency = this.multi_currency.name;
                        selectedLine.currency_amount = amount_val;
                        selectedLine.update?.({
                            payment_currency: this.multi_currency.name,
                            currency_amount: amount_val,
                        });
                    }
                    const order = this.currentOrder || this.pos.getOrder();
                    if (order) {
                        order.converted_currency = {
                            name: this.multi_currency.name,
                            symbol: this.multi_currency.symbol,
                            rate: this.multi_currency.rate,
                            amount: amount_val,
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

    _updateSelectedPaymentline() {
        super._updateSelectedPaymentline(...arguments);
        if (this.pos.config.enable_multicurrency) {
            if (this.selectedPaymentLine && this.multi_currency.rate && this.selectedPaymentLine.converted_currency) {
                const change_amount = this.selectedPaymentLine.amount * this.multi_currency.rate;
                this.selectedPaymentLine.converted_currency = {
                    name: this.multi_currency.name,
                    symbol: this.multi_currency.symbol,
                    amount: change_amount,
                };
                this.selectedPaymentLine.payment_currency = this.multi_currency.name;
                this.selectedPaymentLine.currency_amount = change_amount;
                this.selectedPaymentLine.update?.({
                    payment_currency: this.multi_currency.name,
                    currency_amount: change_amount,
                });
            }
        }
    },

    async onClickValidate(args = {}) {
        const order = this.currentOrder || this.pos.getOrder();
        if (order && order.payment_ids) {
            order.payment_ids.forEach(line => {
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

    async validateOrder(isForceValidate) {
        const order = this.currentOrder || this.pos.getOrder();
        if (order && order.payment_ids) {
            order.payment_ids.forEach(line => {
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
