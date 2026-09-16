/** @odoo-module **/

import { _t } from "@web/core/l10n/translation";
import { useService } from "@web/core/utils/hooks";
import { usePos } from "@point_of_sale/app/hooks/pos_hook";
import { Component, useProps, signal, t } from "@odoo/owl";
import { Dialog } from "@web/core/dialog/dialog";
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { TransferRefPopup } from "@stock_transfer_in_pos/app/utils/input_popups/transfer_ref_popup";


export class TransferPopup extends Component {
    static template = "stock_transfer_in_pos.TransferPopup";
    static components = { Dialog };
    props = useProps({
        title: t.string().optional(_t("Confirm?")),
        data: t.object().optional({}),
        confirmButtonLabel: t.string().optional("Confirm"),
        close: t.function(),
    });

    dest_tr = signal.ref();
    source_tr = signal.ref();
    picking = signal.ref();
    source_loc = signal.ref();
    dest_loc = signal.ref();
    stage = signal.ref();

    setup() {
        this.dialog = useService("dialog");
        this.pos = usePos();
        this.orm = useService("orm");
    }
    _clickPicking(ev){
           //This will hide and show destination and source location based on
           //the picking type selected
           var type = ev.target.selectedOptions[0].dataset.type
           var sourceTr = this.source_tr();
           var destTr = this.dest_tr();
           if (sourceTr) sourceTr.classList.remove('d-none');
           if (destTr) destTr.classList.remove('d-none');
           if (type == 'incoming') {
               if (sourceTr) sourceTr.classList.add('d-none');
           }
           else if (type == 'outgoing') {
              if (destTr) destTr.classList.add('d-none');
           }
       }
    //Confirm button for create the transfer in backend
    async confirm(){
        // Retrieved all the values you selected in the popup and transfer the
        // stock by passing data to the backend.
            var pickingEl = this.picking();
            var sourceLocEl = this.source_loc();
            var destLocEl = this.dest_loc();
            var stageEl = this.stage();
            var pick_id = pickingEl ? pickingEl.value : '';
            var source_id = sourceLocEl ? sourceLocEl.value : '';
            var dest_id = destLocEl ? destLocEl.value : '';
            var state = stageEl ? stageEl.value : 'draft';
            var line = this.pos.getOrder().lines;
            var product = {'pro_id':[],'qty':[]}
            if(pick_id ){
                 for(var i=0; i<line.length;i++){
                 product['pro_id'].push(line[i].product_id.id)
                 product['qty'].push(line[i].qty)
            }
            var self = this;
            await this.orm.call(
            "pos.config", "create_transfer", [pick_id,source_id,dest_id,state,product], {}
            ).then(function(result) {
            self.dialog.add(TransferRefPopup, {
                        title: _t("Success"),
                        data: result,
                    });
            })
           this.cancel();
            }
            else{
                this.dialog.add(WarningDialog, {
                        title: _t("Select Picking Type"),
                        message: _t("Please select a picking type for transferring"),
                    });
            }
        }

    cancel() {
        this.props.close();
    }
}