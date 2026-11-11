/** @odoo-module */
import { registry } from "@web/core/registry";
import { BlockUI } from "@web/core/ui/block_ui";
import { download } from "@web/core/network/download";
// Adding excel to the report handlers and redirect to url /bank_xlsx_reports
registry.category("ir.actions.report handlers").add("bank_book_xlsx", async function (action) {
    if (action.report_type === 'bank_book_xlsx') {
        BlockUI;
        await download({
            url: '/bank_xlsx_reports',
            data: action.data,
            complete: () => unblockUI,
            error: (error) => self.call('crash_manager', 'rpc_error', error),
        });
    }
});
