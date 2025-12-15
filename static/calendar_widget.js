/**
 * Calendar Widget - Interactive month calendar
 * Provides navigation between months and date selection for filtering
 */

class CalendarWidget {
    constructor(containerId, options = {}) {
        this.container = document.getElementById(containerId);
        if (!this.container) {
            console.error(`Calendar widget container #${containerId} not found`);
            return;
        }

        this.currentDate = new Date();
        this.selectedDate = null;
        this.eventDates = options.eventDates || []; // Array of date strings 'YYYY-MM-DD'
        this.onDateSelect = options.onDateSelect || null;
        this.baseUrl = options.baseUrl || '';
        this.urlParams = options.urlParams || {};

        // Spanish month names
        this.monthNames = [
            'enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio',
            'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'
        ];

        // Spanish day names (short)
        this.dayNames = ['LU', 'MA', 'MI', 'JU', 'VI', 'SA', 'DO'];

        this.render();
    }

    /**
     * Render the calendar widget
     */
    render() {
        const today = new Date();
        const year = this.currentDate.getFullYear();
        const month = this.currentDate.getMonth();

        // Format current date display
        const dayName = this.getDayName(today);
        const dateStr = `${dayName}, ${today.getDate()} de ${this.monthNames[today.getMonth()]}`;

        // Create header
        let html = `
            <div class="calendar-widget-header">
                <div class="calendar-widget-date">${dateStr}</div>
            </div>
            <div class="calendar-widget-month-nav">
                <button class="calendar-nav-btn" onclick="calendarWidget.prevMonth()">
                    <i class="fas fa-chevron-left"></i>
                </button>
                <span class="calendar-widget-month">${this.monthNames[month]} de ${year}</span>
                <button class="calendar-nav-btn" onclick="calendarWidget.nextMonth()">
                    <i class="fas fa-chevron-right"></i>
                </button>
            </div>
            <div class="calendar-widget-grid">
        `;

        // Day headers
        for (let day of this.dayNames) {
            html += `<div class="calendar-widget-day-header">${day}</div>`;
        }

        // Get first day of month and number of days
        const firstDay = new Date(year, month, 1);
        const lastDay = new Date(year, month + 1, 0);
        const daysInMonth = lastDay.getDate();

        // Get day of week for first day (0 = Sunday, but we want Monday = 0)
        let startDay = firstDay.getDay() - 1;
        if (startDay < 0) startDay = 6; // Sunday

        // Get days from previous month
        const prevMonth = new Date(year, month, 0);
        const prevMonthDays = prevMonth.getDate();

        // Previous month days
        for (let i = startDay - 1; i >= 0; i--) {
            const day = prevMonthDays - i;
            html += `<div class="calendar-widget-day other-month">${day}</div>`;
        }

        // Current month days
        for (let day = 1; day <= daysInMonth; day++) {
            const dateStr = this.formatDate(year, month, day);
            const isToday = this.isToday(year, month, day);
            const isWeekend = this.isWeekend(year, month, day);
            const hasEvent = this.eventDates.includes(dateStr);
            const isSelected = this.selectedDate === dateStr;

            let classes = ['calendar-widget-day'];
            if (isToday) classes.push('today');
            if (isWeekend) classes.push('weekend');
            if (isSelected && !isToday) classes.push('selected');

            const eventDot = hasEvent ? '<span class="event-dot"></span>' : '';

            html += `
                <div class="${classes.join(' ')}" onclick="calendarWidget.selectDate('${dateStr}')">
                    ${day}${eventDot}
                </div>
            `;
        }

        // Next month days to fill the grid
        const totalCells = startDay + daysInMonth;
        const remainder = totalCells % 7;
        if (remainder > 0) {
            for (let i = 1; i <= 7 - remainder; i++) {
                html += `<div class="calendar-widget-day other-month">${i}</div>`;
            }
        }

        html += '</div>';

        this.container.innerHTML = html;
    }

    /**
     * Navigate to previous month
     */
    prevMonth() {
        this.currentDate.setMonth(this.currentDate.getMonth() - 1);
        this.render();
    }

    /**
     * Navigate to next month
     */
    nextMonth() {
        this.currentDate.setMonth(this.currentDate.getMonth() + 1);
        this.render();
    }

    /**
     * Handle date selection
     */
    selectDate(dateStr) {
        this.selectedDate = dateStr;

        if (this.onDateSelect) {
            this.onDateSelect(dateStr);
        } else {
            // Default behavior: redirect with date filter
            const url = new URL(window.location.href);
            url.searchParams.set('start_date', dateStr);
            url.searchParams.set('end_date', dateStr);
            url.searchParams.set('period', 'custom');
            window.location.href = url.toString();
        }

        this.render();
    }

    /**
     * Format date as YYYY-MM-DD
     */
    formatDate(year, month, day) {
        const m = String(month + 1).padStart(2, '0');
        const d = String(day).padStart(2, '0');
        return `${year}-${m}-${d}`;
    }

    /**
     * Check if date is today
     */
    isToday(year, month, day) {
        const today = new Date();
        return today.getFullYear() === year &&
            today.getMonth() === month &&
            today.getDate() === day;
    }

    /**
     * Check if date is weekend (Saturday or Sunday)
     */
    isWeekend(year, month, day) {
        const date = new Date(year, month, day);
        const dayOfWeek = date.getDay();
        return dayOfWeek === 0 || dayOfWeek === 6;
    }

    /**
     * Get Spanish day name
     */
    getDayName(date) {
        const days = ['domingo', 'lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado'];
        return days[date.getDay()];
    }

    /**
     * Update event dates and re-render
     */
    setEventDates(dates) {
        this.eventDates = dates;
        this.render();
    }
}

// Global instance
let calendarWidget = null;

/**
 * Initialize the calendar widget
 * @param {string} containerId - ID of the container element
 * @param {Array} eventDates - Array of date strings 'YYYY-MM-DD' that have events
 * @param {Function} onDateSelect - Optional callback when a date is selected
 */
function initCalendarWidget(containerId, eventDates = [], onDateSelect = null) {
    calendarWidget = new CalendarWidget(containerId, {
        eventDates: eventDates,
        onDateSelect: onDateSelect
    });
    return calendarWidget;
}
