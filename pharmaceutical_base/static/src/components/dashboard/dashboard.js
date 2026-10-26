/** @odoo-module **/

import { Component, onWillStart, useEffect, useRef, useState } from "@odoo/owl";
import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadJS } from "@web/core/assets";

export class PharmaDashboard extends Component {
    setup() {
        this.actionService = useService("action");
        this.orm = useService("orm");
        this.chartRef = useRef("chartCanvas");
        this.statusChartRef = useRef("statusChartCanvas");

        const today = luxon.DateTime.local();
        this.state = useState({
            // Rolling last-12-months window so the dashboard never goes blank
            // at a month boundary (data may predate the current month).
            startDate: today.minus({ months: 11 }).startOf("month").toFormat("yyyy-MM-dd"),
            endDate: today.endOf("month").toFormat("yyyy-MM-dd"),

            totalBatches: 0,
            openQcTests: 0,
            openDeviations: 0,
            openCapas: 0,
            openOos: 0,

            // All-status counts (used by the "All Quality Activities" tiles).
            allQcTests: 0,
            allDeviations: 0,
            allCapas: 0,
            allOos: 0,

            // Whether the optional pharma_capa_deviation module is installed.
            // Deviation / CAPA tiles and activity boxes are hidden when false.
            capaAvailable: true,

            releasedBatches: 0,
            quarantineBatches: 0,
            rejectedBatches: 0,
            pendingReleaseBatches: 0,
            statusPercent: 0,

            expiringToday: 0,
            expiring30: 0,
            expiring60: 0,
            expiring90: 0,

            recentBatches: [],

            chartLabels: ["Dec", "Jan", "Feb", "Mar", "Apr", "May"],
            chartData: [82, 96, 108, 95, 125, 148],   // Released (done) per bucket
            chartWip: [0, 0, 0, 0, 0, 0],              // In-process per bucket

            trendBatches: { value: 0, up: true },
            trendQc: { value: 0, up: true },
            trendDev: { value: 0, up: true },
            trendCapa: { value: 0, up: true },
            trendOos: { value: 0, up: true },

            chartFilter: "daily",
        });

        onWillStart(async () => {
            await loadJS("/web/static/lib/Chart/Chart.js");
            await this.fetchData();
        });

        useEffect(() => {
            this.renderChart();
        }, () => [this.state.chartData, this.state.chartWip]);

        useEffect(() => {
            this.renderStatusChart();
        }, () => [
            this.state.releasedBatches, this.state.quarantineBatches,
            this.state.rejectedBatches, this.state.pendingReleaseBatches,
        ]);
    }

    async fetchData() {
        const startStr = this.state.startDate + " 00:00:00";
        const endStr = this.state.endDate + " 23:59:59";

        // Trend chart buckets both series (Released / In-process) on the SAME
        // field so their categories line up exactly.
        const chartField = "create_date";
        let interval = "month";
        if (this.state.chartFilter === "yearly") interval = "year";
        else if (this.state.chartFilter === "weekly") interval = "week";
        else if (this.state.chartFilter === "daily") interval = "day";
        const groupBy = `${chartField}:${interval}`;
        const countKey = `${chartField}_count`;

        const startDT = luxon.DateTime.fromISO(this.state.startDate);
        const endDT = luxon.DateTime.fromISO(this.state.endDate);
        const diffDays = endDT.diff(startDT, 'days').days;

        const prevStartStr = startDT.minus({ days: diffDays + 1 }).toFormat("yyyy-MM-dd") + " 00:00:00";
        const prevEndStr = startDT.minus({ days: 1 }).toFormat("yyyy-MM-dd") + " 23:59:59";

        const today = luxon.DateTime.local();
        const todayEndStr = today.endOf("day").toFormat("yyyy-MM-dd HH:mm:ss");
        const todayStartStr = today.startOf("day").toFormat("yyyy-MM-dd HH:mm:ss");
        const in30 = today.plus({ days: 30 }).toFormat("yyyy-MM-dd HH:mm:ss");
        const in60 = today.plus({ days: 60 }).toFormat("yyyy-MM-dd HH:mm:ss");
        const in90 = today.plus({ days: 90 }).toFormat("yyyy-MM-dd HH:mm:ss");

        const dateDomain = [["create_date", ">=", startStr], ["create_date", "<=", endStr]];
        const prevDateDomain = [["create_date", ">=", prevStartStr], ["create_date", "<=", prevEndStr]];

        const [
            totalBatches, openQcTests, openDeviations, openCapas, openOos,
            releasedBatches, quarantineBatches, rejectedBatches, pendingReleaseBatches,
            expiringToday, expiring30, expiring60, expiring90,
            productionDone, productionWip, recentBatches,

            tmBatches, tmQc, tmDev, tmCapa, tmOos,
            lmBatches, lmQc, lmDev, lmCapa, lmOos
        ] = await Promise.all([
            // Current Period
            this.orm.searchCount("stock.lot", dateDomain),
            this.orm.searchCount("pharma.qc.test.order", [["status", "in", ["draft", "in_progress",
             "under_investigation"]], ...dateDomain]),
            // pharma.deviation / pharma.capa live in the optional
            // pharma_capa_deviation module — default to 0 when it's not installed
            // and remember its absence so the KPI tiles don't try to open it.
            this.orm.searchCount("pharma.deviation", [["status", "in", ["open", "under_investigation"]], ...dateDomain]).catch(() => { this.state.capaAvailable = false; return 0; }),
            this.orm.searchCount("pharma.capa", [["status", "in", ["open", "under_investigation"]], ...dateDomain]).catch(() => 0),
            this.orm.searchCount("pharma.oos.investigation", [["closed_on", "=", false], ...dateDomain]),

            // Statuses
            this.orm.searchCount("stock.lot", [["lot_status", "=", "released"], ...dateDomain]),
            this.orm.searchCount("stock.lot", [["lot_status", "=", "quarantine"], ...dateDomain]),
            this.orm.searchCount("stock.lot", [["lot_status", "=", "rejected"], ...dateDomain]),
            this.orm.searchCount("stock.lot", [["lot_status", "=", "approved"], ...dateDomain]),

            // Expiring — buckets are cumulative and all start at the beginning of
            // today, so a lot expiring today is also counted in the 30/60/90 windows.
            this.orm.searchCount("stock.lot", [["expiration_date", "<=", todayEndStr], ["expiration_date", ">=", todayStartStr]]),
            this.orm.searchCount("stock.lot", [["expiration_date", "<=", in30], ["expiration_date", ">=", todayStartStr]]),
            this.orm.searchCount("stock.lot", [["expiration_date", "<=", in60], ["expiration_date", ">=", todayStartStr]]),
            this.orm.searchCount("stock.lot", [["expiration_date", "<=", in90], ["expiration_date", ">=", todayStartStr]]),

            // Chart — Released (done) per bucket
            this.orm.call("mrp.production", "read_group", [[["state", "=", "done"],
            [chartField, ">=", startStr], [chartField, "<=", endStr]], ["id"], [groupBy]]),
            // Chart — In-process (not done / not cancelled) per bucket
            this.orm.call("mrp.production", "read_group", [[["state", "in", ["confirmed", "progress", "to_close"]],
            [chartField, ">=", startStr], [chartField, "<=", endStr]], ["id"], [groupBy]]),

            // Recent batches: the most recently created lots, any status.
            this.orm.searchRead("stock.lot",
                [],
                ["id", "name", "lot_status", "product_id", "create_date", "manufacture_date"],
                { limit: 6, order: "create_date desc" }),

            // This period creations for trend
            this.orm.searchCount("stock.lot", dateDomain),
            this.orm.searchCount("pharma.qc.test.order", dateDomain),
            this.orm.searchCount("pharma.deviation", dateDomain).catch(() => 0),
            this.orm.searchCount("pharma.capa", dateDomain).catch(() => 0),
            this.orm.searchCount("pharma.oos.investigation", dateDomain),

            // Previous period creations for trend
            this.orm.searchCount("stock.lot", prevDateDomain),
            this.orm.searchCount("pharma.qc.test.order", prevDateDomain),
            this.orm.searchCount("pharma.deviation", prevDateDomain).catch(() => 0),
            this.orm.searchCount("pharma.capa", prevDateDomain).catch(() => 0),
            this.orm.searchCount("pharma.oos.investigation", prevDateDomain),
        ]);

        const calcTrend = (tm, lm) => {
            if (lm === 0) return tm > 0 ? { value: 100, up: true } : { value: 0, up: true };
            const diff = ((tm - lm) / lm) * 100;
            return { value: Math.abs(Math.round(diff)), up: diff >= 0 };
        };

        this.state.trendBatches = calcTrend(tmBatches, lmBatches);
        this.state.trendQc = calcTrend(tmQc, lmQc);
        this.state.trendDev = calcTrend(tmDev, lmDev);
        this.state.trendCapa = calcTrend(tmCapa, lmCapa);
        this.state.trendOos = calcTrend(tmOos, lmOos);

        this.state.totalBatches = totalBatches;
        this.state.openQcTests = openQcTests;
        this.state.openDeviations = openDeviations;
        this.state.openCapas = openCapas;
        this.state.openOos = openOos;

        // All-status counts within the selected period (reuse the trend counts).
        this.state.allQcTests = tmQc;
        this.state.allDeviations = tmDev;
        this.state.allCapas = tmCapa;
        this.state.allOos = tmOos;

        this.state.releasedBatches = releasedBatches;
        this.state.quarantineBatches = quarantineBatches;
        this.state.rejectedBatches = rejectedBatches;
        this.state.pendingReleaseBatches = pendingReleaseBatches;

        const statusTotal = releasedBatches + quarantineBatches + rejectedBatches + pendingReleaseBatches;
        this.state.statusPercent = statusTotal ? Math.round((releasedBatches / statusTotal) * 100) : 0;

        this.state.expiringToday = expiringToday;
        this.state.expiring30 = expiring30;
        this.state.expiring60 = expiring60;
        this.state.expiring90 = expiring90;

        const statusLabels = {
            quarantine: "Quarantine", approved: "Approved", released: "Released",
            rejected: "Rejected", on_hold: "On Hold", recalled: "Recalled",
        };
        const fmtMfg = (val) => {
            if (!val) return "—";
            const dt = luxon.DateTime.fromISO(String(val).replace(" ", "T"));
            return dt.isValid ? dt.toFormat("MMM dd") : "—";
        };
        this.state.recentBatches = (recentBatches || []).map((lot) => ({
            id: lot.id,
            name: lot.name || `#${lot.id}`,
            product: lot.product_id ? lot.product_id[1] : "",
            mfgDate: fmtMfg(lot.manufacture_date || lot.create_date),
            statusLabel: statusLabels[lot.lot_status] || lot.lot_status,
            status: lot.lot_status,
        }));

        // Merge the two series (Released / In-process) on a shared, ordered set
        // of bucket keys so bars align. read_group returns groups in ascending
        // chronological order.
        const order = [];
        const relMap = {};
        const wipMap = {};
        const collect = (rows, map) => {
            for (const item of rows || []) {
                const key = item[groupBy];
                if (!key) continue;
                const k = String(key);
                map[k] = (map[k] || 0) + (item[countKey] || 0);
                if (!order.includes(k)) order.push(k);
            }
        };
        collect(productionDone, relMap);
        collect(productionWip, wipMap);

        if (order.length > 0) {
            const keys = order.slice(-30);
            this.state.chartLabels = keys.map((k) => k.split(" ")[0]);
            this.state.chartData = keys.map((k) => relMap[k] || 0);
            this.state.chartWip = keys.map((k) => wipMap[k] || 0);
        } else {
            this.state.chartLabels = ["No Data"];
            this.state.chartData = [0];
            this.state.chartWip = [0];
        }
    }

    renderChart() {
        if (!this.chartRef.el) return;
        const ctx = this.chartRef.el.getContext("2d");

        if (this.chartInstance) {
            this.chartInstance.destroy();
        }

        this.chartInstance = new Chart(ctx, {
            type: "bar",
            data: {
                labels: this.state.chartLabels,
                datasets: [
                    {
                        label: "Released",
                        data: this.state.chartData,
                        backgroundColor: "#577CBA",   // Blue 500
                        borderRadius: 4,
                        borderSkipped: false,
                        maxBarThickness: 26,
                    },
                    {
                        label: "In process",
                        data: this.state.chartWip,
                        backgroundColor: "#C9DCEE",   // pale blue
                        borderRadius: 4,
                        borderSkipped: false,
                        maxBarThickness: 26,
                    },
                ],
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                plugins: {
                    legend: {
                        display: true,
                        position: "bottom",
                        align: "start",
                        labels: {
                            boxWidth: 10,
                            boxHeight: 10,
                            usePointStyle: true,
                            pointStyle: "rectRounded",
                            color: "#3A4E63",
                            font: { size: 11 },
                        },
                    },
                    tooltip: {
                        backgroundColor: "#16283F",
                        titleColor: "#9BC0E6",
                        bodyColor: "#ffffff",
                        padding: 10,
                        cornerRadius: 8,
                    },
                },
                scales: {
                    y: {
                        beginAtZero: true,
                        grid: { color: "rgba(22, 40, 63, 0.06)" },
                        ticks: { color: "#3A4E63", precision: 0 },
                    },
                    x: {
                        grid: { display: false },
                        ticks: { color: "#3A4E63", maxRotation: 0, autoSkip: true, maxTicksLimit: 12 },
                    }
                }
            }
        });
    }

    renderStatusChart() {
        if (!this.statusChartRef.el) return;
        const ctx = this.statusChartRef.el.getContext("2d");

        if (this.statusChartInstance) {
            this.statusChartInstance.destroy();
        }

        // Anchor the tooltip just OUTSIDE the hovered arc so it never covers the
        // centre "% Released" label sitting in the doughnut hole. Registered
        // once on the shared tooltip plugin (idempotent across re-renders).
        const tooltipPlugin = Chart.registry.getPlugin("tooltip");
        if (tooltipPlugin && !tooltipPlugin.positioners.pharmaOutside) {
            tooltipPlugin.positioners.pharmaOutside = function (elements) {
                if (!elements.length) return false;
                const arc = elements[0].element;
                const angle = (arc.startAngle + arc.endAngle) / 2;
                const r = arc.outerRadius + 6;
                return {
                    x: arc.x + Math.cos(angle) * r,
                    y: arc.y + Math.sin(angle) * r,
                };
            };
        }

        const values = [
            this.state.releasedBatches,
            this.state.pendingReleaseBatches,
            this.state.quarantineBatches,
            this.state.rejectedBatches,
        ];
        const empty = values.every((v) => !v);

        this.statusChartInstance = new Chart(ctx, {
            type: "doughnut",
            data: {
                labels: ["Released", "Pending Release", "Quarantine", "Rejected"],
                datasets: [{
                    data: empty ? [1] : values,
                    backgroundColor: empty
                        ? ["#E7EEF5"]
                        : ["#2E4D8F", "#5B8DD9", "#E0A800", "#DC2626"],
                    borderWidth: 0,
                    hoverOffset: 4,
                }]
            },
            options: {
                responsive: true,
                maintainAspectRatio: false,
                cutout: "72%",
                // Small inset so an outside-anchored tooltip stays on-canvas.
                layout: { padding: 8 },
                plugins: {
                    legend: { display: false },
                    tooltip: {
                        enabled: !empty,
                        position: "pharmaOutside",
                        caretPadding: 6,
                        backgroundColor: "#16283F",
                        bodyColor: "#ffffff",
                        padding: 10,
                        cornerRadius: 8,
                    },
                },
            }
        });
    }

    // --- Action Handlers for Clicks ---

    openLots() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Batches",
            res_model: "stock.lot",
            views: [[false, "list"], [false, "form"]],
        });
    }

    openQcTests() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Open QC Tests",
            res_model: "pharma.qc.test.order",
            domain: [["status", "in", ["draft", "in_progress", "under_investigation"]]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openDeviations() {
        // Deviations live in the optional pharma_capa_deviation module.
        if (!this.state.capaAvailable) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Open Deviations",
            res_model: "pharma.deviation",
            domain: [["status", "in", ["open", "under_investigation"]]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openCapas() {
        // CAPAs live in the optional pharma_capa_deviation module.
        if (!this.state.capaAvailable) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Open CAPAs",
            res_model: "pharma.capa",
            domain: [["status", "in", ["open", "under_investigation"]]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openOos() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Open OOS",
            res_model: "pharma.oos.investigation",
            domain: [["closed_on", "=", false]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openAllQcTests() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "QC Tests",
            res_model: "pharma.qc.test.order",
            domain: [],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openAllDeviations() {
        if (!this.state.capaAvailable) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Deviations",
            res_model: "pharma.deviation",
            domain: [],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openAllCapas() {
        if (!this.state.capaAvailable) return;
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "CAPAs",
            res_model: "pharma.capa",
            domain: [],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openAllOos() {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "OOS",
            res_model: "pharma.oos.investigation",
            domain: [],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openLotsByStatus(status) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `Batches - ${status}`,
            res_model: "stock.lot",
            domain: [["lot_status", "=", status]],
            views: [[false, "list"], [false, "form"]],
        });
    }

    openLot(lotId) {
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: "Batch",
            res_model: "stock.lot",
            res_id: lotId,
            views: [[false, "form"]],
        });
    }

    openExpiringLots(days) {
        const today = luxon.DateTime.local();
        // All windows start at the beginning of today (matches the tile counts),
        // so lots expiring today are included in the 30/60/90 lists too.
        const start = today.startOf("day").toFormat("yyyy-MM-dd HH:mm:ss");
        let end;
        if (days === 0) {
            end = today.endOf("day").toFormat("yyyy-MM-dd HH:mm:ss");
        } else {
            end = today.plus({ days }).toFormat("yyyy-MM-dd HH:mm:ss");
        }

        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: `Expiring within ${days} days`,
            res_model: "stock.lot",
            domain: [["expiration_date", "<=", end], ["expiration_date", ">=", start]],
            views: [[false, "list"], [false, "form"]],
        });
    }
}

PharmaDashboard.template = "pharmaceutical_base.PharmaDashboard";

registry.category("actions").add("pharma_dashboard_action", PharmaDashboard);
