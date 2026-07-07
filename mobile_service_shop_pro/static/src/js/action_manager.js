/** @odoo-module **/
/**
 * Mobile Service Shop Pro — Odoo 19
 * Intercepts 'service_xlsx' report actions and downloads the XLSX file
 * via the /mobile_service_xlsx_reports controller endpoint.
 */

import { registry } from "@web/core/registry";
import { download } from "@web/core/network/download";

registry.category("ir.actions.report handlers").add("service_xlsx", async (action) => {
    if (action.report_type === "service_xlsx") {
        await download({
            url: "/mobile_service_xlsx_reports",
            data: action.data,
        });
        return true;
    }
});
