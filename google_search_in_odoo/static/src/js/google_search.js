/** @odoo-module **/
import { WarningDialog } from "@web/core/errors/error_dialogs";
import { useService } from "@web/core/utils/hooks";
import { Component, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { _t } from "@web/core/l10n/translation";
export class GoogleSearchWidget extends Component {
    async setup() {
        super.setup(...arguments);
        this.orm = useService('orm');
        this.dialog = useService("dialog");
        this.state = useState({
            isGoogleSearchEnabled: '',
        });
        this.orm.call("ir.config_parameter", "get_param", ["google_search_in_odoo.google_search"]).then((result) => {
            this.state.isGoogleSearchEnabled = result;
        });
    }
     onKeyPress(ev) {
        if (ev.key === "Enter") {
            ev.preventDefault();
            this._onClick(ev);
        }
    }
    _onCloseResults(ev) {
        ev.stopPropagation();
        const resultsDiv = document.getElementById('google_result');
        if (resultsDiv) {
            resultsDiv.classList.add('hidden');
        }
    }
    async _onClick(ev) {
        var self = this;
        // Get response from google based on the search value and display result on the template
        var input = document.getElementById("search_text");
        const resultsDiv = document.getElementById('google_result');
        const contentDiv = document.getElementById('google_result_content');
        if (ev.key === "Enter" && input.value.trim() !== '') {
            this.orm.call('res.config.settings', 'google_search_config', [input.value]).then(function (result) {
                if (result.error) {
                    var title = _t("Alert");
                    var message = _t(result.error);
                    self.dialog.add(WarningDialog, { title, message });
                } else if (result === null) {
                    var warning = _t('Limit exceeded for Queries and Queries per day');
                    self.dialog.add(WarningDialog, { title, warning });
                } else {
                    if (contentDiv) {
                        contentDiv.innerHTML = '';
                        contentDiv.scrollTop = 0;
                        for (let i = 0; i < result.length; i++) {
                            const resultItem = document.createElement("div");
                            const titleText = document.createTextNode(result[i].title);
                            const titleElement = document.createElement("h2");
                            titleElement.classList.add("header");
                            titleElement.appendChild(titleText);
                            const linkElement = document.createElement("a");
                            linkElement.classList.add("link");
                            linkElement.href = result[i].link;
                            linkElement.textContent = result[i].link;
                            
                            const snippetElement = document.createElement("p");
                            snippetElement.classList.add("content");
                            const fullSnippet = result[i].snippet || '';
                            const maxLen = 150;
                            if (fullSnippet.length > maxLen) {
                                const shortSnippet = fullSnippet.substring(0, maxLen) + '...';
                                snippetElement.textContent = shortSnippet;
                                snippetElement.classList.add("collapsible");
                                snippetElement.title = "Click to expand";
                                
                                let expanded = false;
                                snippetElement.addEventListener('click', (e) => {
                                    e.stopPropagation();
                                    if (expanded) {
                                        snippetElement.textContent = shortSnippet;
                                        snippetElement.classList.remove("expanded");
                                        snippetElement.title = "Click to expand";
                                        expanded = false;
                                    } else {
                                        snippetElement.textContent = fullSnippet;
                                        snippetElement.classList.add("expanded");
                                        snippetElement.title = "Click to collapse";
                                        expanded = true;
                                    }
                                });
                            } else {
                                snippetElement.textContent = fullSnippet;
                            }
                            
                            resultItem.appendChild(titleElement);
                            resultItem.appendChild(linkElement);
                            resultItem.appendChild(snippetElement);
                            contentDiv.appendChild(resultItem);
                        }
                    }
                    if (resultsDiv) {
                        resultsDiv.classList.remove('hidden');
                    }
                    if (contentDiv) {
                        contentDiv.scrollTop = 0;
                    }
                }
            });
        } else {
            if (resultsDiv) {
                resultsDiv.classList.add('hidden');
            }
        }
    }
}
export const searchItem = {
    Component: GoogleSearchWidget,
};
GoogleSearchWidget.template = "google_search_in_odoo.SearchSystray";
registry.category("systray").add("GoogleSearch", searchItem, { sequence: 0 });
