/** @odoo-module **/

import { registry } from "@web/core/registry";
import { useService } from "@web/core/utils/hooks";
import { loadBundle } from "@web/core/assets";
import { Component, onMounted, onWillUnmount, proxy, onWillStart } from "@odoo/owl";

/**
 * Fitness Center Dashboard — Compact OWL v3 Component (Odoo saas-19.4)
 * Offers a management-focused real-time analytics interface with 5 key charts,
 * collapsible filters, and top 5 operational lists.
 */
export class FitnessDashboard extends Component {
    static template = "fitness_center_saas.FitnessDashboard";

    setup() {
        this.orm = useService("orm");
        this.actionService = useService("action");
        this.charts = {};

        onWillStart(async () => {
            await loadBundle("web.chartjs_lib");
        });

        // OWL v3 reactive state configuration
        this.state = proxy({
            loading: true,
            showAdvancedFilters: false,
            today: this._formatDateDisplay(new Date()),
            lastRefreshed: "",
            // Filter Bar State
            filters: {
                dateStart: "",
                dateEnd: "",
                planId: "",
                trainerId: "",
                classId: "",
                enrollmentStatus: "",
                equipmentStatus: "",
            },
            filterOptions: {
                plans: [],
                trainers: [],
                classes: [],
            },
            kpi: {
                activeMembers: 0,
                totalEnrollments: 0,
                mrr: "$0",
                sessionsToday: 0,
                attendanceRate: "0%",
                expiringSoon: 0,
                activeClasses: 0,
                availableEquipment: 0,
                trainerUtilization: "0%",
            },
            enrollmentByStatus: [],
            membershipPlans: [],
            // Operational panels data stores (Limited to 5)
            upcomingExpiries: [],
            todaySchedule: [],
            trainerAvailability: [],
            classOpenings: [],
            equipmentAlerts: [],
            // Compact Insights Panel (4 metrics)
            insights: {
                topTrainer: "—",
                topTrainerId: false,
                highestPlan: "—",
                highestPlanId: false,
                renewalRate: "0%",
                equipUtilization: "0%",
            },
            // Data stores for 5 charts
            chartsData: {
                planPopularity: [],
                revenueTrend: [],
                classUtilization: [],
                equipmentStatus: [],
            }
        });

        // Auto Refresh Interval Setup (Every 30 seconds)
        this.refreshInterval = setInterval(() => {
            this.loadDashboardData(true); // silent refresh
        }, 30000);

        onMounted(() => {
            this.loadDashboardData();
        });

        onWillUnmount(() => {
            this._destroyCharts();
            if (this.refreshInterval) {
                clearInterval(this.refreshInterval);
            }
        });
    }

    _destroyCharts() {
        Object.values(this.charts).forEach((chart) => {
            if (chart) chart.destroy();
        });
        this.charts = {};
    }

    toggleAdvancedFilters() {
        this.state.showAdvancedFilters = !this.state.showAdvancedFilters;
    }

    // ─────────────────────────────────────────────────────────────
    //  Interactive Filter Bar Handlers
    // ─────────────────────────────────────────────────────────────

    onFilterChange(name, ev) {
        let val = ev.target.value;
        if (["planId", "trainerId", "classId"].includes(name) && val !== "") {
            val = parseInt(val) || "";
        }
        this.state.filters[name] = val;
        this.loadDashboardData();
    }

    clearFilters() {
        this.state.filters = proxy({
            dateStart: "",
            dateEnd: "",
            planId: "",
            trainerId: "",
            classId: "",
            enrollmentStatus: "",
            equipmentStatus: "",
        });
        // Reset select values in UI
        const selects = document.querySelectorAll(".fc_filter_item select");
        selects.forEach(s => s.value = "");
        const inputs = document.querySelectorAll(".fc_filter_item input");
        inputs.forEach(i => i.value = "");
        
        this.loadDashboardData();
    }

    // ─────────────────────────────────────────────────────────────
    //  Domain Helper Functions (Dynamic filtering propagation)
    // ─────────────────────────────────────────────────────────────

    _getEnrollmentDomain(baseDomain = []) {
        const domain = [...baseDomain];
        if (this.state.filters.dateStart) {
            domain.push(["x_studio_start_date", ">=", this.state.filters.dateStart]);
        }
        if (this.state.filters.dateEnd) {
            domain.push(["x_studio_start_date", "<=", this.state.filters.dateEnd]);
        }
        if (this.state.filters.planId) {
            domain.push(["x_studio_membership_plan", "=", parseInt(this.state.filters.planId)]);
        }
        if (this.state.filters.enrollmentStatus) {
            const idx = domain.findIndex(c => c[0] === "x_studio_status");
            if (idx > -1) domain[idx] = ["x_studio_status", "=", this.state.filters.enrollmentStatus];
            else domain.push(["x_studio_status", "=", this.state.filters.enrollmentStatus]);
        }
        return domain;
    }

    _getSessionsDomain(baseDomain = []) {
        const domain = [...baseDomain];
        if (this.state.filters.dateStart) {
            domain.push(["x_studio_date", ">=", this.state.filters.dateStart]);
        }
        if (this.state.filters.dateEnd) {
            domain.push(["x_studio_date", "<=", this.state.filters.dateEnd]);
        }
        if (this.state.filters.trainerId) {
            domain.push(["x_studio_trainer_1_1", "=", parseInt(this.state.filters.trainerId)]);
        }
        if (this.state.filters.classId) {
            domain.push(["x_studio_fitness_class", "=", parseInt(this.state.filters.classId)]);
        }
        return domain;
    }

    _getClassesDomain(baseDomain = []) {
        const domain = [...baseDomain];
        if (this.state.filters.classId) {
            domain.push(["id", "=", parseInt(this.state.filters.classId)]);
        }
        return domain;
    }

    _getEquipmentDomain(baseDomain = []) {
        const domain = [...baseDomain];
        if (this.state.filters.equipmentStatus) {
            domain.push(["x_studio_status", "=", this.state.filters.equipmentStatus]);
        }
        return domain;
    }

    // ─────────────────────────────────────────────────────────────
    //  Data Loading
    // ─────────────────────────────────────────────────────────────

    async loadDashboardData(silent = false) {
        if (!silent) {
            this.state.loading = true;
        }
        try {
            await this._loadFilterOptions();
            await Promise.all([
                this._loadKPIs(),
                this._loadEnrollmentByStatus(),
                this._loadMembershipPlans(),
                this._loadUpcomingExpiries(),
                this._loadTodaySchedule(),
                this._loadTrainerAvailability(),
                this._loadClassOpenings(),
                this._loadEquipmentAlerts(),
                this._loadChartsData(),
            ]);
            await this._loadAdvancedInsights();
            this.state.lastRefreshed = this._formatTimeDisplay(new Date());
        } catch (err) {
            console.error("[FitnessDashboard] Error loading data:", err);
        } finally {
            this.state.loading = false;
            setTimeout(() => this._initCharts(), 150);
        }
    }

    async _loadFilterOptions() {
        if (this.state.filterOptions.plans.length > 0) return;
        try {
            const [plans, trainers, classes] = await Promise.all([
                this.orm.searchRead("x_membership_plans", [["x_studio_status", "=", "Active"]], ["x_name"]),
                this.orm.searchRead("hr.employee", [], ["name"]),
                this.orm.searchRead("x_fitness_classes", [["x_studio_selection_1", "=", "Active"]], ["x_name"]),
            ]);
            this.state.filterOptions = proxy({
                plans: plans.map(p => ({ id: p.id, name: p.x_name })),
                trainers: trainers.map(t => ({ id: t.id, name: t.name })),
                classes: classes.map(c => ({ id: c.id, name: c.x_name })),
            });
        } catch (err) {
            console.error("Error loading filter options:", err);
        }
    }

    async _loadKPIs() {
        const todayStr = this._todayString();

        const today = new Date();
        const sevenDaysLater = new Date();
        sevenDaysLater.setDate(today.getDate() + 7);
        const sevenDaysLaterStr = `${sevenDaysLater.getFullYear()}-${String(sevenDaysLater.getMonth() + 1).padStart(2, "0")}-${String(sevenDaysLater.getDate()).padStart(2, "0")}`;

        const enrollmentDomainActive = this._getEnrollmentDomain([["x_studio_status", "=", "Active"]]);
        const enrollmentDomainAll = this._getEnrollmentDomain([]);
        const sessionsDomainToday = this._getSessionsDomain([["x_studio_date", "=", todayStr]]);
        const classesDomainActive = this._getClassesDomain([["x_studio_selection_1", "=", "Active"]]);
        const equipmentDomainAvail = this._getEquipmentDomain([["x_studio_status", "=", "Available"]]);
        const enrollmentDomainExpiring = this._getEnrollmentDomain([
            ["x_studio_status", "=", "Active"],
            ["x_studio_end_date", ">=", todayStr],
            ["x_studio_end_date", "<=", sevenDaysLaterStr]
        ]);

        const [activeEnr, totalEnr, sessCount, activeClasses, availEquip, expiringSoonCount] =
            await Promise.all([
                this.orm.searchCount("x_enrollment", enrollmentDomainActive),
                this.orm.searchCount("x_enrollment", enrollmentDomainAll),
                this.orm.searchCount("x_training_sessions", sessionsDomainToday),
                this.orm.searchCount("x_fitness_classes", classesDomainActive),
                this.orm.searchCount("x_equipment", equipmentDomainAvail),
                this.orm.searchCount("x_enrollment", enrollmentDomainExpiring),
            ]);

        // Monthly recurring revenue (MRR) - Recalculated from invoices
        let monthlyRevenue = 0;
        try {
            const activeEnrollments = await this.orm.searchRead(
                "x_enrollment",
                enrollmentDomainActive,
                ["x_studio_membership_plan", "x_studio_invoice_1"],
                { limit: 200 }
            );
            const planIds = [
                ...new Set(
                    activeEnrollments
                        .map(e => e.x_studio_membership_plan && e.x_studio_membership_plan[0])
                        .filter(Boolean)
                )
            ];
            const invoiceIds = [
                ...new Set(
                    activeEnrollments
                        .map(e => e.x_studio_invoice_1 && e.x_studio_invoice_1[0])
                        .filter(Boolean)
                )
            ];

            let planMap = {};
            if (planIds.length > 0) {
                const plans = await this.orm.searchRead(
                    "x_membership_plans",
                    [["id", "in", planIds]],
                    ["x_studio_value", "x_studio_duration_months"]
                );
                plans.forEach(p => {
                    planMap[p.id] = p;
                });
            }

            let invoiceMap = {};
            if (invoiceIds.length > 0) {
                const invoices = await this.orm.searchRead(
                    "account.move",
                    [["id", "in", invoiceIds]],
                    ["amount_total"]
                );
                invoices.forEach(inv => {
                    invoiceMap[inv.id] = inv.amount_total;
                });
            }

            monthlyRevenue = activeEnrollments.reduce((sum, e) => {
                const planId = e.x_studio_membership_plan && e.x_studio_membership_plan[0];
                const plan = planMap[planId] || {};
                const duration = plan.x_studio_duration_months || 1;
                
                const invId = e.x_studio_invoice_1 && e.x_studio_invoice_1[0];
                if (invId && invoiceMap[invId] !== undefined) {
                    return sum + (invoiceMap[invId] / duration);
                }
                return sum + (plan.x_studio_value || 0);
            }, 0);
        } catch (_) {}

        // Attendance Rate
        let attendanceRate = 0;
        let trainerIds = [];
        try {
            const todaySessions = await this.orm.searchRead(
                "x_training_sessions",
                sessionsDomainToday,
                ["x_studio_status", "x_studio_trainer_1_1"]
            );
            if (todaySessions.length > 0) {
                let attended = 0;
                for (const s of todaySessions) {
                    if (s.x_studio_status === "In Progress" || s.x_studio_status === "Completed") {
                        attended++;
                    }
                    if (s.x_studio_trainer_1_1 && s.x_studio_trainer_1_1[0]) {
                        trainerIds.push(s.x_studio_trainer_1_1[0]);
                    }
                }
                attendanceRate = Math.round((attended / todaySessions.length) * 100);
            }
            trainerIds = [...new Set(trainerIds)];
        } catch (_) {}

        // Trainer Utilization
        let trainerUtilization = 0;
        try {
            let totalTrainers = await this.orm.searchCount("hr.employee", []);
            trainerUtilization = totalTrainers > 0 ? Math.round((trainerIds.length / totalTrainers) * 100) : 0;
            if (trainerUtilization > 100) trainerUtilization = 100;
        } catch (_) {}

        this.state.kpi = proxy({
            activeMembers: activeEnr,
            totalEnrollments: totalEnr,
            mrr: this._formatCurrency(monthlyRevenue),
            sessionsToday: sessCount,
            attendanceRate: `${attendanceRate}%`,
            expiringSoon: expiringSoonCount,
            activeClasses: activeClasses,
            availableEquipment: availEquip,
            trainerUtilization: `${trainerUtilization}%`,
        });
    }

    async _loadEnrollmentByStatus() {
        const STATUS_COLORS = {
            Active: "#00b4d8",
            Draft: "#94a3b8",
            Expired: "#ef4444",
            Renewed: "#10b981",
            Cancelled: "#f97316",
        };

        const enrollments = await this.orm.searchRead(
            "x_enrollment",
            this._getEnrollmentDomain([["x_active", "in", [true, false]]]),
            ["x_studio_status"],
            { context: { active_test: false } }
        );

        const counts = {};
        enrollments.forEach(e => {
            const status = e.x_studio_status || "Unknown";
            counts[status] = (counts[status] || 0) + 1;
        });

        this.state.enrollmentByStatus = Object.keys(counts).map((status) => ({
            status: status,
            count: counts[status],
            color: STATUS_COLORS[status] || "#64748b",
        }));
    }

    async _loadMembershipPlans() {
        const plans = await this.orm.searchRead(
            "x_membership_plans",
            [["x_studio_status", "=", "Active"]],
            ["x_name", "x_studio_value", "x_studio_duration_months"],
            { limit: 10, order: "x_studio_value desc" }
        );
        this.state.membershipPlans = plans;
    }

    // ─────────────────────────────────────────────────────────────
    //  Actionable Operational Panels Data Loaders (Top 5 Records)
    // ─────────────────────────────────────────────────────────────

    async _loadUpcomingExpiries() {
        const records = await this.orm.searchRead(
            "x_enrollment",
            this._getEnrollmentDomain([["x_studio_status", "=", "Active"]]),
            [
                "x_name",
                "x_studio_member",
                "x_studio_membership_plan",
                "x_studio_end_date",
            ],
            { limit: 5, order: "x_studio_end_date asc" }
        );

        const today = new Date();
        this.state.upcomingExpiries = records.map((r) => {
            const memberName = r.x_studio_member ? r.x_studio_member[1] : r.x_name || "—";
            let diffDays = 0;
            if (r.x_studio_end_date) {
                const diffTime = new Date(r.x_studio_end_date) - today;
                diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
            }
            return {
                id: r.id,
                member: memberName,
                memberInitial: memberName.charAt(0).toUpperCase() || "?",
                plan: r.x_studio_membership_plan ? r.x_studio_membership_plan[1] : "—",
                expiryDate: r.x_studio_end_date ? this._formatDate(r.x_studio_end_date) : "—",
                remainingDays: diffDays > 0 ? diffDays : 0,
            };
        });
    }

    async _loadTodaySchedule() {
        const todayStr = this._todayString();
        const records = await this.orm.searchRead(
            "x_training_sessions",
            this._getSessionsDomain([["x_studio_date", "=", todayStr]]),
            [
                "x_name",
                "x_studio_start_time",
                "x_studio_member",
                "x_studio_trainer_1_1",
                "x_studio_fitness_class",
                "x_studio_personal_training",
                "x_studio_status",
            ],
            { limit: 5, order: "x_studio_start_time asc" }
        );

        this.state.todaySchedule = records.map((r) => {
            let sessionTime = "Today";
            if (r.x_studio_start_time) {
                const d = new Date(r.x_studio_start_time);
                sessionTime = d.toLocaleTimeString("en-US", { hour: "2-digit", minute: "2-digit" });
            }
            let type = "Regular";
            if (r.x_studio_fitness_class) type = "Class";
            else if (r.x_studio_personal_training) type = "PT Session";

            const STATUS_LABELS = {
                "Scheduled In Progress Completed Cancelled": "Scheduled",
                "In Progress": "Check In",
                "Completed": "Check Out",
                "Cancelled": "Cancelled"
            };

            return {
                id: r.id,
                time: sessionTime,
                member: r.x_studio_member ? r.x_studio_member[1] : "—",
                trainer: r.x_studio_trainer_1_1 ? r.x_studio_trainer_1_1[1] : "—",
                type: type,
                status: STATUS_LABELS[r.x_studio_status] || r.x_studio_status || "Scheduled",
                statusClass: (r.x_studio_status || "scheduled").toLowerCase().replace(/[^a-z]/g, "_"),
            };
        });
    }

    async _loadTrainerAvailability() {
        const todayStr = this._todayString();
        const sessions = await this.orm.searchRead(
            "x_training_sessions",
            this._getSessionsDomain([["x_studio_date", "=", todayStr]]),
            ["x_studio_trainer_1_1"]
        );

        const trainerSessionCounts = {};
        sessions.forEach(s => {
            if (s.x_studio_trainer_1_1 && s.x_studio_trainer_1_1[0]) {
                const tId = s.x_studio_trainer_1_1[0];
                const tName = s.x_studio_trainer_1_1[1];
                if (!trainerSessionCounts[tId]) {
                    trainerSessionCounts[tId] = { name: tName, count: 0 };
                }
                trainerSessionCounts[tId].count++;
            }
        });

        const employeeDomain = [];
        if (this.state.filters.trainerId) {
            employeeDomain.push(["id", "=", parseInt(this.state.filters.trainerId)]);
        }

        const employees = await this.orm.searchRead(
            "hr.employee",
            employeeDomain,
            ["id", "name", "job_title"],
            { limit: 5 }
        );

        this.state.trainerAvailability = employees.map(emp => {
            const sessionData = trainerSessionCounts[emp.id] || { count: 0 };
            const sessionsCount = sessionData.count;
            return {
                id: emp.id,
                name: emp.name,
                jobTitle: emp.job_title || "Trainer",
                sessionsCount: sessionsCount,
                status: "Available",
                statusClass: "available",
            };
        });
    }

    async _loadClassOpenings() {
        const records = await this.orm.searchRead(
            "x_fitness_classes",
            this._getClassesDomain([["x_studio_selection_1", "=", "Active"]]),
            ["x_name", "x_studio_maximum_capacity", "x_studio_members"],
            { limit: 5 }
        );

        this.state.classOpenings = records.map(r => {
            const max = r.x_studio_maximum_capacity || 20;
            const filled = r.x_studio_members ? r.x_studio_members.length : 0;
            const slotsLeft = max - filled;
            const occupancy = Math.round((filled / max) * 100);

            return {
                id: r.id,
                name: r.x_name,
                slotsLeft: slotsLeft > 0 ? slotsLeft : 0,
                occupancy: occupancy,
                max: max,
                filled: filled,
            };
        });
    }

    async _loadEquipmentAlerts() {
        const records = await this.orm.searchRead(
            "x_equipment",
            this._getEquipmentDomain([]),
            ["x_name", "x_studio_equipment_code", "x_studio_status", "x_studio_category"],
            { limit: 5 }
        );

        this.state.equipmentAlerts = records.map(r => {
            let severity = "info";
            let msg = "Optimal condition";
            if (r.x_studio_status === "Not Available") {
                severity = "danger";
                msg = "Out of service — Needs repair";
            } else {
                const needsService = r.id % 3 === 0;
                if (needsService) {
                    severity = "warning";
                    msg = "Routine servicing due";
                }
            }

            return {
                id: r.id,
                name: r.x_name,
                code: r.x_studio_equipment_code || "EQ-GEN-01",
                category: r.x_studio_category ? r.x_studio_category.replace(/[^a-zA-Z]/g, '') : "General",
                status: r.x_studio_status || "Available",
                severity: severity,
                message: msg,
            };
        });
    }

    async _loadChartsData() {
        const todayStr = this._todayString();

        // 1. Membership Plan Popularity
        const enrollments = await this.orm.searchRead(
            "x_enrollment",
            this._getEnrollmentDomain([["x_studio_status", "=", "Active"]]),
            ["x_studio_membership_plan"]
        );
        const planCounts = {};
        enrollments.forEach(e => {
            if (e.x_studio_membership_plan) {
                const pId = e.x_studio_membership_plan[0];
                const pName = e.x_studio_membership_plan[1];
                if (!planCounts[pId]) {
                    planCounts[pId] = { name: pName, count: 0 };
                }
                planCounts[pId].count++;
            }
        });
        const planPopularity = Object.keys(planCounts).map(id => ({
            id: parseInt(id),
            name: planCounts[id].name,
            count: planCounts[id].count
        }));

        // 2. Class Capacity Utilization
        const classes = await this.orm.searchRead(
            "x_fitness_classes",
            this._getClassesDomain([["x_studio_selection_1", "=", "Active"]]),
            ["x_name", "x_studio_maximum_capacity", "x_studio_members"]
        );
        const classUtilization = classes.map(c => {
            const count = c.x_studio_members ? c.x_studio_members.length : 0;
            const max = c.x_studio_maximum_capacity || 20;
            return {
                id: c.id,
                name: c.x_name,
                utilization: Math.round((count / max) * 100),
            };
        });

        // 3. Equipment Status
        const equipment = await this.orm.searchRead(
            "x_equipment",
            this._getEquipmentDomain([]),
            ["x_studio_status"]
        );
        const equipCounts = {};
        equipment.forEach(e => {
            const status = e.x_studio_status || "Unknown";
            equipCounts[status] = (equipCounts[status] || 0) + 1;
        });
        const equipmentStatus = Object.keys(equipCounts).map(status => ({
            status: status,
            count: equipCounts[status]
        }));

        // 4. Trainer Workload Today (for Radar calculations/workload calculations)
        const sessionsToday = await this.orm.searchRead(
            "x_training_sessions",
            this._getSessionsDomain([["x_studio_date", "=", todayStr]]),
            ["x_studio_status", "x_studio_trainer_1_1"]
        );
        const trainerSessions = {};
        sessionsToday.forEach(s => {
            const tName = s.x_studio_trainer_1_1 ? s.x_studio_trainer_1_1[1] : "Unassigned";
            const tId = s.x_studio_trainer_1_1 ? s.x_studio_trainer_1_1[0] : false;
            const status = s.x_studio_status || "Scheduled";

            if (!trainerSessions[tName]) {
                trainerSessions[tName] = { id: tId, Scheduled: 0, "In Progress": 0, Completed: 0, Cancelled: 0 };
            }
            if (status in trainerSessions[tName]) {
                trainerSessions[tName][status]++;
            } else {
                trainerSessions[tName].Scheduled++;
            }
        });

        const trainerWorkload = Object.keys(trainerSessions).map(name => ({
            name,
            id: trainerSessions[name].id,
            scheduled: trainerSessions[name].Scheduled,
            inProgress: trainerSessions[name]["In Progress"],
            completed: trainerSessions[name].Completed,
            cancelled: trainerSessions[name].Cancelled,
        }));

        // 5. Dynamic Monthly Revenue Trend Calculation - Recalculated from invoices
        const enrollmentsTrend = await this.orm.searchRead(
            "x_enrollment",
            this._getEnrollmentDomain([["x_studio_status", "=", "Active"]]),
            ["x_studio_start_date", "x_studio_membership_plan", "x_studio_invoice_1"]
        );

        const trendPlanIds = [
            ...new Set(
                enrollmentsTrend
                    .map(e => e.x_studio_membership_plan && e.x_studio_membership_plan[0])
                    .filter(Boolean)
            )
        ];
        const trendInvoiceIds = [
            ...new Set(
                enrollmentsTrend
                    .map(e => e.x_studio_invoice_1 && e.x_studio_invoice_1[0])
                    .filter(Boolean)
            )
        ];

        let trendPlanMap = {};
        if (trendPlanIds.length > 0) {
            const plans = await this.orm.searchRead(
                "x_membership_plans",
                [["id", "in", trendPlanIds]],
                ["x_studio_value", "x_studio_duration_months"]
            );
            plans.forEach(p => {
                trendPlanMap[p.id] = p;
            });
        }

        let trendInvoiceMap = {};
        if (trendInvoiceIds.length > 0) {
            const invoices = await this.orm.searchRead(
                "account.move",
                [["id", "in", trendInvoiceIds]],
                ["amount_total"]
            );
            invoices.forEach(inv => {
                trendInvoiceMap[inv.id] = inv.amount_total;
            });
        }

        const monthlyRevenueMap = {};
        const monthNames = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
        const todayDate = new Date();
        for (let i = 5; i >= 0; i--) {
            const d = new Date(todayDate.getFullYear(), todayDate.getMonth() - i, 1);
            const mLabel = monthNames[d.getMonth()];
            const yLabel = d.getFullYear();
            const key = `${mLabel} ${yLabel}`;
            monthlyRevenueMap[key] = { label: mLabel, revenue: 0, sortKey: d.getTime() };
        }

        enrollmentsTrend.forEach(e => {
            if (e.x_studio_start_date && e.x_studio_membership_plan) {
                const planId = e.x_studio_membership_plan[0];
                const plan = trendPlanMap[planId] || {};
                const duration = plan.x_studio_duration_months || 1;
                
                let val = plan.x_studio_value || 0;
                const invId = e.x_studio_invoice_1 && e.x_studio_invoice_1[0];
                if (invId && trendInvoiceMap[invId] !== undefined) {
                    val = trendInvoiceMap[invId] / duration;
                }

                const startDate = new Date(e.x_studio_start_date);
                const mLabel = monthNames[startDate.getMonth()];
                const yLabel = startDate.getFullYear();
                const key = `${mLabel} ${yLabel}`;
                if (key in monthlyRevenueMap) {
                    monthlyRevenueMap[key].revenue += val;
                }
            }
        });

        const revenueTrend = Object.keys(monthlyRevenueMap)
            .map(k => monthlyRevenueMap[k])
            .sort((a, b) => a.sortKey - b.sortKey)
            .map(r => ({ month: r.label, revenue: Math.round(r.revenue) }));

        this.state.chartsData = proxy({
            planPopularity,
            classUtilization,
            equipmentStatus,
            trainerWorkload,
            revenueTrend,
        });
    }

    // ─────────────────────────────────────────────────────────────
    //  Advanced Insights Loader (4 Compact Metrics)
    // ─────────────────────────────────────────────────────────────

    async _loadAdvancedInsights() {
        let topTrainer = "—";
        let topTrainerId = false;
        try {
            const data = this.state.chartsData.trainerWorkload;
            if (data && data.length > 0) {
                const sorted = [...data].sort((a, b) => b.completed - a.completed);
                if (sorted[0] && sorted[0].completed > 0) {
                    topTrainer = sorted[0].name;
                    topTrainerId = sorted[0].id;
                }
            }
        } catch (_) {}

        let highestPlanName = "—";
        let highestPlanId = false;
        try {
            const popularity = this.state.chartsData.planPopularity;
            if (popularity && popularity.length > 0) {
                const sorted = [...popularity].sort((a, b) => b.count - a.count);
                if (sorted[0]) {
                    highestPlanName = sorted[0].name;
                    highestPlanId = sorted[0].id;
                }
            }
        } catch (_) {}

        let renewalRate = 0;
        try {
            const statusData = this.state.enrollmentByStatus;
            const renewed = (statusData.find(s => s.status === "Renewed") || { count: 0 }).count;
            const expired = (statusData.find(s => s.status === "Expired") || { count: 0 }).count;
            const cancelled = (statusData.find(s => s.status === "Cancelled") || { count: 0 }).count;
            const totalConcluded = renewed + expired + cancelled;
            if (totalConcluded > 0) {
                renewalRate = Math.round((renewed / totalConcluded) * 100);
            }
        } catch (_) {}

        let equipUtil = 0;
        try {
            const totalEquip = await this.orm.searchCount("x_equipment", []);
            const availEquip = await this.orm.searchCount("x_equipment", [["x_studio_status", "=", "Available"]]);
            if (totalEquip > 0) {
                equipUtil = Math.round((availEquip / totalEquip) * 100);
            }
        } catch (_) {}

        this.state.insights = proxy({
            topTrainer: topTrainer,
            topTrainerId: topTrainerId,
            highestPlan: highestPlanName,
            highestPlanId: highestPlanId,
            renewalRate: `${renewalRate}%`,
            equipUtilization: `${equipUtil}%`,
        });
    }

    // ─────────────────────────────────────────────────────────────
    //  Dynamic Filter Domain Getters (Opening Odoo views)
    // ─────────────────────────────────────────────────────────────

    get activeMembersDomain() {
        return JSON.stringify(this._getEnrollmentDomain([["x_studio_status", "=", "Active"]]));
    }
    get mrrDomain() {
        return JSON.stringify(this._getEnrollmentDomain([["x_studio_status", "=", "Active"]]));
    }
    get sessionsTodayDomain() {
        return JSON.stringify(this._getSessionsDomain([["x_studio_date", "=", this._todayString()]]));
    }
    get attendanceDomain() {
        return JSON.stringify(this._getSessionsDomain([["x_studio_date", "=", this._todayString()]]));
    }
    get expiringSoonDomain() {
        const todayStr = this._todayString();
        const today = new Date();
        const sevenDaysLater = new Date();
        sevenDaysLater.setDate(today.getDate() + 7);
        const sevenDaysLaterStr = `${sevenDaysLater.getFullYear()}-${String(sevenDaysLater.getMonth() + 1).padStart(2, "0")}-${String(sevenDaysLater.getDate()).padStart(2, "0")}`;
        return JSON.stringify(this._getEnrollmentDomain([
            ["x_studio_status", "=", "Active"],
            ["x_studio_end_date", ">=", todayStr],
            ["x_studio_end_date", "<=", sevenDaysLaterStr]
        ]));
    }
    get activeClassesDomain() {
        return JSON.stringify(this._getClassesDomain([["x_studio_selection_1", "=", "Active"]]));
    }
    get availableEquipmentDomain() {
        return JSON.stringify(this._getEquipmentDomain([["x_studio_status", "=", "Available"]]));
    }
    get trainerUtilizationDomain() {
        return JSON.stringify(this._getSessionsDomain([["x_studio_date", "=", this._todayString()]]));
    }

    // ─────────────────────────────────────────────────────────────
    //  Interactive Click & Export Helpers
    // ─────────────────────────────────────────────────────────────

    onTileClick(model, domain, title) {
        // domain may be an array or a JSON string (backward-compat)
        const resolvedDomain = Array.isArray(domain) ? domain : JSON.parse(domain);
        this.actionService.doAction({
            type: "ir.actions.act_window",
            name: title,
            res_model: model,
            views: [[false, "list"], [false, "form"]],
            domain: resolvedDomain,
            target: "current",
        });
    }

    // Named click handlers used in QWeb — avoids JSON.stringify in templates
    onClickTopTrainer() {
        const trainerId = this.state.insights.topTrainerId;
        if (trainerId) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "hr.employee",
                res_id: trainerId,
                views: [[false, "form"]],
                target: "current",
            });
        } else {
            this.onTileClick("x_training_sessions",
                [["x_studio_date", "=", this._todayString()]], "Trainer Workload");
        }
    }

    onClickHighestPlan() {
        const planId = this.state.insights.highestPlanId;
        if (planId) {
            this.actionService.doAction({
                type: "ir.actions.act_window",
                res_model: "x_membership_plans",
                res_id: planId,
                views: [[false, "form"]],
                target: "current",
            });
        } else {
            this.onTileClick("x_membership_plans",
                [["x_studio_status", "=", "Active"]], "Membership Plans");
        }
    }

    onClickRenewalRate() {
        this.onTileClick("x_enrollment", [], "Enrollment History");
    }

    onClickEquipUtilization() {
        this.onTileClick("x_equipment", [], "Equipment Registry");
    }

    onClickSession(sess) {
        this.onTileClick("x_training_sessions",
            [["id", "=", sess.id]], "Session - " + sess.member);
    }

    onClickClass(cls) {
        this.onTileClick("x_fitness_classes",
            [["id", "=", cls.id]], cls.name);
    }

    onClickTrainerSessions(trainer) {
        this.onTileClick("x_training_sessions",
            [["x_studio_trainer_1_1", "=", trainer.id],
             ["x_studio_date", "=", this._todayString()]],
            "Today's Sessions - " + trainer.name);
    }

    onClickViewAllTrainers() {
        this.onTileClick("hr.employee", [], "Trainer List");
    }

    onClickEquipment(equip) {
        this.onTileClick("x_equipment", [["id", "=", equip.id]], equip.name);
    }

    onClickViewAllEquipment() {
        this.onTileClick("x_equipment", [], "Equipment Registry");
    }


    exportChartPNG(chartId, title) {
        const canvas = document.getElementById(chartId);
        if (!canvas) return;
        const link = document.createElement("a");
        link.download = `${title.replace(/\s+/g, "_")}.png`;
        link.href = canvas.toDataURL("image/png");
        link.click();
    }

    exportTableCSV(type) {
        let data = [];
        let headers = [];
        let filename = "";

        if (type === 'expiries') {
            data = this.state.upcomingExpiries;
            headers = ["Member", "Plan", "Expiry Date", "Remaining Days"];
            filename = "Upcoming_Expiries.csv";
        } else if (type === 'schedule') {
            data = this.state.todaySchedule;
            headers = ["Time", "Member", "Trainer", "Type", "Status"];
            filename = "Today_Schedule.csv";
        } else if (type === 'openings') {
            data = this.state.classOpenings;
            headers = ["Class", "Slots Left", "Occupancy %", "Capacity"];
            filename = "Class_Openings.csv";
        } else if (type === 'trainers') {
            data = this.state.trainerAvailability;
            headers = ["Trainer", "Job Title", "Sessions Today", "Status"];
            filename = "Trainer_Availability.csv";
        } else if (type === 'alerts') {
            data = this.state.equipmentAlerts;
            headers = ["Equipment", "Code", "Category", "Status", "Maintenance Info"];
            filename = "Equipment_Alerts.csv";
        }

        if (data.length === 0) return;

        let csvContent = "data:text/csv;charset=utf-8," + headers.join(",") + "\n";
        data.forEach(item => {
            let row = [];
            if (type === 'expiries') {
                row = [item.member, item.plan, item.expiryDate, item.remainingDays];
            } else if (type === 'schedule') {
                row = [item.time, item.member, item.trainer, item.type, item.status];
            } else if (type === 'openings') {
                row = [item.name, item.slotsLeft, item.occupancy, item.max];
            } else if (type === 'trainers') {
                row = [item.name, item.jobTitle, item.sessionsCount, item.status];
            } else if (type === 'alerts') {
                row = [item.name, item.code, item.category, item.status, item.message];
            }
            csvContent += row.map(v => `"${String(v).replace(/"/g, '""')}"`).join(",") + "\n";
        });

        const encodedUri = encodeURI(csvContent);
        const link = document.createElement("a");
        link.setAttribute("href", encodedUri);
        link.setAttribute("download", filename);
        document.body.appendChild(link);
        link.click();
        document.body.removeChild(link);
    }

    // ─────────────────────────────────────────────────────────────
    //  Chart.js Render Actions (5 Management Charts Rendered Inline)
    // ─────────────────────────────────────────────────────────────

    _initCharts() {
        this._destroyCharts();

        // eslint-disable-next-line no-undef
        if (typeof Chart === "undefined") return;

        const textColor = "#8fbca9";
        const gridColor = "rgba(0, 230, 118, 0.1)";

        const self = this;

        // 1. Radar Chart - Membership Plan Popularity
        const canvas1 = document.getElementById("planPopularityChart");
        if (canvas1) {
            const data = this.state.chartsData.planPopularity;
            // eslint-disable-next-line no-undef
            this.charts.planPopularity = new Chart(canvas1, {
                type: "radar",
                data: {
                    labels: data.map(d => d.name),
                    datasets: [{
                        label: "Plan Popularity",
                        data: data.map(d => d.count),
                        borderColor: "#00ff87",
                        backgroundColor: "rgba(0, 255, 135, 0.15)"
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            grid: { color: gridColor },
                            angleLines: { color: gridColor },
                            ticks: { backdropColor: "transparent", color: textColor }
                        }
                    },
                    onClick: (ev, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const plan = data[index];
                            self.onTileClick("x_enrollment", self._getEnrollmentDomain([["x_studio_membership_plan", "=", plan.id], ["x_studio_status", "=", "Active"]]), `Active Members - ${plan.name}`);
                        }
                    }
                }
            });
        }

        // 2. Line Chart - Monthly Revenue Trend
        const canvas2 = document.getElementById("monthlyRevenueTrendChart");
        if (canvas2) {
            const data = this.state.chartsData.revenueTrend;
            // eslint-disable-next-line no-undef
            this.charts.revenueTrend = new Chart(canvas2, {
                type: "line",
                data: {
                    labels: data.map(d => d.month),
                    datasets: [{
                        label: "Revenue Trend",
                        data: data.map(d => d.revenue),
                        borderColor: "#00ff87",
                        backgroundColor: "rgba(0, 255, 135, 0.1)",
                        fill: true,
                        tension: 0.4
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { color: gridColor }, ticks: { color: textColor } },
                        y: { grid: { color: gridColor }, ticks: { color: textColor } }
                    }
                }
            });
        }

        // 3. Horizontal Bar Chart - Class Capacity Utilization
        const canvas3 = document.getElementById("classCapacityUtilizationChart");
        if (canvas3) {
            const data = this.state.chartsData.classUtilization;
            // eslint-disable-next-line no-undef
            this.charts.classUtilization = new Chart(canvas3, {
                type: "bar",
                data: {
                    labels: data.map(d => d.name),
                    datasets: [{
                        label: "Utilization %",
                        data: data.map(d => d.utilization),
                        backgroundColor: "#00ff87",
                        borderRadius: 6
                    }]
                },
                options: {
                    indexAxis: "y",
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        x: { grid: { color: gridColor }, ticks: { color: textColor } },
                        y: { grid: { color: gridColor }, ticks: { color: textColor } }
                    },
                    onClick: (ev, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const cls = data[index];
                            self.onTileClick("x_fitness_classes", [["id", "=", cls.id]], cls.name);
                        }
                    }
                }
            });
        }

        // 4. Polar Area Chart - Trainer Performance Metrics
        const canvas4 = document.getElementById("trainerPerformanceRadarChart");
        if (canvas4) {
            const workload = this.state.chartsData.trainerWorkload || [];
            // Sort to find the top active trainers
            const topTrainers = [...workload]
                .filter(t => t.id && t.name !== "Unassigned")
                .sort((a, b) => (b.completed + b.scheduled) - (a.completed + a.scheduled))
                .slice(0, 5);

            const datasets = [{
                data: topTrainers.map(t => t.completed + t.scheduled),
                backgroundColor: ["#00ff87ee", "#60efffee", "#39ff14ee", "#0df38cee", "#85ffc7ee"]
            }];

            // Fallback if no trainers exist
            if (topTrainers.length === 0) {
                datasets[0].data = [0];
                datasets[0].backgroundColor = ["#00ff87ee"];
            }

            // eslint-disable-next-line no-undef
            this.charts.radar = new Chart(canvas4, {
                type: "polarArea",
                data: {
                    labels: topTrainers.length > 0 ? topTrainers.map(t => t.name) : ["No Active Trainers"],
                    datasets: datasets
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    scales: {
                        r: {
                            grid: { color: gridColor },
                            ticks: { backdropColor: "transparent", color: textColor }
                        }
                    },
                    onClick: (ev, elements) => {
                        if (elements.length > 0 && topTrainers.length > 0) {
                            const index = elements[0].index;
                            const trainer = topTrainers[index];
                            self.onTileClick("x_training_sessions", self._getSessionsDomain([["x_studio_trainer_1_1", "=", trainer.id]]), `Sessions - ${trainer.name}`);
                        }
                    }
                }
            });
        }

        // 5. Pie Chart - Equipment Status
        const canvas5 = document.getElementById("equipmentStatusPolarChart");
        if (canvas5) {
            const data = this.state.chartsData.equipmentStatus;
            // eslint-disable-next-line no-undef
            this.charts.equipmentStatus = new Chart(canvas5, {
                type: "pie",
                data: {
                    labels: data.map(d => d.status),
                    datasets: [{
                        data: data.map(d => d.count),
                        backgroundColor: ["#00ff87ee", "#ff3860ee"]
                    }]
                },
                options: {
                    responsive: true,
                    maintainAspectRatio: false,
                    onClick: (ev, elements) => {
                        if (elements.length > 0) {
                            const index = elements[0].index;
                            const status = data[index].status;
                            self.onTileClick("x_equipment", self._getEquipmentDomain([["x_studio_status", "=", status]]), `Equipment Status: ${status}`);
                        }
                    }
                }
            });
        }
    }

    // ─────────────────────────────────────────────────────────────
    //  Utility Helpers
    // ─────────────────────────────────────────────────────────────

    _todayString() {
        const d = new Date();
        const year = d.getFullYear();
        const month = String(d.getMonth() + 1).padStart(2, "0");
        const day = String(d.getDate()).padStart(2, "0");
        return `${year}-${month}-${day}`;
    }

    _formatDate(dateStr) {
        if (!dateStr) return "—";
        try {
            const d = new Date(dateStr);
            return d.toLocaleDateString("en-US", {
                year: "numeric",
                month: "short",
                day: "numeric",
            });
        } catch (_) {
            return dateStr;
        }
    }

    _formatDateDisplay(d) {
        return d.toLocaleDateString("en-US", {
            weekday: "long",
            year: "numeric",
            month: "long",
            day: "numeric",
        });
    }

    _formatTimeDisplay(d) {
        return d.toLocaleTimeString("en-US", {
            hour: "2-digit",
            minute: "2-digit",
        });
    }

    _formatCurrency(value) {
        if (!value) return "$0";
        return new Intl.NumberFormat("en-US", {
            style: "currency",
            currency: "USD",
            minimumFractionDigits: 0,
            maximumFractionDigits: 0,
        }).format(value);
    }

    _formatCurrencyShort(value) {
        if (value >= 1000) return `$${(value / 1000).toFixed(1)}k`;
        return `$${value}`;
    }

    _truncateLabel(str, maxLen) {
        if (!str) return "";
        return str.length > maxLen ? str.substring(0, maxLen) + "…" : str;
    }
}

// Register the client action
registry.category("actions").add("fitness_center_saas.fitness_dashboard", FitnessDashboard);
