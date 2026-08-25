document.addEventListener('DOMContentLoaded', function () {
    const dateInput = document.getElementById('x_studio_date');
    const beauticianSelect = document.getElementById('x_studio_staff_beautician');
    const slotSelect = document.getElementById('x_studio_time_slot');

    if (!dateInput || !beauticianSelect || !slotSelect) return;

    // Set minimum date to today
    const today = new Date().toISOString().split('T')[0];
    dateInput.setAttribute('min', today);

    async function updateSlots() {
        const dateVal = dateInput.value;
        const beauticianVal = beauticianSelect.value;

        if (!dateVal || !beauticianVal) {
            slotSelect.innerHTML = '<option value="">Choose date/beautician first...</option>';
            return;
        }

        slotSelect.innerHTML = '<option value="">Loading available slots...</option>';

        try {
            // 1. Fetch booked appointments for this date and beautician
            const appointments = await new Promise((resolve, reject) => {
                const xhr = new XMLHttpRequest();
                xhr.open('POST', '/web/dataset/call_kw');
                xhr.setRequestHeader('Content-Type', 'application/json');
                xhr.onload = function () {
                    if (xhr.status === 200) {
                        const resp = JSON.parse(xhr.responseText);
                        if (resp.error) reject(resp.error);
                        else resolve(resp.result || []);
                    } else {
                        reject(xhr.statusText);
                    }
                };
                xhr.onerror = function () { reject(xhr.statusText); };
                xhr.send(JSON.stringify({
                    jsonrpc: '2.0',
                    method: 'call',
                    params: {
                        model: 'x_appointment',
                        method: 'search_read',
                        args: [[
                            ['x_studio_date', '=', dateVal],
                            ['x_studio_staff_beautician', '=', parseInt(beauticianVal)],
                            ['x_studio_selection_1', 'in', ['Confirmed', 'Completed']]
                        ]],
                        kwargs: {
                            fields: ['x_studio_time_slot']
                        }
                    }
                }));
            });

            const bookedSlots = appointments.map(appt => appt.x_studio_time_slot);

            // 2. Fetch company break settings
            let breakStart = null;
            let breakEnd = null;
            let allowBreak = false;
            try {
                const company = await new Promise((resolve, reject) => {
                    const xhr = new XMLHttpRequest();
                    xhr.open('POST', '/web/dataset/call_kw');
                    xhr.setRequestHeader('Content-Type', 'application/json');
                    xhr.onload = function () {
                        if (xhr.status === 200) {
                            const resp = JSON.parse(xhr.responseText);
                            if (resp.error) reject(resp.error);
                            else resolve(resp.result || []);
                        } else {
                            reject(xhr.statusText);
                        }
                    };
                    xhr.send(JSON.stringify({
                        jsonrpc: '2.0',
                        method: 'call',
                        params: {
                            model: 'res.company',
                            method: 'search_read',
                            args: [[], ['x_studio_allow_break', 'x_studio_break_start', 'x_studio_break_end']],
                            kwargs: { limit: 1 }
                        }
                    }));
                });
                if (company && company.length > 0) {
                    allowBreak = company[0].x_studio_allow_break;
                    breakStart = company[0].x_studio_break_start;
                    breakEnd = company[0].x_studio_break_end;
                }
            } catch (e) {
                console.warn("Failed to fetch break settings, proceeding without break checks", e);
            }

            // Helper to parse HH:MM to minutes
            const toMinutes = (timeStr) => {
                if (!timeStr) return 0;
                const parts = timeStr.split(':');
                return parseInt(parts[0]) * 60 + parseInt(parts[1]);
            };

            // 3. Define all standard time slots (09:00 AM to 05:30 PM)
            const allSlots = [
                { value: '09:00', label: '09:00 AM' },
                { value: '09:30', label: '09:30 AM' },
                { value: '10:00', label: '10:00 AM' },
                { value: '10:30', label: '10:30 AM' },
                { value: '11:00', label: '11:00 AM' },
                { value: '11:30', label: '11:30 AM' },
                { value: '12:00', label: '12:00 PM' },
                { value: '12:30', label: '12:30 PM' },
                { value: '13:00', label: '01:00 PM' },
                { value: '13:30', label: '01:30 PM' },
                { value: '14:00', label: '02:00 PM' },
                { value: '14:30', label: '02:30 PM' },
                { value: '15:00', label: '03:00 PM' },
                { value: '15:30', label: '03:30 PM' },
                { value: '16:00', label: '04:00 PM' },
                { value: '16:30', label: '04:30 PM' },
                { value: '17:00', label: '05:00 PM' },
                { value: '17:30', label: '05:30 PM' }
            ];

            // Filter slots
            let availableSlots = allSlots.filter(slot => !bookedSlots.includes(slot.value));

            // Filter by break time
            if (allowBreak && breakStart && breakEnd) {
                const bsMin = toMinutes(breakStart);
                const beMin = toMinutes(breakEnd);
                availableSlots = availableSlots.filter(slot => {
                    const slotMin = toMinutes(slot.value);
                    return !(slotMin >= bsMin && slotMin < beMin);
                });
            }

            // 4. Render slots
            if (availableSlots.length === 0) {
                slotSelect.innerHTML = '<option value="">No slots available for this date</option>';
            } else {
                let html = '<option value="">Choose a Time Slot...</option>';
                for (const slot of availableSlots) {
                    html += `<option value="${slot.value}">${slot.label}</option>`;
                }
                slotSelect.innerHTML = html;
            }

        } catch (error) {
            console.error("Failed to load slots", error);
            slotSelect.innerHTML = '<option value="">Error loading slots</option>';
        }
    }

    dateInput.addEventListener('change', updateSlots);
    beauticianSelect.addEventListener('change', updateSlots);
});
