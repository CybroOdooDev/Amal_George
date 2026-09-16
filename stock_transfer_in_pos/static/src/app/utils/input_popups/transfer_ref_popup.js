/** @odoo-module **/
import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { Component, useProps, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";

export class TransferRefPopup extends Component {
    static template = "stock_transfer_in_pos.TransferRefPopup";
    static components = { Dialog };
    props = useProps({
        title: t.string().optional(_t("Confirm?")),
        data: t.object().optional({}),
        confirmButtonLabel: t.string().optional("OK"),
        close: t.function(),
    });

    setup() {
    this.dialog = useService("dialog");
    }

    // Function for redirect to the backend transfer  view
    stock_view() {
    var ref_id = this.props.data.id
     location.href = '/web#id='+ ref_id +'&&model=stock.picking&view_type=form'
    }
    confirm(){
    this.props.close();
    }
}