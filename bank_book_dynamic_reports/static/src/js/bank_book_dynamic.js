/** @odoo-module */
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { useState } from "@odoo/owl";
const actionRegistry = registry.category("actions");
import { Component , useSubEnv } from "@odoo/owl";

class ParentLine extends Component {
    static template = 'ParentLine';
    async setup() {
        this.state = useState({
             is_expanded: false,}
        )
       super.setup(...arguments);
    }
}

class BankBook extends Component {
    static template = 'bank_book_temp';
    static components = { ParentLine };
    async setup() {
        super.setup(...arguments);
        useSubEnv({ currency: this.props.action.params.currency });
        this.actionService = useService("action");
        }
    line_click(self) {
        this.actionService.doAction({
            type: 'ir.actions.act_window',
            res_model: "account.move",
            res_id: self,
            views: [[false, 'form']],
        });
    }
}
actionRegistry.add("report_bankbook", BankBook);
