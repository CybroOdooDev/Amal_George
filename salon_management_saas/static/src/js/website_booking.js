/** @odoo-module **/
import { Interaction } from "@web/public/interaction";
import { registry } from "@web/core/registry";

class SalonBookingForm extends Interaction {
    static selector = "#salon_booking_form";

    setup() {
        // Hidden inputs
        this.bookingTypeInput = this.el.querySelector('#x_studio_booking_type');
        this.serviceInput = this.el.querySelector('#x_studio_service');
        this.packageInput = this.el.querySelector('#x_studio_service_package');
        this.dateInput = this.el.querySelector('#x_studio_date');
        this.slotInput = this.el.querySelector('#x_studio_time_slot');
        this.chairInput = this.el.querySelector('#x_studio_chair_num');
        this.beauticianInput = this.el.querySelector('#x_studio_staff_beautician');

        // Containers / Groups
        this.serviceGroup = this.el.querySelector('#service_group');
        this.packageGroup = this.el.querySelector('#package_group');
        this.beauticianGroup = this.el.querySelector('#beautician_group');
        this.beauticianSelect = this.el.querySelector('#beautician_select');
        this.calendarGroup = this.el.querySelector('#calendar_group');
        this.slotGroup = this.el.querySelector('#slot_group');
        this.chairGroup = this.el.querySelector('#chair_group');
        this.submitBtn = this.el.querySelector('#btn_confirm_booking');
        this.dateFeedback = this.el.querySelector('#date_feedback');

        // Calendar DOM elements
        this.calendarTitle = this.el.querySelector('#calendar_title');
        this.calendarDaysContainer = this.el.querySelector('#calendar_days');
        this.prevMonthBtn = this.el.querySelector('#prev_month');
        this.nextMonthBtn = this.el.querySelector('#next_month');

        // Pills containers
        this.slotPillsContainer = this.el.querySelector('#slot_pills_container');
        this.chairPillsContainer = this.el.querySelector('#chair_pills_container');

        // Sidebar elements (owner document or sibling context)
        const sidebar = this.el.ownerDocument.querySelector('#sidebar_selection_info');
        this.sidebarGroup = sidebar;
        if (sidebar) {
            this.sidebarName = sidebar.querySelector('#sidebar_item_name');
            this.sidebarPrice = sidebar.querySelector('#sidebar_item_price');
            this.sidebarDuration = sidebar.querySelector('#sidebar_item_duration');
            this.sidebarDate = sidebar.querySelector('#sidebar_item_date');
            this.sidebarChair = sidebar.querySelector('#sidebar_item_chair');
        }

        // State variables
        this.currentDate = new Date();
        this.selectedDateStr = "";

        // Cache settings
        this._holidays = null;
        this._weeklyHolidays = null;
        this._breakSettings = null;
    }

    dynamicContent = {
        // Booking Type Pill Clicks
        ".booking-type-pill": {
            "t-on-click": this.onBookingTypeSelect,
        },
        // Service Card Clicks
        ".service-card-pill": {
            "t-on-click": this.onServiceSelect,
        },
        // Package Card Clicks
        ".package-card-pill": {
            "t-on-click": this.onPackageSelect,
        },
        // Calendar Month Navigation
        "#prev_month": {
            "t-on-click": this.onPrevMonth,
        },
        "#next_month": {
            "t-on-click": this.onNextMonth,
        },
        // Beautician Dropdown Change
        "#beautician_select": {
            "t-on-change": this.onBeauticianChange,
        },
        // Form Submission
        _root: {
            "t-on-submit.prevent": this.onFormSubmit,
        },
    };

    async start() {
        // Reset selections
        this.bookingTypeInput.value = "";
        this.serviceInput.value = "";
        this.packageInput.value = "";
        this.beauticianInput.value = "";
        if (this.beauticianSelect) this.beauticianSelect.value = "";
        this.dateInput.value = "";
        this.slotInput.value = "";
        this.chairInput.value = "";

        // Pre-fetch holiday and break configuration
        try {
            await this._fetchHolidaysAndBreaks();
        } catch (e) {
            console.warn("Failed to fetch initial settings", e);
        }
    }

    async _fetchHolidaysAndBreaks() {
        if (!this._weeklyHolidays) {
            const companies = await this.services.orm.searchRead(
                'res.company', [], [
                    'x_studio_holiday_sunday', 'x_studio_holiday_monday',
                    'x_studio_holiday_tuesday', 'x_studio_holiday_wednesday',
                    'x_studio_holiday_thursday', 'x_studio_holiday_friday',
                    'x_studio_holiday_saturday', 'x_studio_holiday_ids'
                ]
            );
            const activeCompany = companies.find(c =>
                c.x_studio_holiday_sunday || c.x_studio_holiday_monday ||
                c.x_studio_holiday_tuesday || c.x_studio_holiday_wednesday ||
                c.x_studio_holiday_thursday || c.x_studio_holiday_friday ||
                c.x_studio_holiday_saturday ||
                (c.x_studio_holiday_ids && c.x_studio_holiday_ids.length > 0)
            ) || companies[0];
            this._weeklyHolidays = activeCompany || {};
        }
        if (!this._holidays) {
            const holidayIds = this._weeklyHolidays?.x_studio_holiday_ids || [];
            if (holidayIds.length > 0) {
                this._holidays = await this.services.orm.searchRead(
                    'x_salon_holiday',
                    [['id', 'in', holidayIds]],
                    ['x_name', 'x_studio_date']
                );
            } else {
                this._holidays = [];
            }
        }
        if (!this._breakSettings) {
            const companies = await this.services.orm.searchRead(
                'res.company', [], ['x_studio_allow_break', 'x_studio_break_start', 'x_studio_break_end']
            );
            const activeCompany = companies.find(c => c.x_studio_allow_break) || companies[0];
            this._breakSettings = activeCompany || {};
        }
    }

    // ─── Booking Type selection ──────────────────────────────────
    onBookingTypeSelect(ev) {
        const btn = ev.currentTarget;
        const val = btn.dataset.value;

        // Toggle active pill state
        this.el.querySelectorAll('.booking-type-pill').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');

        this.bookingTypeInput.value = val;
        this.serviceInput.value = "";
        this.packageInput.value = "";

        // Reset lower elements
        this._resetCalendarSelection();
        this._hideSection(this.calendarGroup);
        this._hideSection(this.slotGroup);
        this._hideSection(this.chairGroup);

        if (val === 'service') {
            this.serviceGroup.style.display = '';
            this.packageGroup.style.display = 'none';
        } else if (val === 'package') {
            this.serviceGroup.style.display = 'none';
            this.packageGroup.style.display = '';
        } else {
            this.serviceGroup.style.display = 'none';
            this.packageGroup.style.display = 'none';
        }

        // Remove active selection classes from all cards
        this.el.querySelectorAll('.service-card-pill, .package-card-pill').forEach(c => c.classList.remove('active'));

        // Hide Beautician group and reset
        this.beauticianInput.value = "";
        if (this.beauticianSelect) this.beauticianSelect.value = "";
        this._hideSection(this.beauticianGroup);

        this._updateSidebar();
        this._validateForm();
    }

    // ─── Service Selection ──────────────────────────────────────
    async onServiceSelect(ev) {
        const card = ev.currentTarget;
        this.el.querySelectorAll('.service-card-pill').forEach(c => c.classList.remove('active'));
        card.classList.add('active');

        this.serviceInput.value = card.dataset.id;
        this.packageInput.value = "";

        // Reset Beautician
        this.beauticianInput.value = "";
        if (this.beauticianSelect) this.beauticianSelect.value = "";

        // Reset date/slots/chairs
        this._resetCalendarSelection();
        this._hideSection(this.calendarGroup);
        this._hideSection(this.slotGroup);
        this._hideSection(this.chairGroup);

        // Fetch same skilled employees based on category via ORM searchRead
        const categoryId = parseInt(card.dataset.category_id);
        let employees = [];
        if (categoryId) {
            try {
                employees = await this.services.orm.searchRead(
                    'hr.employee',
                    [['x_studio_specialties', 'in', [categoryId]]],
                    ['name']
                );
            } catch (e) {
                console.error("Failed to fetch beauticians", e);
            }
        }
        this._populateBeauticians(employees);

        this._updateSidebar();
        this._validateForm();
    }

    // ─── Package Selection ──────────────────────────────────────
    async onPackageSelect(ev) {
        const card = ev.currentTarget;
        this.el.querySelectorAll('.package-card-pill').forEach(c => c.classList.remove('active'));
        card.classList.add('active');

        this.packageInput.value = card.dataset.id;
        this.serviceInput.value = "";

        // Reset Beautician
        this.beauticianInput.value = "";
        if (this.beauticianSelect) this.beauticianSelect.value = "";

        // Reset date/slots/chairs
        this._resetCalendarSelection();
        this._hideSection(this.calendarGroup);
        this._hideSection(this.slotGroup);
        this._hideSection(this.chairGroup);

        // Fetch employees from package staff list via ORM searchRead
        const staffIds = card.dataset.staff_ids ? card.dataset.staff_ids.split(',').map(Number).filter(Boolean) : [];
        let employees = [];
        if (staffIds.length > 0) {
            try {
                employees = await this.services.orm.searchRead(
                    'hr.employee',
                    [['id', 'in', staffIds]],
                    ['name']
                );
            } catch (e) {
                console.error("Failed to fetch beauticians", e);
            }
        }
        this._populateBeauticians(employees);

        this._updateSidebar();
        this._validateForm();
    }

    _populateBeauticians(employees) {
        if (!employees || employees.length === 0) {
            this.beauticianSelect.innerHTML = '<option value="">No beauticians available for this selection</option>';
        } else {
            let html = '<option value="">Choose a Beautician...</option>';
            for (const emp of employees) {
                html += `<option value="${emp.id}">${emp.name}</option>`;
            }
            this.beauticianSelect.innerHTML = html;
        }
        this._showSection(this.beauticianGroup);
    }

    onBeauticianChange() {
        const val = this.beauticianSelect.value;
        this.beauticianInput.value = val;

        this._resetCalendarSelection();
        this._hideSection(this.slotGroup);
        this._hideSection(this.chairGroup);

        if (val) {
            this._showSection(this.calendarGroup);
            this._renderCalendar();
        } else {
            this._hideSection(this.calendarGroup);
        }

        this._updateSidebar();
        this._validateForm();
    }

    // ─── Inline Calendar Engine ─────────────────────────────────
    onPrevMonth() {
        this.currentDate.setMonth(this.currentDate.getMonth() - 1);
        this._renderCalendar();
    }

    onNextMonth() {
        this.currentDate.setMonth(this.currentDate.getMonth() + 1);
        this._renderCalendar();
    }

    async _renderCalendar() {
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();

        const monthNames = ["January", "February", "March", "April", "May", "June",
                            "July", "August", "September", "October", "November", "December"];
        this.calendarTitle.textContent = `${monthNames[month]} ${year}`;

        // Clear existing days
        this.calendarDaysContainer.innerHTML = "";

        // Ensure settings are loaded
        await this._fetchHolidaysAndBreaks();

        const todayStr = this._formatLocalDate(new Date());
        const firstDay = new Date(year, month, 1).getDay();
        const totalDays = new Date(year, month + 1, 0).getDate();

        // 1. Add empty slots for days before the 1st of the month
        for (let i = 0; i < firstDay; i++) {
            const emptyCell = document.createElement('div');
            emptyCell.className = 'calendar-day disabled';
            this.calendarDaysContainer.appendChild(emptyCell);
        }

        // 2. Add calendar days
        for (let day = 1; day <= totalDays; day++) {
            const dayCell = document.createElement('div');
            dayCell.className = 'calendar-day';
            dayCell.textContent = day;

            const dateObj = new Date(year, month, day);
            const dateStr = this._formatLocalDate(dateObj);

            // Highlight today
            if (dateStr === todayStr) {
                dayCell.classList.add('today');
            }

            // Check if day is selected
            if (dateStr === this.selectedDateStr) {
                dayCell.classList.add('selected');
            }

            // Determine if date is in the past, or holiday
            const isPast = dateStr < todayStr;
            const holidayReason = this._isHoliday(dateStr, dateObj.getDay());

            if (isPast || holidayReason) {
                dayCell.classList.add('disabled');
                if (holidayReason) {
                    dayCell.title = holidayReason;
                }
            } else {
                dayCell.dataset.date = dateStr;
                dayCell.addEventListener('click', (e) => this.onCalendarDateSelect(e));
            }

            this.calendarDaysContainer.appendChild(dayCell);
        }
    }

    _isHoliday(dateStr, dayOfWeek) {
        // Specific Holidays check
        if (this._holidays) {
            for (const h of this._holidays) {
                if (h.x_studio_date === dateStr) {
                    return `Holiday: ${h.x_name}`;
                }
            }
        }

        // Weekly Holidays check
        if (this._weeklyHolidays) {
            const dayMap = {
                0: 'x_studio_holiday_sunday',
                1: 'x_studio_holiday_monday',
                2: 'x_studio_holiday_tuesday',
                3: 'x_studio_holiday_wednesday',
                4: 'x_studio_holiday_thursday',
                5: 'x_studio_holiday_friday',
                6: 'x_studio_holiday_saturday',
            };
            if (this._weeklyHolidays[dayMap[dayOfWeek]]) {
                const dayNames = ['Sunday', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday'];
                return `${dayNames[dayOfWeek]} is a weekly holiday.`;
            }
        }
        return null;
    }

    onCalendarDateSelect(ev) {
        const cell = ev.currentTarget;

        // Toggle visual selected state
        this.calendarDaysContainer.querySelectorAll('.calendar-day').forEach(d => d.classList.remove('selected'));
        cell.classList.add('selected');

        this.selectedDateStr = cell.dataset.date;
        this.dateInput.value = this.selectedDateStr;

        this._hideSection(this.chairGroup);
        this._showSection(this.slotGroup);
        this._updateSlots();
        this._updateSidebar();
        this._validateForm();
    }

    _resetCalendarSelection() {
        this.selectedDateStr = "";
        this.dateInput.value = "";
        if (this.calendarDaysContainer) {
            this.calendarDaysContainer.querySelectorAll('.calendar-day').forEach(d => d.classList.remove('selected'));
        }
    }

    // ─── Time Slot Pills generator ──────────────────────────────
    async _updateSlots() {
        const dateVal = this.dateInput.value;
        const duration = this._getSelectedDuration();

        this.slotPillsContainer.innerHTML = '<span class="text-muted small">Loading available slots...</span>';
        this.slotInput.value = "";

        try {
            const breakCfg = await this._getBreakSettings();
            let breakStartMin = null, breakEndMin = null;
            if (breakCfg.x_studio_allow_break && breakCfg.x_studio_break_start && breakCfg.x_studio_break_end) {
                breakStartMin = this._toMinutes(breakCfg.x_studio_break_start);
                breakEndMin = this._toMinutes(breakCfg.x_studio_break_end);
            }

            // Fetch all chairs and active bookings to verify slot capacity
            const allChairs = await this.services.orm.searchRead('x_chair', [], ['id']);
            const totalChairsCount = allChairs.length || 1;

            const bookings = await this.services.orm.searchRead(
                'x_appointment',
                [
                    ['x_studio_date', '=', dateVal],
                    ['x_studio_selection_1', 'in', ['Confirmed', 'Completed', 'In Progress', 'Checked In']],
                    ['x_studio_chair_num', '!=', false],
                ],
                ['x_studio_time_slot', 'x_studio_duration', 'x_studio_chair_num']
            );

            const slots = [];
            for (let startMin = 9 * 60; startMin <= 17 * 60 + 30; startMin += 30) {
                const endMin = startMin + duration;
                if (endMin > 18 * 60) continue; // Must finish by 18:00
                if (breakStartMin !== null && startMin < breakEndMin && breakStartMin < endMin) continue; // overlaps break

                // Verify if there is at least one free chair during this slot
                let busyChairsCount = 0;
                for (const appt of bookings) {
                    if (!appt.x_studio_time_slot) continue;
                    const apptStart = this._toMinutes(appt.x_studio_time_slot);
                    const apptEnd = apptStart + (appt.x_studio_duration || 30);
                    if (startMin < apptEnd && apptStart < endMin) {
                        busyChairsCount++;
                    }
                }

                // Only show slot if at least one chair is free
                if (busyChairsCount < totalChairsCount) {
                    slots.push({
                        value: this._formatValue(startMin),
                        label: this._formatTime(startMin)
                    });
                }
            }

            if (slots.length === 0) {
                this.slotPillsContainer.innerHTML = '<span class="text-danger small">No slots available for this date</span>';
            } else {
                let html = '';
                for (const s of slots) {
                    html += `<button type="button" class="pill-button slot-pill" data-value="${s.value}">${s.label}</button>`;
                }
                this.slotPillsContainer.innerHTML = html;

                // Bind click events to slot pills
                this.slotPillsContainer.querySelectorAll('.slot-pill').forEach(pill => {
                    pill.addEventListener('click', (e) => this.onSlotPillSelect(e));
                });
            }
        } catch (e) {
            console.error('Failed to load slots', e);
            this.slotPillsContainer.innerHTML = '<span class="text-danger small">Error loading slots</span>';
        }
    }

    onSlotPillSelect(ev) {
        const pill = ev.currentTarget;
        this.slotPillsContainer.querySelectorAll('.slot-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');

        this.slotInput.value = pill.dataset.value;

        this._showSection(this.chairGroup);
        this._updateChairs();
        this._updateSidebar();
        this._validateForm();
    }

    // ─── Chair Pills generator ──────────────────────────────────
    async _updateChairs() {
        const dateVal = this.dateInput.value;
        const slotVal = this.slotInput.value;
        const duration = this._getSelectedDuration();

        this.chairPillsContainer.innerHTML = '<span class="text-muted small">Loading available chairs...</span>';
        this.chairInput.value = "";

        try {
            const slotStartMin = this._toMinutes(slotVal);
            const slotEndMin = slotStartMin + duration;

            const allChairs = await this.services.orm.searchRead('x_chair', [], ['x_name']);
            const bookings = await this.services.orm.searchRead(
                'x_appointment',
                [
                    ['x_studio_date', '=', dateVal],
                    ['x_studio_selection_1', 'in', ['Confirmed', 'Completed', 'In Progress', 'Checked In']],
                    ['x_studio_chair_num', '!=', false],
                ],
                ['x_studio_time_slot', 'x_studio_duration', 'x_studio_chair_num']
            );

            const busyChairIds = new Set();
            for (const appt of bookings) {
                if (!appt.x_studio_time_slot) continue;
                const apptStart = this._toMinutes(appt.x_studio_time_slot);
                const apptEnd = apptStart + (appt.x_studio_duration || 30);
                if (slotStartMin < apptEnd && apptStart < slotEndMin && appt.x_studio_chair_num) {
                    busyChairIds.add(appt.x_studio_chair_num[0]);
                }
            }

            const freeChairs = allChairs.filter(c => !busyChairIds.has(c.id));
            if (freeChairs.length === 0) {
                this.chairPillsContainer.innerHTML = '<span class="text-danger small">No chairs available at this time</span>';
            } else {
                let html = '';
                for (const c of freeChairs) {
                    html += `<button type="button" class="pill-button chair-pill" data-id="${c.id}" data-name="${c.x_name}">${c.x_name}</button>`;
                }
                this.chairPillsContainer.innerHTML = html;

                // Bind click events to chair pills
                this.chairPillsContainer.querySelectorAll('.chair-pill').forEach(pill => {
                    pill.addEventListener('click', (e) => this.onChairPillSelect(e));
                });
            }
        } catch (e) {
            console.error('Failed to load chairs', e);
            this.chairPillsContainer.innerHTML = '<span class="text-danger small">Error loading chairs</span>';
        }
    }

    onChairPillSelect(ev) {
        const pill = ev.currentTarget;
        this.chairPillsContainer.querySelectorAll('.chair-pill').forEach(p => p.classList.remove('active'));
        pill.classList.add('active');

        this.chairInput.value = pill.dataset.id;

        this._updateSidebar();
        this._validateForm();
    }

    // ─── Sidebar info updater ───────────────────────────────────
    _updateSidebar() {
        if (!this.sidebarGroup) return;

        const type = this.bookingTypeInput.value;
        let selectedName = "";
        let selectedPrice = "0.00";
        let selectedDuration = 0;

        if (type === 'service' && this.serviceInput.value) {
            const card = this.el.querySelector(`.service-card-pill[data-id="${this.serviceInput.value}"]`);
            if (card) {
                selectedName = card.dataset.name;
                selectedPrice = card.dataset.price;
                selectedDuration = card.dataset.duration;
            }
        } else if (type === 'package' && this.packageInput.value) {
            const card = this.el.querySelector(`.package-card-pill[data-id="${this.packageInput.value}"]`);
            if (card) {
                selectedName = card.dataset.name;
                selectedPrice = card.dataset.price;
                selectedDuration = card.dataset.duration;
            }
        }

        if (selectedName) {
            this.sidebarGroup.style.display = '';
            this.sidebarName.textContent = selectedName;
            this.sidebarPrice.textContent = `$${parseFloat(selectedPrice).toFixed(2)}`;
            this.sidebarDuration.textContent = selectedDuration;

            // Date
            if (this.dateInput.value) {
                const dateParts = this.dateInput.value.split('-');
                const formattedDate = new Date(dateParts[0], dateParts[1] - 1, dateParts[2]).toLocaleDateString('en-US', {
                    weekday: 'long', year: 'numeric', month: 'long', day: 'numeric'
                });
                this.sidebarDate.textContent = `${formattedDate} ${this.slotInput.value ? 'at ' + this._formatTime(this._toMinutes(this.slotInput.value)) : ''}`;
            } else {
                this.sidebarDate.textContent = "-";
            }

            // Chair
            if (this.chairInput.value) {
                const activeChairBtn = this.chairPillsContainer.querySelector('.chair-pill.active');
                this.sidebarChair.textContent = activeChairBtn ? activeChairBtn.dataset.name : "Chair Num";
            } else {
                this.sidebarChair.textContent = "-";
            }
        } else {
            this.sidebarGroup.style.display = 'none';
        }
    }

    // ─── Time calculations ──────────────────────────────────────
    _getSelectedDuration() {
        const type = this.bookingTypeInput.value;
        if (type === 'service' && this.serviceInput.value) {
            const card = this.el.querySelector(`.service-card-pill[data-id="${this.serviceInput.value}"]`);
            return card ? parseInt(card.dataset.duration || '30') : 30;
        } else if (type === 'package' && this.packageInput.value) {
            const card = this.el.querySelector(`.package-card-pill[data-id="${this.packageInput.value}"]`);
            return card ? parseInt(card.dataset.duration || '60') : 60;
        }
        return 30;
    }

    async _getBreakSettings() {
        if (!this._breakSettings) {
            await this._fetchHolidaysAndBreaks();
        }
        return this._breakSettings;
    }

    _toMinutes(timeStr) {
        if (!timeStr) return 0;
        const [h, m] = timeStr.split(':').map(Number);
        return h * 60 + m;
    }

    _formatTime(minutes) {
        const h = Math.floor(minutes / 60);
        const m = minutes % 60;
        const ampm = h < 12 ? 'AM' : 'PM';
        const dh = h === 0 ? 12 : h > 12 ? h - 12 : h;
        return `${String(dh).padStart(2,'0')}:${String(m).padStart(2,'0')} ${ampm}`;
    }

    _formatValue(minutes) {
        return `${String(Math.floor(minutes/60)).padStart(2,'0')}:${String(minutes%60).padStart(2,'0')}`;
    }

    // ─── Helpers ────────────────────────────────────────────────
    _showSection(el) {
        if (el) el.style.display = '';
    }

    _hideSection(el) {
        if (el) el.style.display = 'none';
    }

    _resetSubmitButton() {
        this.submitBtn.disabled = false;
        this.submitBtn.textContent = 'Request Booking';
    }

    _showError(msg) {
        let errDiv = this.el.querySelector('#salon_form_error');
        if (!errDiv) {
            errDiv = document.createElement('div');
            errDiv.id = 'salon_form_error';
            errDiv.className = 'alert alert-danger mt-3';
            this.submitBtn.parentNode.insertBefore(errDiv, this.submitBtn);
        }
        errDiv.textContent = msg;
        errDiv.style.display = '';
    }

    // ─── Form submission ────────────────────────────────────────
    async onFormSubmit(ev) {
        if (this.submitBtn.disabled) return;

        this.submitBtn.disabled = true;
        this.submitBtn.textContent = 'Processing...';

        const prevErr = this.el.querySelector('#salon_form_error');
        if (prevErr) prevErr.style.display = 'none';

        try {
            const partnerId = this.el.querySelector('#x_studio_partner_id').value;
            const formData = new FormData();

            if (window.odoo && window.odoo.csrf_token) {
                formData.append('csrf_token', window.odoo.csrf_token);
            }

            formData.append('x_studio_partner_id', partnerId || '');
            formData.append('x_studio_booking_type', this.bookingTypeInput.value);
            formData.append('x_studio_date', this.dateInput.value);
            formData.append('x_studio_time_slot', this.slotInput.value);
            formData.append('x_studio_chair_num', this.chairInput.value || '');
            formData.append('x_studio_staff_beautician', this.beauticianInput.value || '');
            formData.append('x_studio_selection_1', 'Confirmed');

            if (this.bookingTypeInput.value === 'service') {
                formData.append('x_studio_service', this.serviceInput.value || '');
            } else if (this.bookingTypeInput.value === 'package') {
                formData.append('x_studio_service_package', this.packageInput.value || '');
            }

            const resp = await fetch('/website/form/x_appointment', {
                method: 'POST',
                body: formData,
            });

            let errorMsg = "";
            if (resp.ok) {
                const text = await resp.text();
                let data = null;
                try {
                    data = JSON.parse(text);
                } catch (jsonErr) {
                    errorMsg = "Server returned an unexpected format. Please contact support.";
                }

                if (data !== null) {
                    if (data && data.id) {
                        window.location.href = '/booking/success';
                        return;
                    } else if (data && data.error) {
                        errorMsg = data.error;
                    } else if (data && data.error_fields) {
                        const fieldsStr = Object.keys(data.error_fields).join(', ');
                        errorMsg = `Please correct the following fields: ${fieldsStr}`;
                    } else if (data === false) {
                        errorMsg = "Database rejected the booking (Integrity constraint check failed).";
                    } else {
                        errorMsg = "Unexpected response from server.";
                    }
                }
            } else {
                let detail = "";
                try {
                    const text = await resp.text();
                    const match = text.match(/<title>([\s\S]*?)<\/title>/i) || text.match(/<h1>([\s\S]*?)<\/h1>/i);
                    if (match && match[1]) {
                        detail = match[1].trim();
                    } else if (text && text.length < 200) {
                        detail = text.trim();
                    }
                } catch (textErr) {}
                errorMsg = `Booking failed (Status ${resp.status})${detail ? ': ' + detail : '. Please check your input data.'}`;
            }

            this._showError(errorMsg || 'Booking failed. Please try again.');
            this._resetSubmitButton();
        } catch (e) {
            console.error('Booking submission failed', e);
            this._showError(e.message || 'An error occurred. Please try again.');
            this._resetSubmitButton();
        }
    }

    _validateForm() {
        const type = this.bookingTypeInput.value;
        const hasService = type === 'service' && this.serviceInput.value;
        const hasPackage = type === 'package' && this.packageInput.value;
        const valid = (hasService || hasPackage)
            && !!this.beauticianInput.value
            && !!this.dateInput.value
            && !!this.slotInput.value
            && !!this.chairInput.value;
        this.submitBtn.disabled = !valid;
    }

    _formatLocalDate(dateObj) {
        const y = dateObj.getFullYear();
        const m = String(dateObj.getMonth() + 1).padStart(2, '0');
        const d = String(dateObj.getDate()).padStart(2, '0');
        return `${y}-${m}-${d}`;
    }
}

registry
    .category("public.interactions")
    .add("salon_management_saas.salon_booking_form", SalonBookingForm);
