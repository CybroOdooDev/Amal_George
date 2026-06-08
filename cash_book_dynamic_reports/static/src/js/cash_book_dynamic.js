/** @odoo-module */
import { registry } from "@web/core/registry";
import { Component } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { useRef, onMounted } from "@odoo/owl";

window.click_num = 0;
const actionRegistry = registry.category("actions");

export class ReportCashbook extends Component {
    setup() {
        super.setup(...arguments);
        this.action = useService("action");
        this.root = useRef('root-cash-book');
        this.start_function();
        onMounted(() => {
            this.renderElement();
        });
    }

    start_function() {
        this.acc_name = [];
        this.form = this.props.action.params.form;
        this.currency = this.props.action.params.currency;
        this.account_details = this.props.action.params.acc_name;
        this.account_res = this.props.action.params.account_res;
        this.init_balance = this.props.action.params.init_balance;
        if (this.account_details) {
            this.acc_name = this.account_details.map(item => item.acc_name);
        }
    }

    renderElement() {
        const self = this;
        if (self.account_res) {
            const categElement = this.root.el.querySelector('.categ');
            if (!categElement) {
                console.error("Element with class 'categ' not found.");
                return;
            }

            self.account_res.forEach((account) => {
                if (account) {
                    const tempName = `${account.code} ${account.name}`;
                    const safeId = tempName.replace(/[^a-zA-Z0-9_-]/g, '_');
                    const tr = document.createElement('tr');
                    tr.className = `parent_line ${safeId}`;
                    tr.dataset.id = safeId;
                    tr.style.height = '38px';

                    tr.innerHTML = `
                        <td style='border-bottom: 1px solid #e6e6e6; width:12%;'>${tempName}</td>
                        <td style='border-bottom: 1px solid #e6e6e6;'></td>
                        <td style='border-bottom: 1px solid #e6e6e6;'></td>
                        <td style='border-bottom: 1px solid #e6e6e6;'></td>
                        <td style='border-bottom: 1px solid #e6e6e6;'></td>
                        <td style='border-bottom: 1px solid #e6e6e6;'></td>
                        <td style='border-bottom: 1px solid #e6e6e6;'></td>
                        <td style='border-bottom: 1px solid #e6e6e6; text-align:right;'>${account.debit.toFixed(2)}${this.currency[0]}</td>
                        <td style='border-bottom: 1px solid #e6e6e6; text-align:right;'>${account.credit.toFixed(2)}${this.currency[0]}</td>
                        <td style='border-bottom: 1px solid #e6e6e6; text-align:right;'>${account.balance.toFixed(2)}${this.currency[0]}</td>
                    `;

                    categElement.appendChild(tr);

                    tr.addEventListener('click', (e) => {
                        window.click_num++;
                        const clickedName = e.target.innerHTML;
                        const accDetail = clickedName.split(/\s+/);
                        let moveLines = null;

                        for (const account of self.account_res) {
                            if (account && accDetail[0] === account.code) {
                                moveLines = account.move_lines;
                                break;
                            }
                        }

                        if (moveLines) {
                            const childRows = moveLines.map((line, j) => {
                                const rowId = line.lid;
                                const moveId = line.m_id;
                                const childTr = document.createElement('tr');
                                childTr.className = `child_class bankbook_dynamic_row ${safeId}`;
                                childTr.dataset.id = moveId;
                                childTr.id = rowId;
                                childTr.innerHTML = `
                                    <td style='width:12%;' data-id='${moveId}' id='${rowId}'></td>
                                    ${this.create_lines_with_style(line, `data-id="${moveId}" id="${rowId}"`)}
                                `;
                                return childTr;
                            });

                            const targetAccount = self.account_details.find(
                                (detail) => detail.acc_name === clickedName
                            );

                            if (targetAccount) {
                                if (targetAccount.fold === 1) {
                                    childRows.forEach((row) => {
                                        tr.parentNode.insertBefore(row, tr.nextSibling);
                                    });
                                    targetAccount.fold = 0;
                                } else {
                                    const rowsToRemove = this.root.el.querySelectorAll(`.bankbook_dynamic_row.${CSS.escape(safeId)}`);
                                    rowsToRemove.forEach((row) => row.remove());
                                    targetAccount.fold = 1;
                                }
                            }
                        }

                        const childElements = this.root.el.querySelectorAll('.child_class');
                        childElements.forEach((childElement) => {
                            childElement.removeEventListener('click', this.child_line_click);
                            childElement.addEventListener('click', (ev) => self.child_line_click(ev));
                        });
                    });
                }
            });
        }
    }

    create_lines_with_style(rec, attr) {
        const styleName = "border-bottom: 1px solid #e6e6e6;";
        const attrName = `${attr} style="${styleName}"`;
        let tempStr = `
            <td class='child_col1' ${attrName}>${rec.ldate}</td>
            <td class='child_col2' ${attrName}>${rec.lcode}</td>
            <td class='child_col3' ${attrName}>${rec.partner_name}</td>
            <td class='child_col4' ${attrName}>${rec.lref}</td>
            <td class='child_col5' ${attrName}>${rec.move_name}</td>
            <td class='child_col6' ${attrName}>${rec.lname}</td>
        `;
        if (this.currency[1] === 'after') {
            tempStr += `
                <td class='child_col7' ${attrName}>${rec.debit.toFixed(2)}${this.currency[0]}</td>
                <td class='child_col8' ${attrName}>${rec.credit.toFixed(2)}${this.currency[0]}</td>
                <td class='child_col9' ${attrName}>${rec.balance.toFixed(2)}${this.currency[0]}</td>
            `;
        } else {
            tempStr += `
                <td class='child_col7' ${attrName}>${this.currency[0]}${rec.debit.toFixed(2)}</td>
                <td class='child_col8' ${attrName}>${this.currency[0]}${rec.credit.toFixed(2)}</td>
                <td class='child_col9' ${attrName}>${this.currency[0]}${rec.balance.toFixed(2)}</td>
            `;
        }
        return tempStr;
    }

    child_line_click(el) {
        const line = el.target.dataset.id;
        return this.action.doAction({
            type: 'ir.actions.act_window',
            res_model: "account.move",
            res_id: parseInt(line),
            views: [[false, 'form']],
        });
    }
}

ReportCashbook.template = "cash_book_temp";
actionRegistry.add('report_cashbook', ReportCashbook);
