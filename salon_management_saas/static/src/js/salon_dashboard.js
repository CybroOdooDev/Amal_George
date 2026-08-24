import { registry } from "@web/core/registry";
import { Component, onWillStart, proxy } from "@odoo/owl";
import { useService } from "@web/core/utils/hooks";
import { user } from "@web/core/user";

class SalonDashboard extends Component {
    static template = "salon_management_saas.SalonDashboard";
    static props = ["*"];

    setup() {
        super.setup();
        this.orm = useService("orm");
        
        this.state = proxy({
            today_bookings: 0,
            monthly_revenue: 0,
            active_chairs: 0,
            avg_ticket_value: 0,
            services_rendered: 0,
            today_bookings_list: [],
            beautician_rankings: [],
            category_rankings: [],
            error_message: "",

            // Filter status
            date_filter: "this_month",
            custom_start_date: "",
            custom_end_date: "",

            // Lookup records
            employees: [],
            chairs: [],

            // Dynamically computed SVG and data components
            donut_segments: [],
            line_path: "",
            line_area_path: "",
            line_points: [],
            line_labels: [],
            radar_points_1: "",
            radar_points_2: "",
            radar_employee_1_name: "",
            radar_employee_2_name: "",
            polar_paths: [],
            top_packages: [],
        });

        onWillStart(async () => {
            this.employeesLoaded = false;
            this.chairsLoaded = false;
            this.servicesLoaded = false;
            await this.loadLookups();
            await this.loadData();
        });
    }

    get greeting() {
        const hour = new Date().getHours();
        let greet = "Good evening";
        if (hour < 12) {
            greet = "Good morning";
        } else if (hour < 18) {
            greet = "Good afternoon";
        }
        return `${greet}, ${user.name}!`;
    }

    async loadLookups() {
        try {
            if (!this.employeesLoaded) {
                try {
                    this.state.employees = await this.orm.searchRead("hr.employee", [], ["id", "name"]);
                } catch (err) {
                    console.error("Failed to read hr.employee", err);
                    throw new Error(`Failed to load Staff list: ${err.message || err.toString()}`);
                }
                this.employeesLoaded = true;
            }
            if (!this.chairsLoaded) {
                try {
                    this.state.chairs = await this.orm.searchRead("x_chair", [], ["id", "x_name"]);
                } catch (err) {
                    console.error("Failed to read x_chair", err);
                    throw new Error(`Failed to load Chairs list: ${err.message || err.toString()}`);
                }
                this.chairsLoaded = true;
            }
            if (!this.servicesLoaded) {
                try {
                    this.services = await this.orm.searchRead("x_service", [], ["id", "x_name", "x_studio_service_category"]);
                } catch (err) {
                    console.error("Failed to read x_service", err);
                    throw new Error(`Failed to load Services list: ${err.message || err.toString()}`);
                }
                try {
                    this.categories = await this.orm.searchRead("x_service_category", [], ["id", "x_name"]);
                } catch (err) {
                    console.error("Failed to read x_service_category", err);
                    throw new Error(`Failed to load Service Categories list: ${err.message || err.toString()}`);
                }
                this.servicesLoaded = true;
            }
        } catch (e) {
            console.error("[SalonDashboard] Failed to load lookup data", e);
            this.state.error_message = `Failed to load lookup data: ${e.message || e.toString()}`;
            throw e;
        }
    }

    formatLocalDate(date) {
        if (!date) return "";
        const offset = date.getTimezoneOffset();
        const localDate = new Date(date.getTime() - offset * 60000);
        return localDate.toISOString().split("T")[0];
    }

    getDateRange(filter) {
        const today = new Date();
        const start = new Date(today);
        const end = new Date(today);

        if (filter === "today") {
            // start and end are today
        } else if (filter === "this_week") {
            const day = today.getDay();
            const diff = today.getDate() - day + (day === 0 ? -6 : 1);
            start.setDate(diff);
            end.setDate(diff + 6);
        } else if (filter === "this_month") {
            start.setDate(1);
            end.setMonth(today.getMonth() + 1);
            end.setDate(0);
        } else if (filter === "this_year") {
            start.setMonth(0, 1);
            end.setMonth(11, 31);
        }

        return {
            start: this.formatLocalDate(start),
            end: this.formatLocalDate(end)
        };
    }

    async loadData() {
        try {
            this.state.error_message = "";
            await this.loadLookups();

            const domain = [];

            // Apply Date Range Filter
            if (this.state.date_filter !== "all_time") {
                let start, end;
                if (this.state.date_filter === "custom") {
                    start = this.state.custom_start_date;
                    end = this.state.custom_end_date;
                } else {
                    const range = this.getDateRange(this.state.date_filter);
                    start = range.start;
                    end = range.end;
                }
                if (start) {
                    domain.push(["x_studio_date", ">=", start]);
                }
                if (end) {
                    domain.push(["x_studio_date", "<=", end]);
                }
            }

            // Filter for Confirmed bookings by default to show actual realized metrics
            domain.push(["x_studio_selection_1", "=", "Confirmed"]);

            // 1. Fetch all appointments matching filters
            let appointments;
            try {
                appointments = await this.orm.searchRead(
                    "x_appointment",
                    domain,
                    ["x_studio_value", "x_studio_service", "x_studio_date", "x_studio_time_slot", "x_studio_chair_num", "x_studio_staff_beautician", "x_studio_service_package"]
                );
            } catch (err) {
                console.error("Failed to search x_appointment", err);
                throw new Error(`Failed to load Appointments data: ${err.message || err.toString()}`);
            }

            // Calculate Bookings count
            this.state.today_bookings = appointments.length;

            // Calculate Total Revenue
            let totalRevenue = 0;
            for (const appt of appointments) {
                totalRevenue += appt.x_studio_value || 0;
            }
            this.state.monthly_revenue = Math.round(totalRevenue * 100) / 100;

            // Calculate Average Ticket Value (ATV)
            this.state.avg_ticket_value = appointments.length > 0 ? Math.round(totalRevenue / appointments.length) : 0;

            // Calculate Services (total registered services in lookups)
            this.state.services_rendered = this.services ? this.services.length : 0;

            // Calculate Beautician rankings
            const staffStats = {};
            for (const appt of appointments) {
                const staff = appt.x_studio_staff_beautician;
                if (staff) {
                    const staffId = staff[0];
                    const staffName = staff[1];
                    if (!staffStats[staffId]) {
                        staffStats[staffId] = { name: staffName, bookings: 0, revenue: 0 };
                    }
                    staffStats[staffId].bookings++;
                    staffStats[staffId].revenue += appt.x_studio_value || 0;
                }
            }
            this.state.beautician_rankings = Object.values(staffStats)
                .sort((a, b) => b.revenue - a.revenue)
                .slice(0, 5)
                .map(s => ({ ...s, revenue: Math.round(s.revenue * 100) / 100 }));

            // 2. Active Chairs count
            let activeChairs = 0;
            try {
                activeChairs = await this.orm.searchCount("x_chair", []);
            } catch (err) {
                console.error("Failed to count x_chair", err);
                throw new Error(`Failed to load Active Chairs count: ${err.message || err.toString()}`);
            }
            this.state.active_chairs = activeChairs;

            // 3. Fetch today's bookings
            const todayDate = new Date();
            const yyyy = todayDate.getFullYear();
            const mm = String(todayDate.getMonth() + 1).padStart(2, '0');
            const dd = String(todayDate.getDate()).padStart(2, '0');
            const todayStr = `${yyyy}-${mm}-${dd}`;
            let todayBookings = [];
            try {
                todayBookings = await this.orm.searchRead(
                    "x_appointment",
                    [["x_studio_date", "=", todayStr], ["x_studio_selection_1", "=", "Confirmed"]],
                    ["x_name", "x_studio_partner_id", "x_studio_time_slot", "x_studio_chair_num", "x_studio_value", "x_studio_staff_beautician"],
                    { order: "x_studio_time_slot asc" }
                );
            } catch (err) {
                console.error("Failed to read today appointments", err);
                throw new Error(`Failed to load Today's Bookings list: ${err.message || err.toString()}`);
            }
            this.state.today_bookings_list = todayBookings;

            // Compute Donut Chart segments (Revenue by Category)
            const serviceToCategory = {};
            if (this.services) {
                for (const s of this.services) {
                    serviceToCategory[s.id] = s.x_studio_service_category ? s.x_studio_service_category[1] : "Other Care";
                }
            }

            const categoryRev = {};
            const categoryBookings = {};
            let totalCategoryRev = 0;
            for (const appt of appointments) {
                const val = appt.x_studio_value || 0;
                const srv = appt.x_studio_service;
                const catName = srv ? (serviceToCategory[srv[0]] || "Other Care") : "Other Care";
                categoryRev[catName] = (categoryRev[catName] || 0) + val;
                categoryBookings[catName] = (categoryBookings[catName] || 0) + 1;
                totalCategoryRev += val;
            }

            const catRankings = Object.keys(categoryRev).map(cat => ({
                name: cat,
                bookings: categoryBookings[cat] || 0,
                revenue: Math.round((categoryRev[cat] || 0) * 100) / 100,
            })).sort((a, b) => b.revenue - a.revenue);
            this.state.category_rankings = catRankings;

            const categoryColors = {
                "Hair Care": "#00CEB3",
                "Skin Care": "#36b9cc",
                "Nail Care": "#f6c23e",
                "Massage Therapy": "#4e73df",
                "Makeup & Styling": "#e74a3b",
                "Other Care": "#858796",
            };

            let accumulated = 0;
            const donutSegments = [];
            if (totalCategoryRev > 0) {
                for (const [cat, rev] of Object.entries(categoryRev)) {
                    const pct = Math.round((rev / totalCategoryRev) * 100);
                    if (pct > 0) {
                        donutSegments.push({
                            category: cat,
                            revenue: rev,
                            percent: pct,
                            color: categoryColors[cat] || "#858796",
                            dashArray: `${pct} ${100 - pct}`,
                            dashOffset: (100 - accumulated + 25) % 100,
                        });
                        accumulated += pct;
                    }
                }
            }
            this.state.donut_segments = donutSegments;

            // Compute Line Chart (Revenue Growth Trend)
            const dateMap = {};
            for (const appt of appointments) {
                const dt = appt.x_studio_date;
                if (dt) {
                    dateMap[dt] = (dateMap[dt] || 0) + (appt.x_studio_value || 0);
                }
            }

            const sortedDates = Object.keys(dateMap).sort();
            let selectedDates = [];
            if (sortedDates.length <= 5) {
                selectedDates = sortedDates;
            } else {
                const step = (sortedDates.length - 1) / 4;
                for (let i = 0; i < 5; i++) {
                    selectedDates.push(sortedDates[Math.round(i * step)]);
                }
            }

            // No padding — only render real data points

            const lineValues = selectedDates.map(d => dateMap[d] || 0);
            const maxLineVal = Math.max(...lineValues, 1);
            const n = selectedDates.length;
            const linePoints = [];

            if (n > 0) {
                // Distribute points evenly across SVG width (60 to 740)
                for (let i = 0; i < n; i++) {
                    const x = n === 1 ? 400 : Math.round(60 + (i / (n - 1)) * 680);
                    const val = lineValues[i];
                    const y = 220 - (val / maxLineVal) * 190;
                    linePoints.push({ x, y, val, date: selectedDates[i] });
                }
            }

            if (linePoints.length > 0) {
                let pathD = `M ${linePoints[0].x} ${linePoints[0].y}`;
                for (let i = 1; i < linePoints.length; i++) {
                    pathD += ` L ${linePoints[i].x} ${linePoints[i].y}`;
                }
                this.state.line_path = pathD;
                this.state.line_area_path = `${pathD} L ${linePoints[linePoints.length - 1].x} 220 L ${linePoints[0].x} 220 Z`;
            } else {
                this.state.line_path = "";
                this.state.line_area_path = "";
            }
            this.state.line_points = linePoints;

            const formatLabel = (dtStr) => {
                if (!dtStr || dtStr === "N/A") return "N/A";
                try {
                    const parts = dtStr.split("-");
                    const date = new Date(parts[0], parts[1] - 1, parts[2]);
                    return date.toLocaleDateString("en-US", { month: "short", day: "numeric" });
                } catch (e) {
                    return dtStr;
                }
            };
            this.state.line_labels = selectedDates.map(formatLabel);

            // Compute Radar Chart (Beautician Competency)
            const staffApptCounts = {};
            for (const appt of appointments) {
                const staff = appt.x_studio_staff_beautician;
                if (staff) {
                    staffApptCounts[staff[0]] = (staffApptCounts[staff[0]] || 0) + 1;
                }
            }
            const sortedStaffIds = Object.keys(staffApptCounts).sort((a, b) => staffApptCounts[b] - staffApptCounts[a]);

            let emp1Id, emp2Id;
            let emp1Name = "";
            let emp2Name = "";

            if (this.state.staff_filter !== "all") {
                emp1Id = parseInt(this.state.staff_filter);
                const emp1Obj = this.state.employees.find(e => e.id === emp1Id);
                emp1Name = emp1Obj ? emp1Obj.name : "Selected Staff";
                emp2Name = "Others Average";
            } else {
                if (sortedStaffIds.length > 0) {
                    emp1Id = parseInt(sortedStaffIds[0]);
                    const emp1Obj = this.state.employees.find(e => e.id === emp1Id);
                    if (emp1Obj) emp1Name = emp1Obj.name;
                }
                if (sortedStaffIds.length > 1) {
                    emp2Id = parseInt(sortedStaffIds[1]);
                    const emp2Obj = this.state.employees.find(e => e.id === emp2Id);
                    if (emp2Obj) emp2Name = emp2Obj.name;
                }
            }
            this.state.radar_employee_1_name = emp1Name;
            this.state.radar_employee_2_name = emp2Name;

            const categories = ["Hair Care", "Skin Care", "Nail Care", "Massage Therapy", "Makeup & Styling"];
            const emp1Data = [0, 0, 0, 0, 0];
            const emp2Data = [0, 0, 0, 0, 0];

            for (const appt of appointments) {
                const srv = appt.x_studio_service;
                const val = appt.x_studio_value || 0;
                const staff = appt.x_studio_staff_beautician;
                const catName = srv ? (serviceToCategory[srv[0]] || "Other Care") : "Other Care";
                const catIdx = categories.indexOf(catName);
                if (catIdx !== -1) {
                    if (staff) {
                        const staffId = staff[0];
                        if (this.state.staff_filter !== "all") {
                            if (staffId === emp1Id) {
                                emp1Data[catIdx] += val;
                            } else {
                                emp2Data[catIdx] += val;
                            }
                        } else {
                            if (staffId === emp1Id) emp1Data[catIdx] += val;
                            if (staffId === emp2Id) emp2Data[catIdx] += val;
                        }
                    }
                }
            }

            if (this.state.staff_filter !== "all" && sortedStaffIds.length > 1) {
                const othersCount = sortedStaffIds.length - 1;
                for (let i = 0; i < 5; i++) {
                    emp2Data[i] = emp2Data[i] / othersCount;
                }
            }

            const maxEmpVal = Math.max(...emp1Data, ...emp2Data, 100);
            const getRadarPoints = (dataArray) => {
                const pts = [];
                const angles = [
                    -Math.PI / 2, // Hair Care
                    -Math.PI / 2 + (1 * 2 * Math.PI) / 5, // Nail Care
                    -Math.PI / 2 + (2 * 2 * Math.PI) / 5, // Makeup
                    -Math.PI / 2 + (3 * 2 * Math.PI) / 5, // Skin Care
                    -Math.PI / 2 + (4 * 2 * Math.PI) / 5  // Massage Therapy
                ];
                for (let i = 0; i < 5; i++) {
                    const val = dataArray[i];
                    const radius = (val / maxEmpVal) * 80;
                    const x = Math.round(110 + Math.cos(angles[i]) * radius);
                    const y = Math.round(100 + Math.sin(angles[i]) * radius);
                    pts.push(`${x},${y}`);
                }
                return pts.join(" ");
            };

            this.state.radar_points_1 = getRadarPoints(emp1Data);
            this.state.radar_points_2 = getRadarPoints(emp2Data);

            // Compute Polar Area Chart (Hourly Booking Density)
            const slotCounts = [0, 0, 0, 0];
            for (const appt of appointments) {
                const slot = appt.x_studio_time_slot;
                if (slot) {
                    const hour = parseInt(slot.split(":")[0]);
                    if (hour < 12) slotCounts[0]++;
                    else if (hour < 15) slotCounts[1]++;
                    else if (hour < 17) slotCounts[2]++;
                    else slotCounts[3]++;
                }
            }

            const maxPolarCount = Math.max(...slotCounts, 1);
            const getQuadrantPath = (idx, count) => {
                const radius = (count / maxPolarCount) * 80 + 10;
                const startAngles = [
                    -Math.PI / 2,
                    0,
                    Math.PI / 2,
                    Math.PI
                ];
                const endAngles = [
                    0,
                    Math.PI / 2,
                    Math.PI,
                    -Math.PI / 2
                ];
                const x1 = Math.round(100 + Math.cos(startAngles[idx]) * radius);
                const y1 = Math.round(100 + Math.sin(startAngles[idx]) * radius);
                const x2 = Math.round(100 + Math.cos(endAngles[idx]) * radius);
                const y2 = Math.round(100 + Math.sin(endAngles[idx]) * radius);
                return `M 100 100 L ${x1} ${y1} A ${radius} ${radius} 0 0 1 ${x2} ${y2} Z`;
            };

            this.state.polar_paths = [
                { path: getQuadrantPath(0, slotCounts[0]), color: "#00CEB3", name: "Morning", count: slotCounts[0] },
                { path: getQuadrantPath(1, slotCounts[1]), color: "#f6c23e", name: "Mid-day", count: slotCounts[1] },
                { path: getQuadrantPath(2, slotCounts[2]), color: "#e74a3b", name: "Afternoon", count: slotCounts[2] },
                { path: getQuadrantPath(3, slotCounts[3]), color: "#4e73df", name: "Evening", count: slotCounts[3] },
            ];

            // Compute Horizontal Bar Chart (Top Packages)
            const packageCounts = {};
            for (const appt of appointments) {
                let name = "Single Service";
                if (appt.x_studio_service_package) {
                    name = appt.x_studio_service_package[1];
                } else if (appt.x_studio_service) {
                    name = appt.x_studio_service[1];
                }
                packageCounts[name] = (packageCounts[name] || 0) + 1;
            }

            const sortedPackages = Object.entries(packageCounts)
                .sort((a, b) => b[1] - a[1])
                .slice(0, 3);

            const totalPkgCount = appointments.length || 1; // avoid divide-by-zero
            const topPackages = [];
            const barColors = ["#00CEB3", "#4e73df", "#f6c23e"];
            for (let i = 0; i < 3; i++) {
                if (sortedPackages[i]) {
                    const name = sortedPackages[i][0];
                    const count = sortedPackages[i][1];
                    const pct = Math.round((count / totalPkgCount) * 100);
                    topPackages.push({
                        name,
                        count,
                        percent: pct,
                        color: barColors[i],
                    });
                }
                // If no real data for slot i — skip, don't show fake placeholders
            }
            this.state.top_packages = topPackages;

        } catch (e) {
            console.error("[SalonDashboard] Failed to load dashboard data", e);
            this.state.error_message = `Failed to load dashboard: ${e.message || e.toString()}`;
        }
    }

    async onDateFilterChange(ev) {
        this.state.date_filter = ev.target.value;
        await this.loadData();
    }



    async onCustomStartDateChange(ev) {
        this.state.custom_start_date = ev.target.value;
        await this.loadData();
    }

    async onCustomEndDateChange(ev) {
        this.state.custom_end_date = ev.target.value;
        await this.loadData();
    }
}

registry.category("actions").add("salon_dashboard_client_action", SalonDashboard);
